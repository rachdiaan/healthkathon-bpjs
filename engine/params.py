"""Parameter regulasi PayRay (BR-6). Satu-satunya tempat nilai ini boleh ditulis di engine/.

Setiap konstanta mencatat sumber dan status verifikasi. Status "belum diverifikasi" berarti
nilai belum dicocokkan ke teks resmi dan tidak boleh dipresentasikan sebagai fakta.
"""
from __future__ import annotations

# Iuran PPU = 5% dari upah: 4% pemberi kerja, 1% pekerja.
# Sumber: Perpres 82/2018 jo. Perpres 64/2020 jo. Perpres 59/2024 (Pasal 30).
# Status: belum diverifikasi ke teks resmi (ringkasan sekunder menyatakan tidak berubah sejak 2020).
TARIF_IURAN_PPU = 0.05
TARIF_PEMBERI_KERJA = 0.04
TARIF_PEKERJA = 0.01

# Batas atas upah dasar perhitungan iuran PPU per bulan.
# Sumber: Perpres 59/2024 Pasal 32 ayat (1), https://peraturan.go.id/files/perpres-no-59-tahun-2024.pdf
# Status: belum diverifikasi ke teks resmi (angka dari ringkasan pencarian 2026-10-14).
BATAS_ATAS_UPAH = 12000000

# Batas bawah dasar iuran = upah minimum kab/kota (atau provinsi), dikecualikan untuk usaha mikro dan kecil.
# Sumber: Perpres 59/2024 Pasal 32 ayat (2); PP 36/2021 jo. PP 51/2023 jo. PP 49/2025 (pengupahan).
# Status: belum diverifikasi; perlu cek apakah PP 49/2025 mengubah pengecualian usaha mikro/kecil.
UMKM_DIKECUALIKAN_UPAH_MINIMUM = True
SKALA_UMKM = ("mikro", "kecil")  # kriteria PP 7/2021, belum diverifikasi
