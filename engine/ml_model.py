"""Evaluator Python untuk model JSON yang sama dengan versi browser (dashboard/template.html predict()).

Urutan operasi meniru JS persis supaya |Δskor| ≤ 1e-6 (BUG-8).
"""
from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "artefak" / "model_payray.json"


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def model_version() -> str:
    return hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()


def raw_predict(model: dict, x: list[float | None]) -> float:
    s = model["base"]
    for t in model["trees"]:
        i = 0
        s += t["v"][0]
        while not t["leaf"][i]:
            f = t["f"][i]
            xv = x[f]
            if xv is None or (isinstance(xv, float) and math.isnan(xv)):
                j = t["l"][i] if t["m"][i] else t["r"][i]
            else:
                j = t["l"][i] if xv <= t["t"][i] else t["r"][i]
            s += t["v"][j] - t["v"][i]
            i = j
    return s


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def predict(model: dict, x: list[float | None], pr: float) -> float:
    """Peluang gabungan (stacking): sigmoid(a·clip(raw) + b·persentil_aturan + c)."""
    raw = raw_predict(model, x)
    z = max(-9.21, min(9.21, raw))
    st = model["stack"]
    return _sigmoid(st["ml"] * z + st["aturan"] * pr + st["c"])


def matrix(f: pd.DataFrame) -> list[list[float | None]]:
    from ml.model import matrix as ml_matrix

    X = ml_matrix(f)
    return [[None if (isinstance(v, float) and np.isnan(v)) else float(v) for v in row] for row in X.to_numpy()]
