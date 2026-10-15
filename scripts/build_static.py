"""Build statis GitHub Pages (FR-30, TC-9): web/ + data/snapshot.json, read-only.

    MIGRATE_DATABASE_URL=... python scripts/build_static.py [--branch 1] [--out web-static] [--dry-run]

Jalan sebagai role payray_scoring (tanpa akses schema label). Field snapshot memakai allowlist
eksplisit: tanpa label/ground truth, token NIK dipotong 8 karakter, tanpa data inspeksi.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent
DETAIL_TOP = 500
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'"
QUEUE_KEYS = ("rank", "employer_id", "name", "sector", "score", "confidence", "confidence_bucket", "reasons",
              "rp_low", "rp_high", "rp_band", "sme_protection", "verify_first")
FORBIDDEN_KEYS = re.compile(r'"(is_noncompliant|true_loss[a-z_]*|outcome|violation_types?|nik_token|ground_truth)"')


def snapshot(conn: psycopg.Connection[Any], branch_id: int, rp_mode: str) -> dict[str, Any]:
    batch = conn.execute(
        "SELECT b.id, b.period, b.published_at, b.model_version, br.name AS branch_name FROM core.score_batch b "
        "JOIN core.branch br ON br.id = b.branch_id WHERE b.branch_id = %s AND b.status = 'published'", (branch_id,),
    ).fetchone()
    if batch is None:
        raise SystemExit(f"Cabang {branch_id} belum punya batch published.")
    rows = conn.execute(
        "SELECT rs.rank, e.id AS employer_id, e.name, coalesce(s.name, e.kbli_sector) AS sector, e.kab_kota_code, "
        "e.reported_headcount, rs.score, rs.confidence, rs.confidence_bucket, rs.reason_codes, rs.rp_low, rs.rp_high, "
        "rs.rp_band, rs.sme_protection, rs.flagged_workers "
        "FROM core.risk_score rs JOIN core.employer e ON e.id = rs.employer_id "
        "LEFT JOIN core.sector s ON s.kbli = e.kbli_sector "
        "WHERE rs.batch_id = %s AND e.branch_id = %s ORDER BY rs.rank", (batch["id"], branch_id),
    ).fetchall()
    band = rp_mode == "band"
    items, details = [], {}
    for r in rows:
        verify = r["sme_protection"] and r["confidence_bucket"] == "rendah"
        item = {
            "rank": r["rank"], "employer_id": r["employer_id"], "name": r["name"], "sector": r["sector"],
            "score": round(r["score"], 4), "confidence": round(r["confidence"], 2),
            "confidence_bucket": r["confidence_bucket"],
            "reasons": [{"code": x["code"], "text": x["text"]} for x in r["reason_codes"][:2]],
            "rp_low": None if band else r["rp_low"], "rp_high": None if band else r["rp_high"],
            "rp_band": r["rp_band"], "sme_protection": r["sme_protection"], "verify_first": verify,
        }
        items.append({k: item[k] for k in QUEUE_KEYS})
        if r["rank"] <= DETAIL_TOP:
            details[str(r["employer_id"])] = {
                "employer": {"id": r["employer_id"], "name": r["name"], "sector": r["sector"],
                             "kab_kota": r["kab_kota_code"], "reported_headcount": r["reported_headcount"]},
                "rank": r["rank"], "score": item["score"], "confidence": item["confidence"],
                "confidence_bucket": r["confidence_bucket"],
                "reasons": [{"code": x["code"], "text": x["text"], "evidence": x.get("evidence", {}),
                             "contribution": x.get("contribution", 0), "checklist": x.get("checklist", [])}
                            for x in r["reason_codes"]],
                "rp": {"mode": rp_mode, "low": item["rp_low"], "high": item["rp_high"], "band": r["rp_band"]},
                "sme_protection": r["sme_protection"], "verify_first": verify,
                "flagged_workers": [{"nik_token8": str(w["nik_token8"])[:8], "reason": w["reason"]}
                                    for w in r["flagged_workers"]],
            }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "live_url": os.environ.get("PAYRAY_LIVE_URL", ""),
        "branch": {"id": branch_id, "name": batch["branch_name"]},
        "batch": {"id": batch["id"], "period": batch["period"], "published_at": batch["published_at"].isoformat()},
        "detail_top": DETAIL_TOP,
        "items": items,
        "details": details,
    }


def check_leaks(text: str) -> None:
    """SEC-7/SEC-8: gagal keras bila snapshot membawa label, token penuh, atau pola NIK."""
    if FORBIDDEN_KEYS.search(text):
        raise SystemExit("Snapshot mengandung key terlarang (label/token penuh).")
    if re.search(r"\b\d{16}\b", text):
        raise SystemExit("Snapshot mengandung pola NIK 16 digit.")
    if re.search(r"[0-9a-f]{64}", text):
        raise SystemExit("Snapshot mengandung string hex 64 karakter (token penuh/hash).")


def write_site(out: Path, snap: dict[str, Any]) -> Path:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "web", out)
    html = (out / "index.html").read_text(encoding="utf-8")
    html = html.replace('<html lang="id">', '<html lang="id" data-mode="static">', 1)
    html = html.replace('<meta charset="utf-8">',
                        f'<meta charset="utf-8">\n  <meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
                        '  <meta name="referrer" content="no-referrer">', 1)
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    data = out / "data"
    data.mkdir(exist_ok=True)
    text = json.dumps(snap, ensure_ascii=False, separators=(",", ":"))
    check_leaks(text)
    path = data / "snapshot.json"
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", type=int, default=1)
    ap.add_argument("--out", type=Path, default=ROOT / "web-static")
    ap.add_argument("--dry-run", action="store_true", help="Query + cek kebocoran tanpa menulis file")
    a = ap.parse_args()
    url = os.environ.get("STATIC_DATABASE_URL") or os.environ.get("MIGRATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set STATIC_DATABASE_URL (role payray_scoring) atau MIGRATE_DATABASE_URL.")
    rp_mode = "band" if os.environ.get("PAYRAY_RP_MODE", "range") == "band" else "range"
    with psycopg.connect(url, row_factory=dict_row) as conn:
        conn.execute("SET ROLE payray_scoring")
        has_batch = conn.execute("SELECT 1 FROM core.score_batch WHERE branch_id = %s AND status = 'published'",
                                 (a.branch,)).fetchone()
        if a.dry_run and not has_batch:
            print("build_static: dry-run, belum ada batch published (DB kosong) — koneksi + role OK")
            return 0
        snap = snapshot(conn, a.branch, rp_mode)
    text = json.dumps(snap, ensure_ascii=False, separators=(",", ":"))
    check_leaks(text)
    if a.dry_run:
        print(f"build_static: dry-run OK, {len(snap['items'])} item, {len(text) / 1024:.0f} KB")
        return 0
    path = write_site(a.out, snap)
    print(f"build_static: {path} ({path.stat().st_size / 1024:.0f} KB, {len(snap['items'])} item, "
          f"detail {len(snap['details'])} BU)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
