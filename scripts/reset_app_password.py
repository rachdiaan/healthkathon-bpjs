"""Lokal saja: setel password payray_app dari APP_DATABASE_URL di .env (fixture tes menggantinya di cluster yang sama)."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
env = dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
           if "=" in line and not line.startswith("#"))
with psycopg.connect(env["DATABASE_URL"], autocommit=True) as conn:
    pw = urlparse(env["APP_DATABASE_URL"]).password or ""
    conn.execute(sql.SQL("ALTER ROLE payray_app LOGIN PASSWORD {}").format(sql.Literal(pw)))
print("password payray_app disetel dari .env")
