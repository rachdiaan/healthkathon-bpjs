"""Server lokal: API konek sebagai payray_app (APP_DATABASE_URL di .env).

Role Postgres berlaku per cluster, dan fixture tes mengganti password payray_app di cluster
Docker yang sama. Karena itu password role disetel ulang dari .env (pakai DATABASE_URL admin)
setiap server dev start. Hanya untuk lokal; production memakai secret Render.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import sql
import uvicorn

ROOT = Path(__file__).resolve().parent.parent
env: dict[str, str] = {}
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    k, _, v = line.partition("=")
    if k and not k.startswith("#"):
        env[k.strip()] = v.strip()

app_url = env["APP_DATABASE_URL"]
with psycopg.connect(env["DATABASE_URL"], autocommit=True) as conn:
    pw = urlparse(app_url).password or ""
    conn.execute(sql.SQL("ALTER ROLE payray_app LOGIN PASSWORD {}").format(sql.Literal(pw)))

for k, v in env.items():
    os.environ.setdefault(k, v)
os.environ["DATABASE_URL"] = app_url
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
uvicorn.run("api.main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8765")), reload=False)
