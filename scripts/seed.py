"""Seed data sintetis dari output generator/ ke schema v2 (FR-4, BR-21).

    python scripts/seed.py --data data [--period 2026-09]

* NIK: generator hanya mengeluarkan pseudonim `worker_id`. Script menurunkan NIK
  sintetis 16 digit di memori, lalu langsung menyimpannya sebagai
  HMAC-SHA256(PAYRAY_NIK_KEY, nik). NIK mentah tidak pernah ditulis ke DB, file, atau log.
* Cabang: kab/kota diurutkan, lalu dibagi dua menjadi 2 cabang sintetis.
* Split: `ml/splits.json` (train/validation/holdout 60/20/20, deterministik per kode BU)
  dibuat sekali bila belum ada, lalu dibekukan (BR-20).
* Periode default: bulan berjalan WIB dikurangi satu.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SPLITS = ROOT / "ml" / "splits.json"
WIB = ZoneInfo("Asia/Jakarta")
MIN_KEY_BYTES = 32
SYNTHETIC_SOURCE = "synthetic:generator/referensi (diganti data bps.go.id di t29)"

MODUS_TO_TYPE = {
    "lapor_umk": "under_reported_wage",
    "potong_sebagian": "under_reported_wage",
    "upah_beku": "under_reported_wage",
    "daftar_sebagian": "partial_registration",
    "pindah_pbpu": "ppu_to_pbpu_shift",
}


def load_key() -> bytes:
    raw = os.environ.get("PAYRAY_NIK_KEY", "")
    key = raw.encode("utf-8")
    if len(key) < MIN_KEY_BYTES:
        raise SystemExit(f"PAYRAY_NIK_KEY harus minimal {MIN_KEY_BYTES} byte (sekarang {len(key)}). Tidak ada yang ditulis.")
    return key


def default_period() -> str:
    today = datetime.now(WIB).date()
    y, m = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    return f"{y:04d}-{m:02d}"


def synthetic_nik(worker_id: str, kab: str) -> str:
    """NIK sintetis 16 digit (4 digit wilayah + 12 digit dari hash pseudonim). Hanya hidup di memori."""
    digits = str(int(hashlib.sha256(worker_id.encode()).hexdigest(), 16))[-12:]
    return f"{kab[:4]:0>4}{digits}"


def nik_token(key: bytes, nik: str) -> str:
    return hmac.new(key, nik.encode(), hashlib.sha256).hexdigest()


def employer_numeric_id(code: str) -> int:
    return int("".join(ch for ch in code if ch.isdigit()))


def load_or_make_splits(codes: list[str]) -> dict[str, str]:
    if SPLITS.exists():
        return json.loads(SPLITS.read_text(encoding="utf-8"))["assignment"]
    assignment = {}
    for c in sorted(codes):
        b = int(hashlib.sha256(f"payray-split:{c}".encode()).hexdigest(), 16) % 100
        assignment[c] = "train" if b < 60 else ("validation" if b < 80 else "holdout")
    SPLITS.write_text(json.dumps({
        "method": "sha256('payray-split:'+employer_code) mod 100: <60 train, <80 validation, else holdout",
        "frozen_on": date.today().isoformat(),
        "assignment": assignment,
    }, indent=1), encoding="utf-8")
    return assignment


def build_frames(data: Path, period: str, key: bytes, dataset: str | None = None,
                 worker_id_offset: int = 0) -> dict[str, pd.DataFrame]:
    """dataset=None: pakai ml/splits.json. dataset='blind': semua BU berlabel blind (t31)."""
    emp = pd.read_csv(data / "publik" / "employers.csv", dtype={"kode_wilayah": str, "kbli": str})
    workers = pd.read_csv(data / "publik" / "workers.csv", dtype=str)
    wages = pd.read_csv(data / "publik" / "wage_history.csv")
    muts = pd.read_csv(data / "publik" / "mutations.csv", dtype=str, low_memory=False)
    umk = pd.read_csv(data / "referensi" / "umk.csv", dtype={"kode_wilayah": str})
    bench = pd.read_csv(data / "referensi" / "benchmark_upah.csv", dtype={"kode_wilayah": str, "kbli": str})
    labels = pd.read_csv(data / "label" / "labels.csv")

    kabs = sorted(emp.kode_wilayah.unique())
    half = (len(kabs) + 1) // 2
    branch_of = {k: (1 if i < half else 2) for i, k in enumerate(kabs)}
    branches = pd.DataFrame([
        {"id": 1, "name": "KC Sintetis Barat", "kab_kota_code": kabs[0]},
        {"id": 2, "name": "KC Sintetis Timur", "kab_kota_code": kabs[half]},
    ])

    # Pekerja aktif di tahun upah terakhir, segmen dari mutasi keluar ke PBPU.
    last_year = int(wages.tahun.max())
    w_last = wages[wages.tahun == last_year][["worker_id", "employer_id", "upah_dilaporkan"]]
    w_last = w_last.drop_duplicates(["worker_id", "employer_id"])
    to_pbpu = set(muts.loc[(muts.jenis == "KELUAR_PPU") & (muts.segmen_tujuan == "PBPU"), "worker_id"])
    w_last = w_last.merge(emp[["employer_id", "kode_wilayah"]], on="employer_id")
    w_last["segment"] = w_last.worker_id.map(lambda x: "PBPU" if x in to_pbpu else "PPU")
    w_last["nik_token"] = [nik_token(key, synthetic_nik(wid, kab)) for wid, kab in zip(w_last.worker_id, w_last.kode_wilayah)]
    worker = pd.DataFrame({
        "id": range(worker_id_offset + 1, worker_id_offset + len(w_last) + 1),
        "employer_id": w_last.employer_id.map(employer_numeric_id),
        "nik_token": w_last.nik_token,
        "period": period,
        "segment": w_last.segment,
        "reported_wage_rp": w_last.upah_dilaporkan.astype("int64"),
    })
    del workers  # pseudonim worker_id tidak masuk schema v2

    headcount = worker[worker.segment == "PPU"].groupby("employer_id").size()
    employer = pd.DataFrame({
        "id": emp.employer_id.map(employer_numeric_id),
        "code": emp.employer_id,
        "branch_id": emp.kode_wilayah.map(branch_of),
        "name": emp.nama,
        "kbli_sector": emp.kbli,
        "kab_kota_code": emp.kode_wilayah,
        "is_sme": emp.skala_usaha.isin(["mikro", "kecil"]),
        "is_labor_intensive": emp.padat_karya.astype(str).str.lower() == "true",
        "active": True,
    })
    employer["reported_headcount"] = employer.id.map(headcount).fillna(0).astype(int)

    med = bench.dropna(subset=["median_upah"]).groupby(["kode_wilayah", "tahun"]).apply(
        lambda g: json.dumps({k: int(v) for k, v in zip(g.kbli, g.median_upah)}), include_groups=False)
    wref = umk.rename(columns={"kode_wilayah": "kab_kota_code", "tahun": "year", "umk": "umk_rp"})[
        ["kab_kota_code", "year", "umk_rp"]].copy()
    wref["sector_median_wage_rp"] = [med.get((k, y)) for k, y in zip(wref.kab_kota_code, wref.year)]
    wref["source_url"] = SYNTHETIC_SOURCE
    wref["accessed_on"] = date.today().isoformat()

    splits = {c: dataset for c in emp.employer_id} if dataset else load_or_make_splits(list(emp.employer_id))
    first_modus = labels.modus.fillna("").str.split("|").str[0]
    gt = pd.DataFrame({
        "employer_id": labels.employer_id.map(employer_numeric_id),
        "period": period,
        "dataset": labels.employer_id.map(splits),
        "is_noncompliant": labels.is_violator.astype(bool),
        "violation_type": first_modus.map(MODUS_TO_TYPE).where(labels.is_violator.astype(bool), "none"),
        "true_loss_rp": labels.iuran_tak_tertagih_tahun_terakhir.astype("int64"),
    })
    from engine import features as feat

    fx = feat.build(feat.load(data))
    fx_json = json.loads(fx.to_json(orient="index"))
    efeat = pd.DataFrame({
        "employer_id": [employer_numeric_id(c) for c in fx_json],
        "period": period,
        "features": [json.dumps(v) for v in fx_json.values()],
    })
    sec = pd.read_csv(data / "referensi" / "sektor.csv", dtype={"kbli": str})
    sector = pd.DataFrame({"kbli": sec.kbli, "name": sec.nama_sektor,
                           "is_labor_intensive": sec.padat_karya.astype(str).str.lower() == "true"})
    return {"core.sector": sector, "core.branch": branches, "core.employer": employer, "core.worker": worker,
            "core.wage_reference": wref, "label.ground_truth": gt, "core.employer_feature": efeat}


COLUMNS = {
    "core.sector": ["kbli", "name", "is_labor_intensive"],
    "core.branch": ["id", "name", "kab_kota_code"],
    "core.employer": ["id", "code", "branch_id", "name", "kbli_sector", "kab_kota_code",
                      "reported_headcount", "is_sme", "is_labor_intensive", "active"],
    "core.worker": ["id", "employer_id", "nik_token", "period", "segment", "reported_wage_rp"],
    "core.wage_reference": ["kab_kota_code", "year", "umk_rp", "sector_median_wage_rp", "source_url", "accessed_on"],
    "label.ground_truth": ["employer_id", "period", "dataset", "is_noncompliant", "violation_type", "true_loss_rp"],
    "core.employer_feature": ["employer_id", "period", "features"],
}


def seed(url: str, frames: dict[str, pd.DataFrame]) -> None:
    with psycopg.connect(url) as conn:
        conn.execute("SET ROLE payray_migrator")
        for table, cols in COLUMNS.items():
            if table not in frames:
                continue
            df = frames[table][cols]
            with conn.cursor().copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN") as cp:
                for row in df.itertuples(index=False):
                    cp.write_row([None if (isinstance(v, float) and pd.isna(v)) else v for v in row])
            print(f"  {table}: {len(df):,} baris")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--period", default=None)
    a = ap.parse_args()
    key = load_key()  # gagal sebelum membaca atau menulis apa pun
    url = os.environ.get("MIGRATE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set DATABASE_URL.")
    period = a.period or default_period()
    print(f"Seed periode {period} dari {a.data}")
    seed(url, build_frames(a.data, period, key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
