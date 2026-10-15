"""Baseline prevalensi per (cabang, periode) dari label.ground_truth → ops.metric_snapshot (BR-17).

    MIGRATE_DATABASE_URL=... python scripts/compute_baseline.py [--period 2026-10]

Jalan sebagai role payray_eval. Ground truth sintetis hanya ada untuk periode seed, jadi baseline
periode P memakai ground truth periode terbaru ≤ P; periode sumbernya dicatat di kolom `source`.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg

WIB = ZoneInfo("Asia/Jakarta")
SQL = """
WITH src AS (
    SELECT max(period) AS gt_period FROM label.ground_truth WHERE period <= %(period)s AND dataset <> 'blind'
)
INSERT INTO ops.metric_snapshot (branch_id, period, baseline_prevalence, n_active, computed_at, source)
SELECT e.branch_id, %(period)s,
       round(avg(g.is_noncompliant::int)::numeric, 5), count(*), now(),
       'ground_truth:synthetic@' || src.gt_period
FROM label.ground_truth g
JOIN core.employer e ON e.id = g.employer_id AND e.active
JOIN src ON g.period = src.gt_period
WHERE g.dataset <> 'blind'
GROUP BY e.branch_id, src.gt_period
ON CONFLICT (branch_id, period) DO UPDATE
SET baseline_prevalence = EXCLUDED.baseline_prevalence, n_active = EXCLUDED.n_active,
    computed_at = EXCLUDED.computed_at, source = EXCLUDED.source
RETURNING branch_id, baseline_prevalence, n_active, source
"""


def compute(url: str, period: str) -> list[tuple]:
    with psycopg.connect(url) as conn:
        conn.execute("SET ROLE payray_eval")
        return conn.execute(SQL, {"period": period}).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default=datetime.now(WIB).strftime("%Y-%m"))
    a = ap.parse_args()
    url = os.environ.get("MIGRATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set MIGRATE_DATABASE_URL.")
    for branch, base, n, src in compute(url, a.period):
        print(f"cabang {branch} periode {a.period}: baseline {base} dari {n} BU ({src})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
