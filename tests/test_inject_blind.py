"""t31: injeksi blind (seed dari env, model harus beku, hanya sekali, NIK tetap HMAC)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(db_url: str, **extra: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "MIGRATE_DATABASE_URL": db_url, "PAYRAY_NIK_KEY": "k" * 48,
           "PAYRAY_BLIND_SEED": "987654321", "PAYRAY_BLIND_INJECT_SEED": "123454321", "PYTHONIOENCODING": "utf-8", **extra}
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "inject_blind.py"), "--n", "40"],
                          env=env, capture_output=True, text=True, timeout=600)


def test_requires_seed_env(seeded_db) -> None:
    r = _run(seeded_db, PAYRAY_BLIND_SEED="")
    assert r.returncode != 0 and "PAYRAY_BLIND_SEED" in (r.stdout + r.stderr)


def test_inject_once_and_cleanup(seeded_db, admin) -> None:
    try:
        r = _run(seeded_db)
        assert r.returncode == 0, r.stderr[-2000:]
        n = admin.execute("SELECT count(*) FROM label.ground_truth WHERE dataset = 'blind'").fetchone()[0]
        assert n == 40
        assert admin.execute("SELECT min(id) FROM core.employer e JOIN label.ground_truth g ON g.employer_id = e.id "
                             "WHERE g.dataset = 'blind'").fetchone()[0] >= 90001
        bad = admin.execute("SELECT count(*) FROM core.worker WHERE nik_token !~ '^[0-9a-f]{64}$'").fetchone()[0]
        assert bad == 0
        assert "987654321" not in r.stdout + r.stderr and "123454321" not in r.stdout + r.stderr
        again = _run(seeded_db)
        assert again.returncode != 0 and "sekali" in (again.stdout + again.stderr)
    finally:
        ids = "(SELECT employer_id FROM label.ground_truth WHERE dataset = 'blind')"
        admin.execute(f"DELETE FROM core.worker WHERE employer_id IN {ids}")
        admin.execute(f"DELETE FROM core.employer_feature WHERE employer_id IN {ids}")
        admin.execute(f"DELETE FROM core.risk_score WHERE employer_id IN {ids}")
        admin.execute("CREATE TEMP TABLE b AS SELECT employer_id FROM label.ground_truth WHERE dataset = 'blind'")
        admin.execute("DELETE FROM label.ground_truth WHERE dataset = 'blind'")
        admin.execute("DELETE FROM core.employer WHERE id IN (SELECT employer_id FROM b)")


def test_no_blind_seed_in_repo() -> None:
    """Kriteria t31: grep repo tidak menemukan nilai seed blind. Seed asli tidak ada di repo;
    tes ini memastikan tidak ada env seed yang ditulis literal di kode/konfigurasi."""
    pat = re.compile(r"PAYRAY_BLIND(_INJECT)?_SEED\s*=\s*['\"]?\d+")
    hits = []
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in {".py", ".yml", ".yaml", ".md", ".txt", ".json", ".toml", ".example"} \
                and ".venv" not in p.parts and "data" not in p.parts and p.name != "test_inject_blind.py":
            if pat.search(p.read_text(encoding="utf-8", errors="ignore")):
                hits.append(str(p))
    assert hits == []
