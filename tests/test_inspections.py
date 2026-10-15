"""t17/t18: inspeksi (SEC-9, BUG-1, BUG-3, BUG-10, SEC-2 respons), supersede, cancel."""
from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from conftest import login

CSRF = {"X-PayRay-CSRF": "1"}
WIB = ZoneInfo("Asia/Jakarta")


def today() -> str:
    return datetime.now(WIB).date().isoformat()


def _login(client, admin, user="officer1"):
    admin.execute("DELETE FROM ops.login_attempt")
    assert login(client, user).status_code == 200


def _employer(admin, branch=1, rank=1) -> int:
    return admin.execute(
        "SELECT rs.employer_id FROM core.risk_score rs JOIN core.score_batch b ON b.id = rs.batch_id "
        "WHERE b.status = 'published' AND b.branch_id = %s AND rs.rank = %s", (branch, rank)).fetchone()[0]


@pytest.fixture()
def clean(admin):
    admin.execute("DELETE FROM label.inspection_outcome")
    admin.execute("UPDATE ops.inspection SET supersedes_id = NULL")
    admin.execute("DELETE FROM ops.inspection")
    yield
    admin.execute("DELETE FROM label.inspection_outcome")
    admin.execute("UPDATE ops.inspection SET supersedes_id = NULL")
    admin.execute("DELETE FROM ops.inspection")


def post(client, body, key=None):
    return client.post("/api/inspections", json=body,
                       headers={**CSRF, "Idempotency-Key": key or str(uuid.uuid4())})


def body(eid, **kw):
    return {"employer_id": eid, "inspected_on": today(), "outcome": "violation_found",
            "violation_types": ["under_reported_wage"], "rp_found": 12_500_000, "notes": "Cek slip gaji", **kw}


def test_submit_and_mine_without_outcome(client, admin, clean) -> None:
    _login(client, admin)
    eid = _employer(admin, rank=3)
    r = post(client, body(eid))
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "submitted"
    mine = client.get("/api/inspections/mine").json()["items"]
    assert len(mine) == 1 and "outcome" not in mine[0] and "notes" not in mine[0]
    q = client.get("/api/queue").json()["items"]
    assert [i for i in q if i["employer_id"] == eid][0]["inspection_status"] == "submitted"
    n = admin.execute("SELECT count(*) FROM audit.event WHERE action = 'inspection.submit'").fetchone()[0]
    assert n >= 1


def test_mass_assignment_rejected(client, admin, clean) -> None:
    _login(client, admin)
    r = post(client, {**body(_employer(admin)), "officer_id": 999})
    assert r.status_code == 422
    for extra in ({"branch_id": 2}, {"status": "cancelled"}):
        assert post(client, {**body(_employer(admin)), **extra}).status_code == 422


def test_business_rules_422(client, admin, clean) -> None:
    _login(client, admin)
    eid = _employer(admin)
    assert post(client, body(eid, violation_types=[])).status_code == 422
    assert post(client, body(eid, outcome="no_violation")).status_code == 422
    assert post(client, body(eid, outcome="no_violation", violation_types=[], rp_found=5)).status_code == 422
    assert post(client, body(eid, notes="x" * 1001)).status_code == 422
    assert post(client, body(eid, violation_types=["fraud"])).status_code == 422
    r = client.post("/api/inspections", json=body(eid), headers=CSRF)
    assert r.status_code == 422 and "Idempotency-Key" in r.json()["error"]["fields"]


def test_other_branch_404_and_supervisor_403(client, admin, clean) -> None:
    _login(client, admin)
    assert post(client, body(_employer(admin, branch=2))).status_code == 404
    _login(client, admin, "supervisor1")
    assert post(client, body(_employer(admin))).status_code == 403


def test_wib_month_boundary(client, admin, clean, monkeypatch) -> None:
    """BUG-1: 2026-01-31T17:30Z = 00:30 WIB 1 Feb."""
    from api import inspections

    batch = admin.execute("SELECT id, published_at FROM core.score_batch WHERE branch_id = 1 AND status = 'published'"
                          ).fetchone()
    admin.execute("UPDATE core.score_batch SET published_at = '2026-01-10T00:00:00Z' WHERE id = %s", (batch[0],))
    monkeypatch.setattr(inspections, "now_utc", lambda: datetime(2026, 1, 31, 17, 30, tzinfo=ZoneInfo("UTC")))
    try:
        _login(client, admin)
        eid = _employer(admin, rank=4)
        bad = post(client, body(eid, inspected_on="2026-02-02"))
        assert bad.status_code == 422
        ok = post(client, body(eid, inspected_on="2026-02-01"))
        assert ok.status_code == 201, ok.text
        assert ok.json()["period"] == "2026-02"
    finally:
        admin.execute("UPDATE core.score_batch SET published_at = %s WHERE id = %s", (batch[1], batch[0]))


