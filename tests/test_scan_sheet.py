"""t14: scan sheet (SEC-1, FR-13 mode band, FR-15 token 8 karakter, audit)."""
from __future__ import annotations

import json
import re

from conftest import login


def _login(client, admin, user="officer1"):
    admin.execute("DELETE FROM ops.login_attempt")
    assert login(client, user).status_code == 200


def _top_id(admin, branch: int) -> int:
    return admin.execute("SELECT rs.employer_id FROM core.risk_score rs JOIN core.score_batch b ON b.id = rs.batch_id "
                         "WHERE b.status = 'published' AND b.branch_id = %s AND rs.rank = 1", (branch,)).fetchone()[0]


def test_scan_sheet_own_branch(client, admin) -> None:
    _login(client, admin)
    eid = _top_id(admin, 1)
    r = client.get(f"/api/employers/{eid}/scan-sheet")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rank"] == 1 and body["reasons"] and body["rp"]["mode"] == "range"
    contribs = [x["contribution"] for x in body["reasons"]]
    assert contribs == sorted(contribs, reverse=True)
    assert all(len(w["nik_token8"]) == 8 for w in body["flagged_workers"])


def test_other_branch_is_404(client, admin) -> None:
    _login(client, admin)
    assert client.get(f"/api/employers/{_top_id(admin, 2)}/scan-sheet").status_code == 404
    assert client.get("/api/employers/999999999/scan-sheet").status_code == 404


def test_no_64_hex_in_response(client, admin) -> None:
    _login(client, admin)
    for rank in (1, 2, 3):
        eid = admin.execute("SELECT rs.employer_id FROM core.risk_score rs JOIN core.score_batch b ON b.id = rs.batch_id "
                            "WHERE b.status = 'published' AND b.branch_id = 1 AND rs.rank = %s", (rank,)).fetchone()[0]
        text = json.dumps(client.get(f"/api/employers/{eid}/scan-sheet").json())
        assert not re.search(r"[0-9a-f]{64}", text)


def test_band_mode(client, admin, monkeypatch) -> None:
    monkeypatch.setenv("PAYRAY_RP_MODE", "band")
    _login(client, admin)
    rp = client.get(f"/api/employers/{_top_id(admin, 1)}/scan-sheet").json()["rp"]
    assert rp["mode"] == "band" and rp["low"] is None and rp["high"] is None and rp["band"] in ("rendah", "sedang", "tinggi")
    item = client.get("/api/queue").json()["items"][0]
    assert item["rp_low"] is None and item["rp_high"] is None


def test_each_view_audited(client, admin) -> None:
    _login(client, admin)
    q = "SELECT count(*) FROM audit.event WHERE action = 'scan_sheet.view'"
    before = admin.execute(q).fetchone()[0]
    client.get(f"/api/employers/{_top_id(admin, 1)}/scan-sheet")
    client.get(f"/api/employers/{_top_id(admin, 2)}/scan-sheet")  # 404, tidak diaudit sebagai view
    assert admin.execute(q).fetchone()[0] - before == 1
