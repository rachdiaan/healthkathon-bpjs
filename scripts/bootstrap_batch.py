"""Buat batch pertama `published` per cabang (Fase 1, sebelum endpoint rescore ada di t20/t21).

    python scripts/bootstrap_batch.py [--period 2026-09]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import ml_model  # noqa: E402
from engine.score_batch import score_batch  # noqa: E402
from scripts.seed import default_period  # noqa: E402


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, capture_output=True,  # nosec B603 B607
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return os.environ.get("GIT_SHA", "unknown")


def bootstrap(url: str, period: str) -> list[tuple[int, int]]:
    out = []
    with psycopg.connect(url) as conn:
        branches = [r[0] for r in conn.execute("SELECT id FROM core.branch ORDER BY id").fetchall()]
        for b in branches:
            with conn.transaction():
                conn.execute("SET LOCAL ROLE payray_migrator")
                bid = conn.execute(
                    "INSERT INTO core.score_batch (branch_id, period, status, model_version, engine_version) "
                    "VALUES (%s, %s, 'running', %s, %s) RETURNING id",
                    (b, period, ml_model.model_version(), git_sha()),
                ).fetchone()
                assert bid is not None
                bid = bid[0]
            with conn.transaction():
                conn.execute("SET LOCAL ROLE payray_scoring")
                n = score_batch(conn, bid)
            with conn.transaction():
                conn.execute("SET LOCAL ROLE payray_migrator")
                conn.execute("UPDATE core.score_batch SET status = 'archived' "
                             "WHERE branch_id = %s AND status = 'published'", (b,))
                conn.execute("UPDATE core.score_batch SET status = 'published', published_at = now() WHERE id = %s",
                             (bid,))
            out.append((b, n))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default=None)
    a = ap.parse_args()
    url = os.environ.get("MIGRATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set DATABASE_URL.")
    for b, n in bootstrap(url, a.period or default_period()):
        print(f"cabang {b}: {n:,} BU diskor, batch published")
    return 0


if __name__ == "__main__":
    sys.exit(main())
