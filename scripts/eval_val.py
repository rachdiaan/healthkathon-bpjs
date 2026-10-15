"""Metrik BR-19 pada set validation (atau train), tanpa menyentuh holdout/blind (GR-11).

    python scripts/eval_val.py --data data [--dataset validation] [--out docs/eval-validation.md]

Pipeline sama dengan batch scoring (engine/score_batch.compute) di atas fitur dari data generator.
Label hanya dibaca untuk BU di dataset yang diminta; dataset holdout/blind ditolak.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import features  # noqa: E402
from engine.score_batch import compute, finalize  # noqa: E402

ALLOWED = ("train", "validation")
TYPE_OF = {"lapor_umk": "under_reported_wage", "upah_beku": "under_reported_wage",
           "potong_sebagian": "potong_sebagian", "daftar_sebagian": "partial_registration",
           "pindah_pbpu": "ppu_to_pbpu_shift"}


def score_all(data: Path) -> pd.DataFrame:
    f = features.build(features.load(data))
    ids = pd.Series({c: int("".join(ch for ch in c if ch.isdigit())) for c in f.index})
    sme = f.umkm.astype(bool) & f.padat_karya.astype(str).str.lower().eq("true")
    rows = compute(f, ids, sme)
    for r in rows:
        r.branch_id = 0  # ranking tunggal untuk evaluasi
    rows = finalize(rows)
    return pd.DataFrame([{"code": c, "score": r.score, "rank": r.rank, "rp_low": r.rp_low, "rp_point": r.rp_point,
                          "rp_high": r.rp_high} for c, r in zip(f.index, rows)]).set_index("code").join(
        f[["padat_karya", "umkm"]])


def metrics(res: pd.DataFrame, lab: pd.DataFrame) -> dict:
    d = res.join(lab, how="inner")
    n = len(d)
    k = math.ceil(0.10 * n)
    top = d.sort_values(["score"], ascending=False).head(k)
    y = d.is_violator.astype(bool)
    out = {"n": n, "k": k, "prevalensi": round(y.mean(), 4),
           "p_at_10": round(top.is_violator.astype(bool).mean(), 4)}
    out["lift"] = round(out["p_at_10"] / out["prevalensi"], 2) if out["prevalensi"] else None
    recall = {}
    modus = d.modus.fillna("")
    for m, label in TYPE_OF.items():
        has = modus.str.contains(m)
        if has.sum():
            recall[f"{m} ({label})"] = {"n": int(has.sum()), "recall_top10": round(has[top.index].sum() / has.sum(), 4)}
    out["recall"] = recall
    pk = d.padat_karya.astype(str).str.lower().eq("true")
    compliant_pk = pk & ~y
    out["false_flag_padat_karya"] = {
        "n_patuh_padat_karya": int(compliant_pk.sum()),
        "di_top10": int(compliant_pk[top.index].sum()),
        "rate": round(compliant_pk[top.index].sum() / compliant_pk.sum(), 4) if compliant_pk.sum() else None}
    nc = d[y]
    loss = nc.iuran_tak_tertagih_tahun_terakhir.astype(float)
    sp = spearmanr(nc.rp_point, loss).statistic
    pe = pearsonr(nc.rp_point, loss).statistic
    inside = ((loss >= nc.rp_low) & (loss <= nc.rp_high)).mean()
    out["rp"] = {"n_noncompliant": int(len(nc)), "spearman": round(float(sp), 4), "pearson": round(float(pe), 4),
                 "coverage_rentang": round(float(inside), 4)}
    return out


def to_md(m: dict, dataset: str, note: str) -> str:
    L = [f"# Evaluasi model, set `{dataset}`", "", note, "",
         "Definisi metrik: PRD [BR-19]. N = BU di set, K = ceil(0,10 × N).", "",
         "| Metrik | Nilai | Target PRD |", "|---|---|---|",
         f"| P@10% | {m['p_at_10']:.1%} (K = {m['k']} dari N = {m['n']}) | - |",
         f"| Lift vs prevalensi ({m['prevalensi']:.1%}) | {m['lift']}× | ≥ 2× (KILL-4) |",
         f"| False flag padat karya patuh di top 10% | {m['false_flag_padat_karya']['rate']:.1%} "
         f"({m['false_flag_padat_karya']['di_top10']} dari {m['false_flag_padat_karya']['n_patuh_padat_karya']}) | ≤ 3% (M-7) |",
         f"| Spearman Rp (rp_point vs kerugian sebenarnya, BU tidak patuh) | {m['rp']['spearman']} | ≥ 0,50 (M-4) |",
         f"| Pearson Rp | {m['rp']['pearson']} | dilaporkan |",
         f"| Kerugian sebenarnya di dalam rentang rp_low–rp_high | {m['rp']['coverage_rentang']:.1%} | dilaporkan |",
         "", "## Recall per tipe (top 10%)", "", "| Modus | n kasus | Recall |", "|---|---|---|"]
    L += [f"| {k} | {v['n']} | {v['recall_top10']:.1%} |" for k, v in m["recall"].items()]
    L += ["", "Target M-5/M-6: recall pemotongan upah parsial ≥ 35%, pendaftaran parsial ≥ 50%. Target, bukan klaim.", "",
          "```json", json.dumps(m, indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--dataset", default="validation", choices=ALLOWED)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    splits = json.loads((ROOT / "ml" / "splits.json").read_text(encoding="utf-8"))["assignment"]
    codes = [c for c, ds in splits.items() if ds == a.dataset]
    lab = pd.read_csv(a.data / "label" / "labels.csv").set_index("employer_id").loc[codes]
    res = score_all(a.data)
    m = metrics(res, lab)
    md = to_md(m, a.dataset, a.note)
    if a.out:
        a.out.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
