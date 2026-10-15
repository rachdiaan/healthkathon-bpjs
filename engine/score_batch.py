"""Batch scoring: fitur dari core.employer_feature → core.risk_score untuk satu batch (FR-21..FR-25).

Skor = peluang gabungan model stacking yang sama dengan versi browser (engine/ml_model.py),
dengan persentil prioritas mesin aturan (engine/score.py) sebagai input kedua.
Rank, bucket confidence, badge UMKM, dan Rp dihitung sekali di sini (BR-2..BR-5).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from engine import ml_model, score
from engine.format import confidence_bucket, to_rp
from engine.reasons import CATALOG, RULE_TO_CODE, checklist
from engine.rules import RULES, apply_rules

MAX_EMPLOYERS = 50_000
MAX_FLAGGED = 50
# Skor confidence engine/score.py berupa poin 0..4 (≥4 tinggi, ≥2 sedang). Dipetakan ke angka 0..1
# supaya bucket BR-3 (0,40 / 0,70) menghasilkan kategori yang sama dengan engine.
CONF_FROM_POINTS = {0: 0.10, 1: 0.30, 2: 0.45, 3: 0.60, 4: 0.90}
EVIDENCE = {
    "bunching_umk": ["porsi_tepat_umk", "porsi_atas_umk", "n_pekerja"],
    "naik_sama_umk": ["porsi_naik_sama_umk"],
    "upah_beku": ["porsi_upah_beku", "pasangan_kenaikan"],
    "bawah_umk_wajib": ["porsi_bawah_umk", "skala_usaha"],
    "upah_atas_rendah": ["p90_rasio_umk", "median_upah", "umk_terakhir", "benchmark_upah", "rasio_upah_peer"],
    "headcount_oss": ["n_pekerja_awal", "tk_oss", "rasio_headcount_oss"],
    "klaster_pbpu": ["klaster_pbpu_n", "klaster_pbpu_porsi"],
}
REQUIRED = ["n_pekerja", "skala_usaha", "umk_terakhir"]


class OutputInvalid(Exception):
    """Satu baris gagal validasi GR-5 → seluruh batch failed."""


@dataclass
class Row:
    employer_id: int
    score: float
    confidence: float
    reasons: list[dict[str, Any]]
    rp_point: int
    sme_protection: bool
    branch_id: int = 0
    rank: int = 0
    rp_low: int = 0
    rp_high: int = 0
    rp_band: str | None = None
    flagged: list[dict[str, str]] = field(default_factory=list)

    @property
    def bucket(self) -> str:
        return confidence_bucket(self.confidence)


def _num(v: Any) -> Any:
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if math.isnan(float(v)) else round(float(v), 4)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def _confidence_points(f: pd.DataFrame) -> pd.Series:
    return ((f.n_pekerja >= 10).astype(int) + (f.n_pekerja >= 5).astype(int)
            + (f.tahun_teramati >= 3).astype(int) + f.benchmark_upah.notna().astype(int))


def compute(f: pd.DataFrame, ids: pd.Series, sme: pd.Series) -> list[Row]:
    """f: fitur per BU (index = kode BU). ids: kode → employer.id. sme: kode → sme_protection."""
    res, S = score.run(f)
    res = res.reindex(f.index)
    _, R = apply_rules(f)
    weights = pd.Series({k: w for k, (_, w) in RULES.items()})
    contrib = S * weights
    pr = res.prioritas.rank(pct=True)
    model = ml_model.load()
    X = ml_model.matrix(f)
    pts = _confidence_points(f)
    missing = f[REQUIRED].isna().any(axis=1) | f.skala_usaha.astype(str).eq("")
    no_sector = f.kbli.isna() | f.kbli.astype(str).str.strip().isin(["", "nan", "None"])

    rows: list[Row] = []
    for i, code in enumerate(f.index):
        if missing.at[code]:
            p = float(res.skor_aturan.at[code]) / 100  # fallback: skor aturan saja
            conf = CONF_FROM_POINTS[0]
        else:
            p = ml_model.predict(model, X[i], float(pr.at[code]))
            conf = CONF_FROM_POINTS[int(pts.at[code])]
        c = contrib.loc[code].sort_values(ascending=False)
        reasons: list[dict[str, Any]] = []
        for rule, v in c.items():
            if v <= 0 or (S.at[code, rule] < 0.3 and reasons):
                continue
            rc = RULE_TO_CODE[str(rule)]
            reasons.append({"code": rc, "text": str(R.at[code, rule]), "contribution": round(float(v), 4),
                            "evidence": {k: _num(f.at[code, k]) for k in EVIDENCE[str(rule)]},
                            "checklist": checklist(rc)})
        anom = float(res.skor_anomali.at[code]) / 100
        if anom >= 0.9 or not reasons:
            reasons.append({"code": "ANOMALI_KOMBINASI",
                            "text": "Kombinasi pola tidak biasa dibanding usaha seskala",
                            "contribution": round(anom * 0.25, 4),
                            "evidence": {"persentil_anomali": round(anom, 4)},
                            "checklist": checklist("ANOMALI_KOMBINASI")})
        if no_sector.at[code]:
            reasons.append({"code": "DATA_SEKTOR_KOSONG", "text": "Data sektor usaha kosong",
                            "contribution": 0.0, "evidence": {}, "checklist": checklist("DATA_SEKTOR_KOSONG")})
        reasons.sort(key=lambda r: -r["contribution"])
        rows.append(Row(
            employer_id=int(ids.at[code]), score=float(p), confidence=conf, reasons=reasons,
            rp_point=to_rp(Decimal(str(float(res.estimasi_iuran_tak_tertagih.at[code] or 0)))),
            sme_protection=bool(sme.at[code]) and not bool(no_sector.at[code]),
        ))
    return rows


RP_INTERVAL_PATH = Path(__file__).resolve().parent.parent / "ml" / "artefak" / "rp_interval.json"


def rp_interval_factors() -> tuple[Decimal, Decimal]:
    """Faktor rentang Rp dikalibrasi di set train (scripts/fit_rp_interval.py, FR-35); low ≤ 1 ≤ high."""
    d = json.loads(RP_INTERVAL_PATH.read_text(encoding="utf-8"))
    lo = min(Decimal(str(d["factor_lo"])), Decimal(1))
    hi = max(Decimal(str(d["factor_hi"])), Decimal(1))
    return lo, hi


def finalize(rows: list[Row]) -> list[Row]:
    """Rp rentang + band per cabang, lalu rank per cabang: score DESC, employer_id ASC (BR-2, BUG-5)."""
    lo, hi = rp_interval_factors()
    for r in rows:
        point = Decimal(r.rp_point)
        r.rp_low = to_rp(point * lo)
        r.rp_high = to_rp(point * hi)
    by_branch: dict[int, list[Row]] = {}
    for r in rows:
        by_branch.setdefault(r.branch_id, []).append(r)
    for group in by_branch.values():
        group.sort(key=lambda r: (-r.score, r.employer_id))
        for k, r in enumerate(group, 1):
            r.rank = k
        pts = sorted(r.rp_point for r in group)
        t1, t2 = pts[len(pts) // 3], pts[(2 * len(pts)) // 3]
        for r in group:
            r.rp_band = "rendah" if r.rp_point <= t1 else ("sedang" if r.rp_point <= t2 else "tinggi")
    return rows


def validate(rows: list[Row]) -> None:
    """GR-5: skor ∈ [0,1], tidak NaN, low ≤ point ≤ high, low ≥ 0, reason non-kosong dari katalog."""
    for r in rows:
        if not (isinstance(r.score, float) and 0.0 <= r.score <= 1.0) or math.isnan(r.score):
            raise OutputInvalid(f"skor tidak valid untuk BU {r.employer_id}: {r.score}")
        if not (0 <= r.rp_low <= r.rp_point <= r.rp_high):
            raise OutputInvalid(f"rentang Rp tidak valid untuk BU {r.employer_id}")
        if not r.reasons or any(x["code"] not in CATALOG for x in r.reasons):
            raise OutputInvalid(f"reason code tidak valid untuk BU {r.employer_id}")
        if math.isnan(r.confidence) or not 0 <= r.confidence <= 1:
            raise OutputInvalid(f"confidence tidak valid untuk BU {r.employer_id}")


def _q(conn: psycopg.Connection[Any], sql: str, params: Any = None) -> psycopg.Cursor[Any]:
    """Query dengan baris tuple, apa pun row_factory koneksi (pool API memakai dict_row)."""
    return conn.cursor(row_factory=tuple_row).execute(sql, params)  # type: ignore[arg-type]


def load_features(conn: psycopg.Connection[Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    emp = pd.DataFrame(_q(conn,
        "SELECT e.id, e.code, e.branch_id, e.is_sme, e.is_labor_intensive, ef.features "
        "FROM core.employer e JOIN core.employer_feature ef ON ef.employer_id = e.id WHERE e.active ORDER BY e.id"
    ).fetchall(), columns=["id", "code", "branch_id", "is_sme", "is_labor_intensive", "features"])
    if len(emp) > MAX_EMPLOYERS:
        raise OutputInvalid(f"jumlah BU {len(emp)} melebihi batas {MAX_EMPLOYERS} (BR-15)")
    f = pd.DataFrame(list(emp.features), index=emp.code)
    for col in f.columns:
        if f[col].dtype == object:
            conv = pd.to_numeric(f[col], errors="coerce")
            if conv.notna().sum() == f[col].notna().sum():
                f[col] = conv
    f["kbli"] = f["kbli"].astype(str)
    return f, emp.set_index("code")


def flagged_workers(conn: psycopg.Connection[Any], employer_ids: list[int]) -> dict[int, list[dict[str, str]]]:
    """Pekerja ter-flag: upah tepat UMK atau segmen PBPU. Hanya 8 karakter pertama token (FR-15)."""
    out: dict[int, list[dict[str, str]]] = {}
    cur = _q(conn,
        "SELECT w.employer_id, left(w.nik_token, 8) AS t8, "
        "CASE WHEN w.segment = 'PBPU' THEN 'Pindah ke segmen PBPU' ELSE 'Upah dilaporkan tepat UMK' END AS reason "
        "FROM core.worker w JOIN core.employer e ON e.id = w.employer_id "
        "JOIN core.wage_reference r ON r.kab_kota_code = e.kab_kota_code "
        "  AND r.year = (SELECT max(year) FROM core.wage_reference) "
        "WHERE w.employer_id = ANY(%s) AND (w.segment = 'PBPU' OR w.reported_wage_rp = r.umk_rp) "
        "ORDER BY w.employer_id, w.segment DESC, w.id",
        (employer_ids,),
    )
    for eid, t8, reason in cur.fetchall():
        lst = out.setdefault(eid, [])
        if len(lst) < MAX_FLAGGED:
            lst.append({"nik_token8": t8, "reason": reason})
    return out


def write(conn: psycopg.Connection[Any], batch_id: int, rows: list[Row]) -> None:
    with conn.cursor().copy(
        "COPY core.risk_score (batch_id, employer_id, score, rank, confidence, confidence_bucket, reason_codes, "
        "rp_low, rp_point, rp_high, rp_band, sme_protection, flagged_workers) FROM STDIN"
    ) as cp:
        for r in rows:
            cp.write_row([batch_id, r.employer_id, r.score, r.rank, r.confidence, r.bucket, Jsonb(r.reasons),
                          r.rp_low, r.rp_point, r.rp_high, r.rp_band, r.sme_protection, Jsonb(r.flagged)])


def score_batch(conn: psycopg.Connection[Any], batch_id: int, fail_at: int | None = None) -> int:
    """Isi core.risk_score untuk batch `running`. Dipanggil di transaksi dengan role payray_scoring.

    `fail_at` hanya untuk tes BUG-6 (inject exception di BU ke-n).
    """
    batch = _q(conn, "SELECT branch_id, status FROM core.score_batch WHERE id = %s", (batch_id,)).fetchone()
    if batch is None or batch[1] != "running":
        raise OutputInvalid(f"batch {batch_id} tidak berstatus running")
    branch_id = batch[0]
    f, emp = load_features(conn)
    sme = emp.is_sme & emp.is_labor_intensive
    rows = compute(f, emp["id"], sme)
    for r, code in zip(rows, f.index):
        r.branch_id = int(emp.at[code, "branch_id"])
    rows = [r for r in rows if r.branch_id == branch_id]
    if fail_at is not None and len(rows) >= fail_at:
        raise RuntimeError(f"kegagalan uji di BU ke-{fail_at}")
    rows = finalize(rows)
    flags = flagged_workers(conn, [r.employer_id for r in rows])
    for r in rows:
        r.flagged = flags.get(r.employer_id, [])
    validate(rows)
    write(conn, batch_id, rows)
    conn.execute("UPDATE core.score_batch SET status = 'ready', n_scored = %s, finished_at = now() WHERE id = %s",
                 (len(rows), batch_id))
    return len(rows)
