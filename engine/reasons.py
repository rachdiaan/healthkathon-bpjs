"""Katalog reason code (GR-5). Setiap kode punya modul dan checklist pemeriksaan.

Teks alasan per BU dibuat oleh engine/rules.py. Katalog ini hanya menetapkan kode yang sah
dan checklist yang terkait, supaya scan sheet konsisten.
"""
from __future__ import annotations

CATALOG: dict[str, dict[str, object]] = {
    "UPAH_BUNCHING_UMK": {
        "rule": "bunching_umk", "module": "upah",
        "checklist": ["Cocokkan slip gaji 3 bulan terakhir dengan upah yang dilaporkan",
                      "Periksa upah supervisor/staf, apakah benar setara UMK"],
    },
    "UPAH_NAIK_SAMA_UMK": {
        "rule": "naik_sama_umk", "module": "upah",
        "checklist": ["Bandingkan kenaikan upah di slip gaji dengan kenaikan UMK tahunan"],
    },
    "UPAH_BEKU": {
        "rule": "upah_beku", "module": "upah",
        "checklist": ["Minta riwayat penyesuaian upah 3 tahun terakhir"],
    },
    "UPAH_BAWAH_UMK": {
        "rule": "bawah_umk_wajib", "module": "upah",
        "checklist": ["Konfirmasi skala usaha (menengah/besar wajib upah minimum)",
                      "Cocokkan daftar upah dengan rekening pembayaran gaji"],
    },
    "UPAH_ATAS_RENDAH": {
        "rule": "upah_atas_rendah", "module": "upah",
        "checklist": ["Periksa upah jabatan teratas dibanding sektor dan wilayah sejenis"],
    },
    "HEADCOUNT_OSS": {
        "rule": "headcount_oss", "module": "headcount",
        "checklist": ["Bandingkan daftar hadir/payroll dengan jumlah peserta terdaftar",
                      "Cek rencana tenaga kerja di NIB/OSS"],
    },
    "STATUS_KLASTER_PBPU": {
        "rule": "klaster_pbpu", "module": "status",
        "checklist": ["Konfirmasi status kerja pekerja yang pindah ke PBPU",
                      "Minta dokumen pemutusan hubungan kerja, bila ada"],
    },
    "ANOMALI_KOMBINASI": {
        "rule": None, "module": "anomali",
        "checklist": ["Telusuri fitur yang paling menyimpang dibanding usaha seskala"],
    },
    "DATA_SEKTOR_KOSONG": {
        "rule": None, "module": "data",
        "checklist": ["Lengkapi data sektor/skala usaha sebelum pemeriksaan"],
    },
}

RULE_TO_CODE = {str(v["rule"]): k for k, v in CATALOG.items() if v["rule"]}


def checklist(code: str) -> list[str]:
    items = CATALOG[code]["checklist"]
    assert isinstance(items, list)
    return [str(x) for x in items]
