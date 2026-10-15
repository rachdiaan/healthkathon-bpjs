"""Ekspor input model (x, persentil aturan) untuk 5.000 BU seed, lalu jalankan evaluator browser di Node.

    python scripts/make_reference_scores.py --data data
Hasil: ml/reference_scores.json (di-commit; dipakai tes paritas BUG-8).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import features, ml_model, score  # noqa: E402
from scripts.seed import employer_numeric_id  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    a = ap.parse_args()
    f = features.build(features.load(a.data))
    res, _ = score.run(f)
    pr = res.reindex(f.index).prioritas.rank(pct=True)
    X = ml_model.matrix(f)
    rows = [{"employer_id": employer_numeric_id(c), "x": X[i], "pr": float(pr.at[c])} for i, c in enumerate(f.index)]
    payload = {"source": "generator --seed 42 --inject-seed 4242 --n-employers 5000",
               "model_sha256": ml_model.model_version(), "rows": rows}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(payload, tmp)
    subprocess.run(["node", str(ROOT / "ml" / "reference_eval.mjs"), tmp.name,  # nosec B603 B607
                    str(ROOT / "ml" / "reference_scores.json")], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
