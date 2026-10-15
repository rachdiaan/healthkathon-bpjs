"""KILL-2: cek isolasi schema label di DB mana pun (lokal, CI, Neon).

    MIGRATE_DATABASE_URL=postgresql://owner:...@host/db python scripts/check_permissions.py
Keluar 0 bila payray_officer dan payray_scoring mendapat permission denied di label.*.
"""
from __future__ import annotations

import os
import sys

import psycopg
from psycopg import errors

CHECKS = [("payray_officer", "label.ground_truth"), ("payray_officer", "label.inspection_outcome"),
          ("payray_scoring", "label.ground_truth"), ("payray_scoring", "label.inspection_outcome")]


def main() -> int:
    url = os.environ.get("MIGRATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set MIGRATE_DATABASE_URL.")
    ok = True
    with psycopg.connect(url, autocommit=True) as conn:
        for role, table in CHECKS:
            try:
                with conn.transaction():
                    conn.execute(f"SET LOCAL ROLE {role}")
                    conn.execute(f"SELECT 1 FROM {table} LIMIT 1")  # nosec B608: nama tabel dari konstanta CHECKS
                print(f"GAGAL  {role} BISA membaca {table}")
                ok = False
            except errors.InsufficientPrivilege:
                print(f"LULUS  {role} -> {table}: permission denied")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
