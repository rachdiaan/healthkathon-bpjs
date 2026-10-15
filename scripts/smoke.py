"""Smoke test terhadap URL live: /api/health, login officer demo, /api/queue 10 item, logout.

    PAYRAY_URL=https://payray.onrender.com PAYRAY_SMOKE_USER=officer1 PAYRAY_SMOKE_PASSWORD=... python scripts/smoke.py
"""
from __future__ import annotations

import os
import sys

import httpx


def main() -> int:
    base = os.environ.get("PAYRAY_URL", "http://127.0.0.1:8765").rstrip("/")
    user = os.environ.get("PAYRAY_SMOKE_USER", "officer1")
    pw = os.environ.get("PAYRAY_SMOKE_PASSWORD") or os.environ.get("PAYRAY_DEMO_PASSWORD")
    if not pw:
        raise SystemExit("Set PAYRAY_SMOKE_PASSWORD.")
    csrf = {"X-PayRay-CSRF": "1"}
    with httpx.Client(base_url=base, timeout=90, follow_redirects=False) as c:
        steps = []
        r = c.get("/api/health")
        steps.append(("health 200", r.status_code == 200 and r.json().get("status") == "ok"))
        r = c.post("/api/auth/login", json={"username": user, "password": pw}, headers=csrf)
        steps.append(("login 200", r.status_code == 200))
        token = r.cookies.get("payray_session")
        if token and base.startswith("http://"):
            # Cookie Secure tidak dikirim lewat http lokal; salin manual hanya untuk uji lokal.
            c.cookies.set("payray_session", token)
        r = c.get("/api/queue")
        items = r.json().get("items", []) if r.status_code == 200 else []
        steps.append(("queue 10 item", len(items) == 10))
        r = c.post("/api/auth/logout", headers=csrf)
        steps.append(("logout 200", r.status_code == 200))
        steps.append(("sesi habis setelah logout", c.get("/api/me").status_code == 401))
    for name, ok in steps:
        print(f"{'LULUS' if ok else 'GAGAL'}  {name}")
    return 0 if all(ok for _, ok in steps) else 1


if __name__ == "__main__":
    sys.exit(main())
