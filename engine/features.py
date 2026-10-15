"""Fitur per badan usaha dari data publik + referensi (tanpa label).

Setiap fitur bisa dibaca manusia, karena dipakai juga sebagai bukti di reason code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class Inputs:
    employers: pd.DataFrame
    wages: pd.DataFrame
    mutations: pd.DataFrame
    umk: pd.DataFrame
    benchmark: pd.DataFrame


def load(data: Path) -> Inputs:
    dt = {"kbli": str, "kode_wilayah": str}
    emp = pd.read_csv(data / "publik/employers.csv", dtype=dt)
    wages = pd.read_csv(data / "publik/wage_history.csv")
    mut = pd.read_csv(data / "publik/mutations.csv", parse_dates=["tanggal", "tgl_segmen_baru"], low_memory=False)
    umk = pd.read_csv(data / "referensi/umk.csv", dtype=dt)
    bm = pd.read_csv(data / "referensi/benchmark_upah.csv", dtype=dt)
    return Inputs(emp, wages, mut, umk, bm)


def build(inp: Inputs) -> pd.DataFrame:
    emp = inp.employers.set_index("employer_id")
    w = inp.wages.merge(inp.employers[["employer_id", "kbli", "kode_wilayah"]], on="employer_id")
    w = w.merge(inp.umk[["kode_wilayah", "tahun", "umk"]], on=["kode_wilayah", "tahun"])
    w = w.merge(inp.benchmark[["kbli", "kode_wilayah", "tahun", "median_upah"]],
                on=["kbli", "kode_wilayah", "tahun"], how="left")
    w["r_umk"] = w.upah_dilaporkan / w.umk

    f = pd.DataFrame(index=emp.index)
    g_all = w.groupby("employer_id")
    f["tahun_teramati"] = g_all.tahun.nunique()
    first_year, last_year = g_all.tahun.transform("min"), g_all.tahun.transform("max")

    # --- snapshot tahun terakhir ---
    wl = w[w.tahun == last_year]
    gl = wl.groupby("employer_id")
    f["n_pekerja"] = gl.worker_id.nunique()
    f["porsi_tepat_umk"] = (wl.upah_dilaporkan == wl.umk).groupby(wl.employer_id).mean()
    f["porsi_bawah_umk"] = (wl.upah_dilaporkan < wl.umk).groupby(wl.employer_id).mean()
    f["porsi_atas_umk"] = (wl.upah_dilaporkan > wl.umk).groupby(wl.employer_id).mean()
    f["median_rasio_umk"] = gl.r_umk.median()
    f["p90_rasio_umk"] = gl.r_umk.quantile(0.9)
    f["porsi_upah_modus"] = gl.upah_dilaporkan.agg(lambda s: s.value_counts(normalize=True).iloc[0])
    f["median_upah"] = gl.upah_dilaporkan.median()
    f["umk_terakhir"] = gl.umk.first()
    bm_last = gl.median_upah.first()
    f["benchmark_upah"] = bm_last
    f["rasio_benchmark"] = f.median_upah / bm_last

    # --- dinamika kenaikan upah (pasangan tahun berurutan per pekerja) ---
    s = w.sort_values(["worker_id", "tahun"])
    prev = s.groupby("worker_id")[["tahun", "upah_dilaporkan", "umk"]].shift()
    pair = s[(prev.tahun == s.tahun - 1).to_numpy()].copy()
    pair["w0"], pair["u0"] = prev.loc[pair.index, "upah_dilaporkan"], prev.loc[pair.index, "umk"]
    pair = pair[pair.umk > pair.u0]
    gp = pair.groupby("employer_id")
    f["pasangan_kenaikan"] = gp.size()
    f["porsi_upah_beku"] = (pair.upah_dilaporkan <= pair.w0).groupby(pair.employer_id).mean()
    # kenaikan persis = kenaikan UMK (dalam pembulatan Rp1.000), hanya untuk pekerja di atas UMK tahun lalu
    above = pair[pair.w0 > pair.u0]
    same = (above.upah_dilaporkan - above.w0 - (above.umk - above.u0)).abs() <= 1000
    f["porsi_naik_sama_umk"] = same.groupby(above.employer_id).mean()

    # --- headcount vs rencana tenaga kerja di OSS (dideklarasikan di awal) ---
    # rata-rata pekerja (orang-bulan / 12) di tahun pertama, agar pengganti turnover tidak terhitung ganda
    wf = w[w.tahun == first_year]
    f["n_pekerja_awal"] = (wf.groupby("employer_id").bulan_aktif.sum() / 12).round(1)
    f["tk_oss"] = emp.tk_oss
    f["rasio_headcount_oss"] = f.n_pekerja_awal / f.tk_oss

    # --- status: klaster keluar PPU -> PBPU cepat (<=30 hari), bukan PHK ---
    m = inp.mutations
    pb = m[(m.jenis == "KELUAR_PPU") & (m.segmen_tujuan == "PBPU")
           & ((m.tgl_segmen_baru - m.tanggal).dt.days <= 30) & (m.alasan != "phk")].copy()
    pb["bulan"] = pb.tanggal.dt.year * 12 + pb.tanggal.dt.month
    cnt = pb.groupby(["employer_id", "bulan"]).size().rename("n").reset_index()
    # jendela bergulir 3 bulan
    best = {}
    for eid, d in cnt.groupby("employer_id"):
        mm = d.set_index("bulan").n
        idx = np.arange(mm.index.min(), mm.index.max() + 1)
        roll = mm.reindex(idx, fill_value=0).rolling(3, min_periods=1).sum()
        best[eid] = (int(roll.max()), int(roll.idxmax()))
    f["klaster_pbpu_n"] = pd.Series({k: v[0] for k, v in best.items()})
    f["klaster_pbpu_bulan"] = pd.Series({k: v[1] for k, v in best.items()})
    f["rata_pekerja"] = w.groupby(["employer_id", "tahun"]).worker_id.nunique().groupby(level=0).mean()
    f["klaster_pbpu_porsi"] = f.klaster_pbpu_n / f.rata_pekerja

    f = f.join(emp[["nama", "kbli", "nama_sektor", "padat_karya", "kode_wilayah", "skala_usaha"]])
    f["umkm"] = f.skala_usaha.isin(["mikro", "kecil"])
    f = f.fillna({"klaster_pbpu_n": 0, "klaster_pbpu_porsi": 0, "n_pekerja": 0, "porsi_tepat_umk": 0,
                  "porsi_bawah_umk": 0, "pasangan_kenaikan": 0})
    # FR-36: median upah relatif terhadap BU sejenis (sektor × kab/kota × skala); fallback sektor × skala.
    fine = f.groupby(["kbli", "kode_wilayah", "skala_usaha"]).median_upah.transform("median")
    n_fine = f.groupby(["kbli", "kode_wilayah", "skala_usaha"]).median_upah.transform("count")
    coarse = f.groupby(["kbli", "skala_usaha"]).median_upah.transform("median")
    f["median_upah_peer"] = fine.where(n_fine >= 8, coarse)
    f["rasio_upah_peer"] = f.median_upah / f.median_upah_peer
    return f
