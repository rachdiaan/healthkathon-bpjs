"""Injeksi blind set (t31, FR-37/38, BR-20). DIJALANKAN OLEH PM (non-modeler), bukan tim model.

    PAYRAY_BLIND_SEED=... PAYRAY_BLIND_INJECT_SEED=... PAYRAY_NIK_KEY=... \
    MIGRATE_DATABASE_URL=... python scripts/inject_blind.py [--n 1000] [--period 2026-09]

* Seed dibaca dari env saja; tidak pernah dicetak, ditulis ke file, atau di-commit. Simpan di password manager PM.
* Menolak jalan bila ml/FROZEN.txt tidak ada atau hash artefak tidak cocok (model harus beku dulu).
* Menolak jalan bila data blind sudah ada (sekali saja).
* BU blind diberi kode BU9xxxx (id 90001+) supaya tidak bentrok dengan BU seed; NIK tetap di-HMAC.
* Dunia sintetis sementara ditulis ke folder temp lalu dihapus.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import seed as seed_mod  # noqa: E402

TABLES = ("core.employer", "core.worker", "core.employer_feature", "label.ground_truth")


def check_frozen() -> None:
    frozen = ROOT / "ml" / "FROZEN.txt"
    if not frozen.exists():
        raise SystemExit("ml/FROZEN.txt belum ada: bekukan model dulu (FR-37).")
    for line in frozen.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, path = line.split(None, 1)
        if hashlib.sha256((ROOT / path.strip()).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"Artefak {path.strip()} tidak cocok dengan ml/FROZEN.txt.")


def remap(world: Path) -> None:
    """BU00001 → BU90001 di semua CSV, supaya kode dan id tidak bentrok dengan BU seed."""
    pat = re.compile(r"\bBU0(\d{4})\b")
    for csv in world.rglob("*.csv"):
        text = csv.read_text(encoding="utf-8")
        csv.write_text(pat.sub(r"BU9\1", text), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--period", default=None)
    a = ap.parse_args()
    seed_world = os.environ.get("PAYRAY_BLIND_SEED")
    seed_inject = os.environ.get("PAYRAY_BLIND_INJECT_SEED")
    if not seed_world or not seed_inject:
        raise SystemExit("Set PAYRAY_BLIND_SEED dan PAYRAY_BLIND_INJECT_SEED (rahasia PM).")
    url = os.environ.get("MIGRATE_DATABASE_URL")
    if not url:
        raise SystemExit("Set MIGRATE_DATABASE_URL.")
    key = seed_mod.load_key()
    check_frozen()
    period = a.period or seed_mod.default_period()

    with psycopg.connect(url) as conn:
        if conn.execute("SELECT 1 FROM label.ground_truth WHERE dataset = 'blind' LIMIT 1").fetchone():
            raise SystemExit("Data blind sudah ada; injeksi hanya sekali.")
        row = conn.execute("SELECT coalesce(max(id), 0) FROM core.worker").fetchone()
        offset = int(row[0]) if row else 0

    tmp = Path(tempfile.mkdtemp(prefix="payray-blind-"))
    try:
        from generator.__main__ import main as gen_main

        rc = gen_main(["--out", str(tmp), "--n-employers", str(a.n), "--seed", seed_world,
                       "--inject-seed", seed_inject, "--skip-validate"])
        if rc != 0:
            raise SystemExit("Generator gagal.")
        remap(tmp)
        frames = seed_mod.build_frames(tmp, period, key, dataset="blind", worker_id_offset=offset)
        frames = {t: frames[t] for t in TABLES}
        seed_mod.seed(url, frames)
        n_emp = len(frames["core.employer"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"Blind set masuk: {n_emp} BU, periode {period}. Jumlah tidak patuh sengaja tidak dicetak.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
