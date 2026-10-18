"""t10/t11: antrean (SEC-1, SEC-3, BUG-4) dan ekspor CSV (SEC-10, BR-22)."""
from __future__ import annotations

import csv
import io

from conftest import login


def _login(client, admin, user="officer1"):
    admin.execute("DELETE FROM ops.login_attempt")
    assert login(client, user).status_code == 200


def test_queue_default_10_from_own_branch(client, admin) -> None:
    _login(client, admin)
    r = client.get("/api/queue")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 10 and body["next_cursor"]
    assert [i["rank"] for i in body["items"]] == list(range(1, 11))
    ids = [i["employer_id"] for i in body["items"]]
    branches = {row[0] for row in admin.execute("SELECT DISTINCT branch_id FROM core.employer WHERE id = ANY(%s)",
                                                 (ids,)).fetchall()}
    assert branches == {1}
    item = body["items"][0]
    assert len(item["reasons"]) <= 3 and "nik_token" not in str(item)


def test_queue_officer_branch2_sees_only_branch2(client, admin) -> None:
    _login(client, admin, "officer2")
    ids = [i["employer_id"] for i in client.get("/api/queue?limit=100").json()["items"]]
    rows = admin.execute("SELECT DISTINCT branch_id FROM core.employer WHERE id = ANY(%s)", (ids,)).fetchall()
    assert {r[0] for r in rows} == {2}


def test_cursor_injection_422(client, admin) -> None:
    _login(client, admin)
    assert client.get("/api/queue", params={"cursor": "1;DROP TABLE"}).status_code == 422
    assert client.get("/api/queue", params={"limit": 101}).status_code == 422
    assert client.get("/api/queue", params={"limit": 0}).status_code == 422


def test_cursor_locked_to_batch_after_new_publish(client, admin, seeded_db) -> None:
    from scripts.bootstrap_batch import bootstrap

    _login(client, admin)
    p1 = client.get("/api/queue").json()
    old_batch = p1["batch"]["id"]
    bootstrap(seeded_db, "2026-09")  # batch baru dipublikasikan di tengah paging
    p2 = client.get("/api/queue", params={"cursor": p1["next_cursor"]}).json()
    assert p2["batch"]["id"] == old_batch
    assert [i["rank"] for i in p2["items"]] == list(range(11, 21))
    assert not {i["employer_id"] for i in p1["items"]} & {i["employer_id"] for i in p2["items"]}
    assert client.get("/api/queue").json()["batch"]["id"] != old_batch


def test_csv_export(client, admin) -> None:
    _login(client, admin)
    admin.execute("UPDATE core.employer SET name = '=HYPERLINK(\"http://x\")' WHERE id = "
                  "(SELECT employer_id FROM core.risk_score rs JOIN core.score_batch b ON b.id = rs.batch_id "
                  " WHERE b.status = 'published' AND b.branch_id = 1 AND rs.rank = 1)")
    before = admin.execute("SELECT count(*) FROM audit.event WHERE action = 'export.queue_csv'").fetchone()[0]
    r = client.get("/api/queue.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.text)))
    header, data = rows[0], rows[1:]
    assert "nik_token" not in header and not any("label" in h or "outcome" in h for h in header)
    assert 0 < len(data) <= 500
    assert data[0][2].startswith("'=HYPERLINK(")
    after = admin.execute("SELECT count(*) FROM audit.event WHERE action = 'export.queue_csv'").fetchone()[0]
    assert after - before == 1


def test_summary_matches_queue(client, admin) -> None:
    _login(client, admin)
    s = client.get("/api/summary").json()
    assert s["batch"]["id"] == client.get("/api/queue").json()["batch"]["id"]
    assert s["n"] == sum(s["confidence"].values()) == sum(s["score_hist"])
    assert s["top_n"] == -(-s["n"] // 10)
    assert s["rp_top10"]["low"] <= s["rp_top10"]["high"] <= s["rp_top100"]["high"]
    assert "nik_token" not in str(s)
