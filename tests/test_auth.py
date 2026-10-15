"""t7: login, logout, session, lockout, /me (SEC-5, SEC-6, SEC-11)."""
from __future__ import annotations

from conftest import login

CSRF = {"X-PayRay-CSRF": "1"}


def _clear_attempts(admin, username: str) -> None:
    admin.execute("DELETE FROM ops.login_attempt WHERE lower(username) = lower(%s)", (username,))


def test_login_me_logout(client, admin) -> None:
    _clear_attempts(admin, "officer1")
    r = login(client)
    assert r.status_code == 200, r.text
    me = client.get("/api/me")
    assert me.status_code == 200 and me.json()["role"] == "officer"
    assert client.post("/api/auth/logout", headers=CSRF).status_code == 200
    assert client.get("/api/me").status_code == 401


def test_cookie_flags(client, admin) -> None:
    _clear_attempts(admin, "officer1")
    r = login(client)
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "secure" in sc and "samesite=strict" in sc and "max-age=28800" in sc


def test_lockout_sixth_attempt_429(client, admin) -> None:
    _clear_attempts(admin, "officer2")
    codes = [login(client, "officer2", "salah-password").status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
    # Password benar pun ditolak selama terkunci.
    assert login(client, "officer2").status_code == 429
    _clear_attempts(admin, "officer2")


def test_generic_failure_body(client, admin) -> None:
    _clear_attempts(admin, "officer1")
    _clear_attempts(admin, "tidak_ada")
    a = login(client, "officer1", "salah")
    b = login(client, "tidak_ada", "salah")
    assert a.status_code == b.status_code == 401
    assert a.content == b.content
    _clear_attempts(admin, "officer1")
    _clear_attempts(admin, "tidak_ada")


def test_token_hash_differs_from_cookie(client, admin) -> None:
    _clear_attempts(admin, "officer1")
    login(client)
    cookie = client.cookies.get("payray_session")
    hashes = [r[0] for r in admin.execute("SELECT token_hash FROM ops.session").fetchall()]
    assert cookie and cookie not in hashes
    assert all(len(h) == 64 for h in hashes)


def test_failed_login_adds_one_audit_row(client, admin) -> None:
    _clear_attempts(admin, "officer1")
    before = admin.execute("SELECT count(*) FROM audit.event WHERE action = 'auth.login_failed'").fetchone()[0]
    login(client, "officer1", "salah")
    after = admin.execute("SELECT count(*) FROM audit.event WHERE action = 'auth.login_failed'").fetchone()[0]
    assert after - before == 1
    _clear_attempts(admin, "officer1")
