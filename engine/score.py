"""Skor gabungan: aturan transparan + Isolation Forest, keyakinan, dan estimasi rupiah."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from generator.calculator import estimasi_iuran_tak_tertagih as _estimasi

from . import params

from .rules import RULES, apply_rules


def estimasi_iuran_tak_tertagih(upah_wajar, upah_dilaporkan, jumlah_pekerja, pekerja_pindah_pbpu=0):
    """Rumus kalkulator dengan parameter regulasi dari engine/params.py (BR-6)."""
    return _estimasi(upah_wajar, upah_dilaporkan, jumlah_pekerja, pekerja_pindah_pbpu=pekerja_pindah_pbpu,
                     plafon=params.BATAS_ATAS_UPAH, tarif=params.TARIF_IURAN_PPU)

ANOMALY_FEATURES = {
    "porsi_tepat_umk": "porsi upah tepat UMK",
    "porsi_upah_beku": "porsi upah beku",
    "porsi_naik_sama_umk": "kenaikan = kenaikan UMK",
    "median_rasio_umk": "median upah/UMK",
    "p90_rasio_umk": "upah teratas/UMK",
    "porsi_upah_modus": "keseragaman upah",
    "rasio_headcount_oss": "rasio pekerja/OSS",
    "klaster_pbpu_porsi": "klaster pindah PBPU",
}
W_ANOMALY = 0.25


def _peer_z(f: pd.DataFrame, cols) -> pd.DataFrame:
    """Standarisasi robust di dalam kelompok skala usaha, supaya UMKM dibandingkan dengan UMKM."""
    X = f[cols].astype(float)
    X = X.fillna(X.median())
    g = f.skala_usaha
    med = X.groupby(g).transform("median")
    iqr = X.groupby(g).transform(lambda s: s.quantile(0.75) - s.quantile(0.25)).replace(0, np.nan)
    return ((X - med) / iqr.fillna(X.std())).clip(-6, 6)


def anomaly(f: pd.DataFrame, seed: int = 0) -> tuple[pd.Series, pd.DataFrame]:
    Z = _peer_z(f, list(ANOMALY_FEATURES))
    iso = IsolationForest(n_estimators=300, contamination="auto", random_state=seed).fit(Z)
    raw = -iso.score_samples(Z)
    return pd.Series(raw, index=f.index).rank(pct=True), Z


def confidence(f: pd.DataFrame) -> pd.Series:
    pts = (
        (f.n_pekerja >= 10).astype(int) + (f.n_pekerja >= 5).astype(int)
        + (f.tahun_teramati >= 3).astype(int) + f.benchmark_upah.notna().astype(int)
    )
    return pd.Series(np.select([pts >= 4, pts >= 2], ["tinggi", "sedang"], "rendah"), index=f.index)


CONF_WEIGHT = {"tinggi": 1.0, "sedang": 0.85, "rendah": 0.6}


def estimate(f: pd.DataFrame, S: pd.DataFrame) -> pd.DataFrame:
    """Estimasi iuran tak tertagih per tahun (rumus kalkulator PayRay), per modul yang menyala."""
    # upah wajar = median upah badan usaha sejenis yang skornya rendah (proksi patuh), fallback benchmark
    clean = f[S.max(axis=1) < 0.2]
    ref = clean.groupby(["kbli", "skala_usaha", "kode_wilayah"]).median_rasio_umk.median()
    ref_coarse = clean.groupby(["kbli", "skala_usaha"]).median_rasio_umk.median()
    key = list(zip(f.kbli, f.skala_usaha, f.kode_wilayah))
    r = pd.Series(ref.reindex(key).to_numpy(), index=f.index)
    r = r.fillna(pd.Series(ref_coarse.reindex(list(zip(f.kbli, f.skala_usaha))).to_numpy(), index=f.index))
    upah_wajar = (r * f.umk_terakhir).fillna(f.benchmark_upah).fillna(f.median_upah)
    upah_wajar = np.maximum(upah_wajar, f.median_upah)

    upah_on = S[[k for k, (m, _) in RULES.items() if m == "upah"]].max(axis=1) >= 0.3
    est_upah = estimasi_iuran_tak_tertagih(upah_wajar, f.median_upah, f.n_pekerja) * upah_on
    hilang = np.maximum(0, f.tk_oss - f.n_pekerja_awal.fillna(0)) * (S.headcount_oss >= 0.3)
    est_hc = estimasi_iuran_tak_tertagih(upah_wajar, upah_wajar, 0, pekerja_pindah_pbpu=hilang)
    pindah = f.klaster_pbpu_n * (S.klaster_pbpu >= 0.3)
    est_st = estimasi_iuran_tak_tertagih(upah_wajar, upah_wajar, 0, pekerja_pindah_pbpu=pindah)
    out = pd.DataFrame({"upah_wajar_est": upah_wajar.round(-3), "est_upah": est_upah, "est_headcount": est_hc,
                        "est_status": est_st}, index=f.index).fillna(0)
    out["estimasi_iuran_tak_tertagih"] = out[["est_upah", "est_headcount", "est_status"]].sum(axis=1).round(-3)
    return out


def run(f: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    S, R = apply_rules(f)
    weights = pd.Series({k: w for k, (_, w) in RULES.items()})
    # noisy-OR: satu bukti kuat cukup, beberapa bukti lemah saling menguatkan
    rule_score = 1 - (1 - S * weights).prod(axis=1)
    anom, Z = anomaly(f)
    score = (1 - W_ANOMALY) * rule_score + W_ANOMALY * anom * (0.3 + 0.7 * rule_score.clip(upper=1) ** 0.5)
    conf = confidence(f)
    est = estimate(f, S)

    res = pd.DataFrame(index=f.index)
    res["skor"] = (score * 100).round(1)
    res["keyakinan"] = conf
    res["prioritas"] = res.skor * conf.map(CONF_WEIGHT)
    res["skor_aturan"] = (rule_score * 100).round(1)
    res["skor_anomali"] = (anom * 100).round(1)
    for mod in ("upah", "headcount", "status"):
        cols = [k for k, (m, _) in RULES.items() if m == mod]
        res[f"modul_{mod}"] = (S[cols].max(axis=1) * 100).round(0)
    res = res.join(est)

    # reason code: 3 aturan dengan kontribusi terbesar, + anomali bila menonjol
    # ambang yang sama dengan estimasi rupiah (>= 0.3), supaya setiap alasan punya andil di estimasi
    contrib = (S * weights).where(S >= 0.3, 0)
    reasons = []
    for eid in f.index:
        c = contrib.loc[eid].sort_values(ascending=False)
        rs = [R.at[eid, k] for k, v in c.items() if v > 0][:3]
        if len(rs) < 3 and anom[eid] >= 0.9:
            top = Z.loc[eid].abs().sort_values(ascending=False).index[:2]
            rs.append("Kombinasi pola tidak biasa dibanding usaha seskala: " + ", ".join(ANOMALY_FEATURES[t] for t in top))
        reasons.append(rs)
    res["alasan"] = [" | ".join(r) for r in reasons]
    res["kategori_risiko"] = pd.cut(res.skor, [-1, 30, 55, 101], labels=["Rendah", "Sedang", "Tinggi"]).astype(str)
    res = res.join(f[["nama", "nama_sektor", "skala_usaha", "kode_wilayah", "n_pekerja"]])
    return res.sort_values("prioritas", ascending=False), S
