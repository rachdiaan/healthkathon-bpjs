"""t20/t21: rescore (SEC-12, SEC-3, BR-15), publish atomik, recovery batch basi (BUG-6, TC-5)."""
from __future__ import annotations

import threading
import time

import pytest

from conftest import login

CSRF = {"X-PayRay-CSRF": "1"}


def _login(client, admin, user="supervisor1"):
    admin.execute("DELETE FROM ops.login_attempt")
    assert login(client, user).status_code == 200


@pytest.fixture()
def no_gap(admin):
    """Batch lama dimundurkan supaya aturan jeda 5 menit tidak menghalangi tes lain."""
    admin.execute("UPDATE core.score_batch SET created_at = created_at - interval '1 hour'")
    admin.execute("UPDATE core.score_batch SET status = 'failed' WHERE status = 'running'")
    yield
    admin.execute("UPDATE core.score_batch SET created_at = created_at - interval '1 hour'")
    admin.execute("UPDATE core.score_batch SET status = 'failed' WHERE status = 'running'")


def _wait(client, bid, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = client.get(f"/api/rescore-batches/{bid}").json()["status"]
        if st != "running":
            return st
        time.sleep(0.3)
    return "running"


def test_officer_forbidden(client, admin, no_gap) -> None:
    _login(client, admin, "officer1")
    assert client.post("/api/rescore-batches", json={"period": "2026-09"}, headers=CSRF).status_code == 403
    assert client.get("/api/rescore-batches").status_code == 403


def test_period_validation(client, admin, no_gap) -> None:
    _login(client, admin)
    for p in ("2026-13", "2026-9", "2026-00", "1;DROP", "2999-01"):
        assert client.post("/api/rescore-batches", json={"period": p}, headers=CSRF).status_code == 422


def test_parallel_one_202_one_409(app_db_url, client, admin, no_gap, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from api import batches
    from api.main import app

    # Tahan background scoring supaya batch pertama tetap running saat request kedua datang.
    gate = threading.Event()
    real = batches.run_rescore
    monkeypatch.setattr(batches, "run_rescore", lambda bid, fa=None: (gate.wait(10), real(bid, fa)))
    _login(client, admin)
    other = TestClient(app, base_url="https://testserver")
    assert login(other, "supervisor2").status_code == 200
    codes: list[int] = []
    barrier = threading.Barrier(2)

    def go(c):
        barrier.wait()
        codes.append(c.post("/api/rescore-batches", json={"period": "2026-09"}, headers=CSRF).status_code)

    ts = [threading.Thread(target=go, args=(c,)) for c in (client, other)]
    for t in ts:
        t.start()
    time.sleep(1.5)
    gate.set()
    for t in ts:
        t.join()
    assert sorted(codes) == [202, 409]


def test_too_soon_429(client, admin, no_gap) -> None:
    _login(client, admin)
    r = client.post("/api/rescore-batches", json={"period": "2026-09"}, headers=CSRF)
    assert r.status_code == 202
    assert _wait(client, r.json()["id"]) == "ready"
    r2 = client.post("/api/rescore-batches", json={"period": "2026-09"}, headers=CSRF)
    assert r2.status_code == 429 and r2.json()["error"]["code"] == "too_soon"


def test_rescore_ready_and_publish_atomic(client, admin, no_gap) -> None:
    _login(client, admin)
    t0 = time.time()
    r = client.post("/api/rescore-batches", json={"period": "2026-09"}, headers=CSRF)
    bid = r.json()["id"]
    assert _wait(client, bid) == "ready"
    assert time.time() - t0 <= 60
    detail = client.get(f"/api/rescore-batches/{bid}").json()
    assert detail["n_scored"] > 0 and "new_in_top10" in detail["summary"]
    assert len(detail["model_version"]) == 64 and detail["engine_version"]
    pub = client.post(f"/api/rescore-batches/{bid}/publish", headers=CSRF)
    assert pub.status_code == 200
    n = admin.execute("SELECT count(*) FROM core.score_batch WHERE branch_id = 1 AND status = 'published'").fetchone()[0]
    assert n == 1
    assert client.get("/api/queue").json()["batch"]["id"] == bid
    assert admin.execute("SELECT count(*) FROM audit.event WHERE action = 'batch.publish'").fetchone()[0] >= 1


def test_failure_keeps_old_queue(client, admin, no_gap, monkeypatch) -> None:
    """BUG-6: exception di tengah scoring → batch failed, antrean tetap batch lama."""
    from api import batches

    _login(client, admin)
    old = client.get("/api/queue").json()["batch"]["id"]
    monkeypatch.setattr(batches, "TEST_FAIL_AT", 50)  # DB uji berisi 200 BU; setara BU ke-2.500 dari 5.000
    r = client.post("/api/rescore-batches", json={"period": "2026-09"}, headers=CSRF)
    bid = r.json()["id"]
    assert _wait(client, bid) == "failed"
    detail = client.get(f"/api/rescore-batches/{bid}").json()
    assert "kegagalan uji" in detail["error"]
    assert admin.execute("SELECT count(*) FROM core.risk_score WHERE batch_id = %s", (bid,)).fetchone()[0] == 0
    assert client.get("/api/queue").json()["batch"]["id"] == old
    assert client.post(f"/api/rescore-batches/{bid}/publish", headers=CSRF).status_code == 409


def test_stale_running_marked_failed_on_startup(client, admin, no_gap) -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    bid = admin.execute(
        "INSERT INTO core.score_batch (branch_id, period, status, model_version, engine_version, created_at) "
        "VALUES (1, '2026-09', 'running', repeat('a', 64), 'test', now() - interval '11 minutes') RETURNING id"
    ).fetchone()[0]
    with TestClient(app, base_url="https://testserver"):
        pass  # lifespan startup menjalankan recovery
    assert admin.execute("SELECT status FROM core.score_batch WHERE id = %s", (bid,)).fetchone()[0] == "failed"


def test_other_branch_batch_404(client, admin, no_gap) -> None:
    _login(client, admin, "supervisor2")
    bid = admin.execute("SELECT id FROM core.score_batch WHERE branch_id = 1 ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert client.get(f"/api/rescore-batches/{bid}").status_code == 404
    assert client.post(f"/api/rescore-batches/{bid}/publish", headers=CSRF).status_code == 404
