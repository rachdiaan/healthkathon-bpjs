"""t22/t23: metrik supervisor (BUG-11, FR-27) dan audit log (FR-29)."""
from __future__ import annotations

import pytest

from conftest import login

CSRF = {"X-PayRay-CSRF": "1"}
PERIOD = "2026-09"


def _login(client, admin, user="supervisor1"):
    admin.execute("DELETE FROM ops.login_attempt")
    assert login(client, user).status_code == 200


def _wipe(admin):
    admin.execute("DELETE FROM label.inspection_outcome")
    admin.execute("UPDATE ops.inspection SET supersedes_id = NULL")
    admin.execute("DELETE FROM ops.inspection")


@pytest.fixture()
def fixture_inspections(admin):
    """6 violation, 4 no_violation, 2 inconclusive, 1 superseded, 1 cancelled di cabang 1, periode 2026-09."""
    _wipe(admin)
    batch = admin.execute("SELECT id FROM core.score_batch WHERE branch_id = 1 AND status = 'published'").fetchone()[0]
    officer = admin.execute("SELECT id FROM ops.app_user WHERE username = 'officer1'").fetchone()[0]
    emps = [r[0] for r in admin.execute("SELECT employer_id FROM core.risk_score WHERE batch_id = %s ORDER BY rank "
                                        "LIMIT 14", (batch,)).fetchall()]
    plan = (["violation_found"] * 6 + ["no_violation"] * 4 + ["inconclusive"] * 2
            + [("violation_found", "superseded"), ("violation_found", "cancelled")])
    for i, (eid, item) in enumerate(zip(emps, plan)):
        outcome, status = item if isinstance(item, tuple) else (item, "submitted")
        iid = admin.execute(
            "INSERT INTO ops.inspection (employer_id, branch_id, officer_id, batch_id, rank_at_selection, "
            "inspected_on, period, status, idempotency_key, cancel_reason) VALUES "
            "(%s, 1, %s, %s, %s, '2026-09-15', %s, %s, gen_random_uuid(), %s) RETURNING id",
            (eid, officer, batch, i + 1, PERIOD, status,
             "Salah input oleh petugas" if status == "cancelled" else None)).fetchone()[0]
        admin.execute("INSERT INTO label.inspection_outcome (inspection_id, outcome, violation_types) VALUES "
                      "(%s, %s, %s)", (iid, outcome, ["under_reported_wage"] if outcome == "violation_found" else []))
    yield
    _wipe(admin)


def test_baseline_script(seeded_db, admin) -> None:
    from scripts.compute_baseline import compute

    rows = compute(seeded_db, PERIOD)
    assert {r[0] for r in rows} == {1, 2}
    assert all(0 < float(r[1]) < 1 for r in rows)
    assert all(r[3] == f"ground_truth:synthetic@{PERIOD}" for r in rows)


def test_hit_rate_fixture(client, admin, seeded_db, fixture_inspections) -> None:
    from scripts.compute_baseline import compute

    compute(seeded_db, PERIOD)
    _login(client, admin)
    m = client.get("/api/metrics", params={"period": PERIOD}).json()
    assert m["hit_rate"] == 0.6 and m["n_decided"] == 10 and m["n_inconclusive"] == 2
    assert m["insufficient"] is False and m["baseline"] and m["lift"] == round(0.6 / m["baseline"], 2)
    assert m["baseline_label"] == "Baseline acak (prevalensi sintetis)" and m["computed_at"]
    assert 0 <= m["coverage_top10"] <= 1


def test_insufficient_when_denominator_9(client, admin, seeded_db, fixture_inspections) -> None:
    admin.execute("UPDATE ops.inspection SET status = 'cancelled', cancel_reason = 'Uji penyebut sembilan' "
                  "WHERE id = (SELECT i.id FROM ops.inspection i JOIN label.inspection_outcome o ON o.inspection_id = i.id "
                  "WHERE o.outcome = 'no_violation' AND i.status = 'submitted' LIMIT 1)")
    _login(client, admin)
    m = client.get("/api/metrics", params={"period": PERIOD}).json()
    assert m["n_decided"] == 9 and m["hit_rate"] is None and m["insufficient"] is True and m["lift"] is None


def test_officer_forbidden(client, admin) -> None:
    _login(client, admin, "officer1")
    assert client.get("/api/metrics").status_code == 403
    assert client.get("/api/audit-events").status_code == 403


def test_metrics_period_validation(client, admin) -> None:
    _login(client, admin)
    assert client.get("/api/metrics", params={"period": "2026-13"}).status_code == 422


def test_audit_filter_scope_limit_and_self_audit(client, admin) -> None:
    _login(client, admin, "officer1")
    client.get(f"/api/employers/{admin.execute('SELECT rs.employer_id FROM core.risk_score rs JOIN core.score_batch b ON b.id = rs.batch_id WHERE b.status = %s AND b.branch_id = 1 AND rs.rank = 1', ('published',)).fetchone()[0]}/scan-sheet")
    _login(client, admin)
    r = client.get("/api/audit-events", params={"action": "scan_sheet.view"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and all(i["action"] == "scan_sheet.view" for i in items)
    branches = {row[0] for row in admin.execute("SELECT DISTINCT branch_id FROM audit.event WHERE id = ANY(%s)",
                                                ([i["id"] for i in items],)).fetchall()}
    assert branches == {1}
    assert client.get("/api/audit-events", params={"limit": 101}).status_code == 422
    assert client.get("/api/audit-events", params={"action": "x;DROP"}).status_code == 422
    q = "SELECT count(*) FROM audit.event WHERE action = 'audit.read'"
    before = admin.execute(q).fetchone()[0]
    client.get("/api/audit-events")
    assert admin.execute(q).fetchone()[0] - before == 1


def test_supervisor_b_does_not_see_branch_a(client, admin) -> None:
    _login(client, admin, "supervisor2")
    ids = [i["id"] for i in client.get("/api/audit-events", params={"limit": 100}).json()["items"]]
    if ids:
        rows = admin.execute("SELECT DISTINCT branch_id FROM audit.event WHERE id = ANY(%s)", (ids,)).fetchall()
        assert {r[0] for r in rows} == {2}


def test_audit_cursor_paging(client, admin) -> None:
    _login(client, admin)
    p1 = client.get("/api/audit-events", params={"limit": 2}).json()
    assert len(p1["items"]) == 2 and p1["next_cursor"]
    p2 = client.get("/api/audit-events", params={"limit": 2, "cursor": p1["next_cursor"]}).json()
    assert max(i["id"] for i in p2["items"]) < min(i["id"] for i in p1["items"])
