"""t8: GR-2 route guard, CSRF (SEC-6), body limit (TC-1), CSP (SEC-4), rate limit."""
from __future__ import annotations

from fastapi.routing import APIRoute

from conftest import login

PUBLIC = {"/api/health", "/api/auth/login"}
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'"


def _has_role_guard(dependant) -> bool:
    if getattr(dependant.call, "__payray_roles__", None):
        return True
    return any(_has_role_guard(d) for d in dependant.dependencies)


def _flatten(routes):
    for r in routes:
        sub = getattr(r, "original_router", None)
        if sub is not None:
            yield from _flatten(sub.routes)
        else:
            yield r


def test_every_api_route_requires_role_except_public() -> None:
    from api.main import app

    api_routes = [r for r in _flatten(app.routes) if isinstance(r, APIRoute) and r.path.startswith("/api")]
    assert api_routes
    unguarded = {r.path for r in api_routes if not _has_role_guard(r.dependant)}
    assert unguarded == PUBLIC


def test_mutation_without_csrf_is_403(client, admin) -> None:
    admin.execute("DELETE FROM ops.login_attempt")
    assert login(client).status_code == 200
    r = client.post("/api/auth/logout")
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf"
    r = client.post("/api/auth/login", json={"username": "officer1", "password": "x"})
    assert r.status_code == 403


def test_body_70kb_is_413(client) -> None:
    big = b'{"username":"' + b"a" * 70_000 + b'","password":"x"}'
    r = client.post("/api/auth/login", content=big,
                    headers={"X-PayRay-CSRF": "1", "content-type": "application/json"})
    assert r.status_code == 413


def test_body_70kb_streamed_without_length_is_413(client) -> None:
    def gen():
        for _ in range(70):
            yield b"a" * 1024

    r = client.post("/api/auth/login", content=gen(),
                    headers={"X-PayRay-CSRF": "1", "content-type": "application/json"})
    assert r.status_code == 413


def test_html_has_csp_and_security_headers(client) -> None:
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert r.headers["content-security-policy"] == CSP
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["x-frame-options"] == "DENY"


def test_61st_request_in_a_minute_is_429(client, admin) -> None:
    admin.execute("DELETE FROM ops.login_attempt")
    assert login(client, "supervisor2").status_code == 200
    codes = [client.get("/api/me").status_code for _ in range(61)]
    assert codes[:60] == [200] * 60
    assert codes[60] == 429
