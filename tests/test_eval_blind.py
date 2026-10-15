"""t32: eval_blind sekali saja, metrik BR-19, cek KILL-4/5."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def test_metrics_and_kill_flags() -> None:
    from scripts.eval_blind import metrics, to_md

    n = 100
    d = pd.DataFrame({
        "employer_id": range(1, n + 1),
        "score": [1 - i / n for i in range(n)],
        "rp_point": [1_000_000 * (n - i) for i in range(n)],
        "is_noncompliant": [i < 15 for i in range(n)],
        "violation_type": ["under_reported_wage" if i < 15 else "none" for i in range(n)],
        "true_loss_rp": [2_000_000 * (n - i) if i < 15 else 0 for i in range(n)],
        "is_labor_intensive": [i % 2 == 0 for i in range(n)],
    })
    m = metrics(d)
    assert m["k"] == 10 and m["p_at_10"] == 1.0 and m["lift"] > 2
    assert m["recall"]["under_reported_wage"]["recall_top10"] == round(10 / 15, 4)
    assert m["rp"]["spearman"] == 1.0 and not m["kill4_triggered"] and not m["kill5_triggered"]
    md = to_md(m, {"run_at": "x", "model_version": "a" * 64, "batches": [1]})
    for word in ("P@10%", "Spearman", "Pearson", "False flag padat karya", "KILL-4", "KILL-5"):
        assert word in md


def test_refuses_second_run(tmp_path, monkeypatch) -> None:
    out = ROOT / "docs" / "eval-blind.md"
    existed = out.exists()
    if not existed:
        out.write_text("hasil lama", encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_blind.py")], capture_output=True, text=True,
                           env={**os.environ, "MIGRATE_DATABASE_URL": "postgresql://x/y_test", "PYTHONIOENCODING": "utf-8"})
        assert r.returncode != 0 and "hanya boleh sekali" in (r.stdout + r.stderr)
        assert out.read_text(encoding="utf-8") == ("hasil lama" if not existed else out.read_text(encoding="utf-8"))
    finally:
        if not existed:
            out.unlink()


def test_refuses_without_blind_data(seeded_db) -> None:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_blind.py")], capture_output=True, text=True,
                       env={**os.environ, "MIGRATE_DATABASE_URL": seeded_db, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode != 0 and "Belum ada data blind" in (r.stdout + r.stderr)
    assert not (ROOT / "docs" / "eval-blind.md").exists()
