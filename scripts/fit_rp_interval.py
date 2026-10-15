"""Kalibrasi rentang Rp (FR-35) dari set TRAIN saja (BR-20, GR-11).

Rentang = rp_point × [q_lo, q_hi], dengan q = kuantil rasio kerugian_sebenarnya / rp_point
pada BU tidak patuh di set train. Hasil: ml/artefak/rp_interval.json.

    python scripts/fit_rp_interval.py --data data
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.eval_val import score_all  # noqa: E402

OUT = ROOT / "ml" / "artefak" / "rp_interval.json"
Q_LO, Q_HI = 0.10, 0.90


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    a = ap.parse_args()
    splits = json.loads((ROOT / "ml" / "splits.json").read_text(encoding="utf-8"))["assignment"]
    train = [c for c, ds in splits.items() if ds == "train"]
    lab = pd.read_csv(a.data / "label" / "labels.csv").set_index("employer_id").loc[train]
    res = score_all(a.data).join(lab, how="inner")
    nc = res[(res.is_violator == 1) & (res.rp_point > 0)]
    ratio = nc.iuran_tak_tertagih_tahun_terakhir.astype(float) / nc.rp_point.astype(float)
    out = {"method": "rp_point x kuantil rasio kerugian/rp_point, BU tidak patuh set train",
           "dataset": "train", "n": int(len(nc)),
           "q_lo": Q_LO, "q_hi": Q_HI,
           "factor_lo": round(float(np.quantile(ratio, Q_LO)), 4),
           "factor_hi": round(float(np.quantile(ratio, Q_HI)), 4)}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
