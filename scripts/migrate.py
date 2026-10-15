"""Migrasi forward-only: jalankan db/migrations/NNN_*.sql yang belum tercatat.

Koneksi memakai MIGRATE_DATABASE_URL (atau DATABASE_URL) milik admin DB. Script
memastikan role pemilik `payray_migrator` ada, lalu setiap migrasi jalan dengan
`SET ROLE payray_migrator` sehingga semua objek dimiliki role itu.

    python scripts/migrate.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).resolve().parent.parent / "db" / "migrations"

BOOTSTRAP = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'payray_migrator') THEN
        CREATE ROLE payray_migrator NOLOGIN CREATEROLE;
    END IF;
END $$;
GRANT payray_migrator TO CURRENT_USER;
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version     text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
);
"""


def migrate(url: str) -> list[str]:
    applied: list[str] = []
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(BOOTSTRAP)
        dbname = conn.info.dbname
        conn.execute(f'GRANT CREATE, CONNECT ON DATABASE "{dbname}" TO payray_migrator')
        done = {r[0] for r in conn.execute("SELECT version FROM public.schema_migrations")}
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute("SET LOCAL ROLE payray_migrator")
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("RESET ROLE")
                conn.execute("INSERT INTO public.schema_migrations (version) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied


def main() -> int:
    url = os.environ.get("MIGRATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("Set MIGRATE_DATABASE_URL atau DATABASE_URL.", file=sys.stderr)
        return 2
    applied = migrate(url)
    print("Migrasi diterapkan:", ", ".join(applied) if applied else "(tidak ada, sudah terbaru)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
