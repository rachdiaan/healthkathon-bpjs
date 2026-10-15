# Sumber data dan regulasi (FR-34, BR-4, BR-6)

Isi `data/` lainnya tidak di-commit (data sintetis hasil generator). File ini mencatat sumber publik dan status verifikasinya. Item berstatus **belum diverifikasi** tidak boleh dipresentasikan sebagai fakta.

## Upah per sektor (bps.go.id)

| Tabel | URL | Tanggal akses | Status |
|---|---|---|---|
| Rata-rata upah/gaji bersih sebulan menurut lapangan pekerjaan utama, 17 sektor (Sakernas) | https://www.bps.go.id/en/statistics-table/2/MTUyMSMy/rata-rata-upah-gaji.html | 2026-10-14 (URL ditemukan; angka belum diunduh) | **belum diverifikasi**: halaman dirender JavaScript, unduh manual CSV/XLSX dari halaman ini lalu simpan di `data_publik/bps/` |
| Rata-rata upah/gaji bersih sebulan menurut provinsi dan lapangan pekerjaan utama, 17 sektor | https://www.bps.go.id/en/statistics-table/2/MjQ3NSMy/rata-rata-upah-gaji-bersih-sebulan-buruh-karyawan-pegawai-menurut-provinsi-dan-lapangan-pekerjaan-utama-di-17-sektor--rupiah-.html | 2026-10-14 (URL ditemukan) | **belum diverifikasi** |

Sampai tabel resmi diunduh, `core.wage_reference.sector_median_wage_rp` masih berasal dari benchmark simulasi generator (sumber dicatat `synthetic:generator/referensi` di kolom `source_url`), yang dikalibrasi ke angka sekunder Sakernas Agustus 2025 di `data_publik/bps/`.

## Regulasi

| Item | Nilai di `engine/params.py` | Rujukan | Status |
|---|---|---|---|
| Tarif iuran PPU | 5% (4% pemberi kerja, 1% pekerja) | Perpres 82/2018 jo. 64/2020 jo. 59/2024 Pasal 30 | **belum diverifikasi** ke teks resmi |
| Batas atas upah dasar iuran PPU | Rp12.000.000/bulan | Perpres 59/2024 Pasal 32 ayat (1), https://peraturan.go.id/files/perpres-no-59-tahun-2024.pdf | **belum diverifikasi** ke teks resmi |
| Batas bawah = upah minimum kab/kota; dikecualikan usaha mikro dan kecil | `UMKM_DIKECUALIKAN_UPAH_MINIMUM = True` | Perpres 59/2024 Pasal 32 ayat (2); PP 36/2021 jo. PP 51/2023 jo. PP 49/2025, https://peraturan.bpk.go.id/Details/161909/pp-no-36-tahun-2021 | **belum diverifikasi**: cek apakah PP 49/2025 mengubah pengecualian |

## Definisi UMKM dan sektor padat karya (BR-4)

- UMKM = skala usaha `mikro` atau `kecil` di data generator. Rujukan kriteria: PP 7/2021. Status: **belum diverifikasi** (generator memakai kategori skala, bukan omzet/aset).
- Sektor padat karya = kolom `padat_karya` di `data/referensi/sektor.csv` (generator), disalin ke `core.sector.is_labor_intensive`. Daftar KBLI padat karya resmi: **belum diverifikasi**.
- `sme_protection = is_sme AND is_labor_intensive`.
