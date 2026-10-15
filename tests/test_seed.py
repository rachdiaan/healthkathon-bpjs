"""t6: seeder sintetis, NIK HMAC (FR-4, SEC-7), user demo (BR-26)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent


def test_seed_rejects_short_key_before_writing(db_url: str, tmp_path: Path) -> None:
    env = {**os.environ, "PAYRAY_NIK_KEY": "x" * 31, "DATABASE_URL": db_url}
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "seed.py"), "--data", str(tmp_path / "kosong")],
                       env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert "minimal 32 byte" in (r.stdout + r.stderr)


def test_employers_seeded(seeded_db: str) -> None:
    with psycopg.connect(seeded_db) as conn:
        assert conn.execute("SELECT count(*) FROM core.employer").fetchone()[0] == 200
        assert conn.execute("SELECT count(DISTINCT branch_id) FROM core.employer").fetchone()[0] == 2


def test_no_raw_nik_anywhere(seeded_db: str) -> None:
    r"""SEC-7: regex \b\d{16}\b di semua kolom text/jsonb/char = 0 match."""
    with psycopg.connect(seeded_db) as conn:
        cols = conn.execute(
            "SELECT table_schema, table_name, column_name FROM information_schema.columns "
            "WHERE table_schema IN ('core','ops','label','audit') "
            "AND data_type IN ('text','jsonb','character','character varying','ARRAY')"
        ).fetchall()
        assert cols
        for schema, table, col in cols:
            n = conn.execute(
                f'SELECT count(*) FROM "{schema}"."{table}" WHERE "{col}"::text ~ %s', (r"\y[0-9]{16}\y",)
            ).fetchone()[0]
            assert n == 0, f"{schema}.{table}.{col} berisi pola NIK"


def test_nik_token_is_hmac_hex(seeded_db: str) -> None:
    with psycopg.connect(seeded_db) as conn:
        bad = conn.execute("SELECT count(*) FROM core.worker WHERE nik_token !~ '^[0-9a-f]{64}$'").fetchone()[0]
        assert bad == 0


def test_password_hash_is_scrypt(seeded_db: str) -> None:
    with psycopg.connect(seeded_db) as conn:
        rows = dict(conn.execute("SELECT username, password_hash FROM ops.app_user").fetchall())
        assert {"officer1", "supervisor1", "officer2", "supervisor2"} <= set(rows)
        assert all(h.startswith("scrypt$") for h in rows.values())