def test_date_rules(client, admin, clean) -> None:
    _login(client, admin)
    eid = _employer(admin, rank=5)
    old = (date.fromisoformat(today()) - timedelta(days=31)).isoformat()
    assert post(client, body(eid, inspected_on=old)).status_code == 422
    future = (date.fromisoformat(today()) + timedelta(days=1)).isoformat()
    assert post(client, body(eid, inspected_on=future)).status_code == 422


def test_idempotency_same_key(client, admin, clean) -> None:
    _login(client, admin)
    eid = _employer(admin, rank=6)
    key = str(uuid.uuid4())
    a = post(client, body(eid), key)
    b = post(client, body(eid), key)
    assert a.status_code == 201 and b.status_code == 200 and a.json() == b.json()
    assert admin.execute("SELECT count(*) FROM ops.inspection WHERE employer_id = %s", (eid,)).fetchone()[0] == 1
    c = post(client, body(eid, notes="isi lain"), key)
    assert c.status_code == 422 and c.json()["error"]["code"] == "idempotency_mismatch"


def test_parallel_same_employer_period(app_db_url, client, admin, clean) -> None:
    """BUG-10: dua petugas (dua sesi) submit BU yang sama bersamaan → satu 201, satu 409."""
    from fastapi.testclient import TestClient

    from api.main import app

    _login(client, admin)
    eid = _employer(admin, rank=7)
    other = TestClient(app, base_url="https://testserver")
    admin.execute("DELETE FROM ops.login_attempt")
    admin.execute("INSERT INTO ops.app_user (username, password_hash, role, branch_id) "
                  "SELECT 'officer1b', password_hash, 'officer', 1 FROM ops.app_user WHERE username = 'officer1' "
                  "ON CONFLICT DO NOTHING")
    assert login(other, "officer1b").status_code == 200
    results: list[int] = []
    barrier = threading.Barrier(2)

    def go(c):
        barrier.wait()
        results.append(post(c, body(eid)).status_code)

    ts = [threading.Thread(target=go, args=(c,)) for c in (client, other)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sorted(results) == [201, 409]


def test_supersede_rules(client, admin, clean, monkeypatch) -> None:
    from api import inspections

    _login(client, admin)
    eid = _employer(admin, rank=8)
    first = post(client, body(eid)).json()
    r = client.post(f"/api/inspections/{first['id']}/supersede", json=body(eid, rp_found=1_000_000),
                    headers={**CSRF, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    rows = dict(admin.execute("SELECT id, status FROM ops.inspection WHERE employer_id = %s", (eid,)).fetchall())
    assert rows[first["id"]] == "superseded" and rows[r.json()["id"]] == "submitted"
    sup = admin.execute("SELECT supersedes_id FROM ops.inspection WHERE id = %s", (r.json()["id"],)).fetchone()[0]
    assert sup == first["id"]
    mine = client.get("/api/inspections/mine").json()["items"]
    assert "outcome" not in mine[0]

    # lewat 7×24 jam → 403
    new_id = r.json()["id"]
    later = datetime.now(ZoneInfo("UTC")) + timedelta(days=7, minutes=1)
    monkeypatch.setattr(inspections, "now_utc", lambda: later)
    r2 = client.post(f"/api/inspections/{new_id}/supersede", json=body(eid),
                     headers={**CSRF, "Idempotency-Key": str(uuid.uuid4())})
    assert r2.status_code == 403


def test_supersede_other_officer_403(client, admin, clean) -> None:
    _login(client, admin)
    eid = _employer(admin, rank=9)
    first = post(client, body(eid)).json()
    admin.execute("INSERT INTO ops.app_user (username, password_hash, role, branch_id) "
                  "SELECT 'officer1b', password_hash, 'officer', 1 FROM ops.app_user WHERE username = 'officer1' "
                  "ON CONFLICT DO NOTHING")
    _login(client, admin, "officer1b")
    r = client.post(f"/api/inspections/{first['id']}/supersede", json=body(eid),
                    headers={**CSRF, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 403
    assert client.post(f"/api/inspections/{first['id']}/cancel", json={"reason": "salah input data"},
                       headers=CSRF).status_code == 403


def test_cancel_rules(client, admin, clean) -> None:
    _login(client, admin)
    eid = _employer(admin, rank=10)
    first = post(client, body(eid)).json()
    _login(client, admin, "supervisor1")
    assert client.post(f"/api/inspections/{first['id']}/cancel", json={"reason": "123456789"},
                       headers=CSRF).status_code == 422
    ok = client.post(f"/api/inspections/{first['id']}/cancel", json={"reason": "Salah pilih BU saat input"},
                     headers=CSRF)
    assert ok.status_code == 200
    items = client.get("/api/inspections").json()["items"]
    row = [i for i in items if i["id"] == first["id"]][0]
    assert row["status"] == "cancelled" and row["outcome"] == "violation_found"
    _login(client, admin, "supervisor2")
    assert client.post(f"/api/inspections/{first['id']}/cancel", json={"reason": "Bukan cabang saya sendiri"},
                       headers=CSRF).status_code == 404
