"""Buat akun demo officer + supervisor per cabang (BR-26). Tidak ada self-registration.

    PAYRAY_DEMO_PASSWORD=... python scripts/seed_users.py

Username: officer<branch_id>, supervisor<branch_id>. Password diambil dari env
(minimal 12 karakter) dan tidak pernah ditulis ke repo atau log.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.security import hash_password  # noqa: E402


def seed_users(url: str, password: str) -> list[str]:
    created = []
    with psycopg.connect(url) as conn:
        conn.execute("SET ROLE payray_migrator")
        for (branch_id,) in conn.execute("SELECT id FROM core.branch ORDER BY id").fetchall():
            for role in ("officer", "supervisor"):
                username = f"{role}{branch_id}"
                cur = conn.execute(
                    "INSERT INTO ops.app_user (username, password_hash, role, branch_id) VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (lower(username)) DO NOTHING",
                    (username, hash_password(password), role, branch_id),
                )
                if cur.rowcount:
                    created.append(username)
    return created


def main() -> int:
    password = os.environ.get("PAYRAY_DEMO_PASSWORD", "")
    if len(password) < 12:
        raise SystemExit("Set PAYRAY_DEMO_PASSWORD (minimal 12 karakter).")
    url = os.environ.get("MIGRATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set DATABASE_URL.")
    created = seed_users(url, password)
    print("User dibuat:", ", ".join(created) if created else "(sudah ada)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
