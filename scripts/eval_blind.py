"""Evaluasi blind SEKALI SAJA (FR-38, BR-19, BR-20). Satu-satunya script yang boleh membaca dataset blind (GR-11).

    MIGRATE_DATABASE_URL=... python scripts/eval_blind.py

Syarat sebelum jalan:
* docs/eval-blind.md belum ada (run kedua ditolak, file tidak ditimpa).
* Blind set sudah diinjeksi PM (label.ground_truth dataset='blind').
* Skor BU blind ada di batch published, dan model_version batch = hash model di ml/FROZEN.txt.
Hasil ditulis apa adanya, termasuk bila lebih buruk dari validation. KILL-4/KILL-5 dicek otomatis.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eval-blind.md"
TYPES = ("under_reported_wage", "partial_registration", "ppu_to_pbpu_shift")
KILL4_MIN_LIFT = 2.0
KILL5_MIN_SPEARMAN = 0.40


def frozen_model_hash() -> str:
    for line in (ROOT / "ml" / "FROZEN.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and line.strip().endswith("model_payray.json"):
            return line.split()[0]
    raise SystemExit("Hash model tidak ada di ml/FROZEN.txt.")


def metrics(d: pd.DataFrame) -> dict[str, Any]:
    """d: satu baris per BU blind: score, rp_point, is_noncompliant, violation_type, true_loss_rp, is_labor_intensive."""
    n = len(d)
    k = math.ceil(0.10 * n)
    top = d.sort_values(["score", "employer_id"], ascending=[False, True]).head(k)
    y = d.is_noncompliant.astype(bool)
    prev = float(y.mean())
    p10 = float(top.is_noncompliant.astype(bool).mean())
    recall = {}
    for t in TYPES:
        has = d.violation_type == t
        recall[t] = {"n": int(has.sum()),
                     "recall_top10": round(float(has[top.index].sum() / has.sum()), 4) if has.sum() else None}
    pk = d.is_labor_intensive.astype(bool) & ~y
    nc = d[y]
    sp = float(spearmanr(nc.rp_point, nc.true_loss_rp).statistic) if len(nc) > 2 else float("nan")
    pe = float(pearsonr(nc.rp_point, nc.true_loss_rp).statistic) if len(nc) > 2 else float("nan")
    lift = p10 / prev if prev else float("nan")
    return {
        "n": n, "k": k, "prevalensi": round(prev, 4), "p_at_10": round(p10, 4), "lift": round(lift, 3),
        "recall": recall,
        "false_flag_padat_karya": {"n_patuh_padat_karya": int(pk.sum()), "di_top10": int(pk[top.index].sum()),
                                   "rate": round(float(pk[top.index].sum() / pk.sum()), 4) if pk.sum() else None},
        "rp": {"n_noncompliant": int(len(nc)), "spearman": round(sp, 4), "pearson": round(pe, 4)},
        "kill4_triggered": bool(lift < KILL4_MIN_LIFT),
        "kill5_triggered": bool(sp < KILL5_MIN_SPEARMAN),
    }


def pct(v: float | None) -> str:
    return "-" if v is None else f"{v:.1%}"


def to_md(m: dict[str, Any], meta: dict[str, Any]) -> str:
    ff = m["false_flag_padat_karya"]
    L = ["# Evaluasi blind (satu kali run)", "",
         f"Dijalankan {meta['run_at']} UTC. Model `{meta['model_version'][:12]}…` (= ml/FROZEN.txt), "
         f"batch {meta['batches']}. Hasil ditulis apa adanya; tidak ada perubahan model setelah run ini (BR-20).", "",
         "| Metrik | Nilai | Ambang |", "|---|---|---|",
         f"| P@10% | {m['p_at_10']:.1%} (K = {m['k']} dari N = {m['n']}) | - |",
         f"| Lift vs prevalensi ({m['prevalensi']:.1%}) | {m['lift']}× | KILL-4 bila < {KILL4_MIN_LIFT}× |",
         f"| False flag padat karya patuh di top 10% | {pct(ff['rate'])} "
         f"({ff['di_top10']} dari {ff['n_patuh_padat_karya']}) | M-7 ≤ 3% |",
         f"| Spearman Rp | {m['rp']['spearman']} | KILL-5 bila < {KILL5_MIN_SPEARMAN} |",
         f"| Pearson Rp | {m['rp']['pearson']} | dilaporkan |", "",
         "| Tipe | n | Recall top 10% |", "|---|---|---|"]
    L += [f"| {t} | {v['n']} | {pct(v['recall_top10'])} |" for t, v in m["recall"].items()]
    L += ["", f"- KILL-4 (lift < {KILL4_MIN_LIFT}×): **{'TERPICU' if m['kill4_triggered'] else 'tidak terpicu'}**",
          f"- KILL-5 (Spearman < {KILL5_MIN_SPEARMAN}): **{'TERPICU' if m['kill5_triggered'] else 'tidak terpicu'}**"
          + (" → set `PAYRAY_RP_MODE=band` di Render dan hapus angka Rp tunggal dari deck." if m["kill5_triggered"] else ""),
          "", "```json", json.dumps({"meta": meta, "metrics": m}, indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(L)


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"{OUT.relative_to(ROOT)} sudah ada. Evaluasi blind hanya boleh sekali (FR-38).")
    url = os.environ.get("MIGRATE_DATABASE_URL")
    if not url:
        raise SystemExit("Set MIGRATE_DATABASE_URL.")
    model = frozen_model_hash()
    with psycopg.connect(url) as conn:
        conn.execute("SET ROLE payray_eval")
        rows = conn.execute(
            "SELECT g.employer_id, rs.score, rs.rp_point, g.is_noncompliant, g.violation_type, g.true_loss_rp, "
            "e.is_labor_intensive, b.id AS batch_id, b.model_version "
            "FROM label.ground_truth g JOIN core.employer e ON e.id = g.employer_id "
            "JOIN core.risk_score rs ON rs.employer_id = g.employer_id "
            "JOIN core.score_batch b ON b.id = rs.batch_id AND b.status = 'published' "
            "WHERE g.dataset = 'blind'"
        ).fetchall()
        row = conn.execute("SELECT count(*) FROM label.ground_truth WHERE dataset = 'blind'").fetchone()
        n_blind = row[0] if row else 0
    if n_blind == 0:
        raise SystemExit("Belum ada data blind (PM menjalankan scripts/inject_blind.py dulu).")
    d = pd.DataFrame(rows, columns=["employer_id", "score", "rp_point", "is_noncompliant", "violation_type",
                                    "true_loss_rp", "is_labor_intensive", "batch_id", "model_version"])
    if len(d) != n_blind:
        raise SystemExit(f"Hanya {len(d)} dari {n_blind} BU blind punya skor di batch published. Rescore + publish dulu.")
    versions = set(d.model_version.str.strip())
    if versions != {model}:
        raise SystemExit("model_version batch published tidak sama dengan ml/FROZEN.txt.")
    m = metrics(d)
    meta = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model_version": model,
            "batches": sorted(int(b) for b in d.batch_id.unique())}
    OUT.write_text(to_md(m, meta), encoding="utf-8")
    print(f"Ditulis {OUT.relative_to(ROOT)}. KILL-4 {'TERPICU' if m['kill4_triggered'] else 'aman'}, "
          f"KILL-5 {'TERPICU' if m['kill5_triggered'] else 'aman'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
