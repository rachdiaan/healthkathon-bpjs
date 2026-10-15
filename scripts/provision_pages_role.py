"""Aktifkan login role payray_pages dan cetak URL-nya ke .env (bukan ke layar).

    python scripts/provision_pages_role.py            # memakai MIGRATE_DATABASE_URL dari env/.env
Hasil: PAGES_DATABASE_URL di .env lokal, siap disalin ke secret GitHub `PAGES_DATABASE_URL` oleh admin repo.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    env_path = ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    env = dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))
    owner = os.environ.get("MIGRATE_DATABASE_URL") or env.get("NEON_OWNER_URL")
    if not owner:
        raise SystemExit("Set MIGRATE_DATABASE_URL atau NEON_OWNER_URL di .env.")
    pw = env.get("PAGES_PASSWORD") or secrets.token_urlsafe(24)
    with psycopg.connect(owner, autocommit=True) as conn:
        conn.execute("SET ROLE payray_migrator")
        conn.execute(sql.SQL("ALTER ROLE payray_pages LOGIN PASSWORD {}").format(sql.Literal(pw)))
    u = urlparse(owner)
    url = f"postgresql://payray_pages:{pw}@{u.hostname}{':' + str(u.port) if u.port else ''}{u.path}?sslmode=require"
    keep = [ln for ln in lines if not ln.startswith(("PAGES_PASSWORD=", "PAGES_DATABASE_URL="))]
    env_path.write_text("\n".join([*keep, f"PAGES_PASSWORD={pw}", f"PAGES_DATABASE_URL={url}"]) + "\n", encoding="utf-8")
    print("payray_pages aktif; PAGES_DATABASE_URL ditulis ke .env (tidak dicetak).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
