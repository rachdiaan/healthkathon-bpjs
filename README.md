# PayRay

Rontgen kepatuhan pemberi kerja untuk JKN — Healthkathon 2026. Konteks lengkap: [CLAUDE.md](CLAUDE.md).

## Mesin scan

```bash
python -m engine --data data --out hasil              # ranking, antrean, lembar hasil scan (tanpa label)
python -m engine --data data --out hasil --evaluate   # + laporan_akurasi.md (butuh data/label/)
```

Cara kerjanya, berurutan:
1. **[features.py](engine/features.py)** menghitung fitur yang bisa dibaca manusia per badan usaha: porsi upah tepat/di bawah/di atas UMK, upah beku saat UMK naik, kenaikan = kenaikan UMK, upah teratas vs sektor, rasio pekerja terdaftar vs OSS, dan klaster pindah PBPU ≤30 hari.
2. **[rules.py](engine/rules.py)** menjalankan 7 aturan transparan dalam 3 modul (upah, headcount, status). Aturannya dibedakan per skala usaha, karena UMKM dikecualikan dari UMK. Pembanding selalu badan usaha sejenis (sektor × skala).
3. **[score.py](engine/score.py)** menggabungkan aturan (noisy-OR) dengan Isolation Forest yang distandarkan per skala. Hasilnya skor 0–100, keyakinan (tinggi/sedang/rendah), 3 alasan utama, dan estimasi Rp per modul.
4. **[evaluate.py](engine/evaluate.py)** dan **[feedback.py](engine/feedback.py)** adalah satu-satunya bagian yang membaca label. Isinya metrik, uji bias per skala, recall per modus, dan simulasi siklus "hasil pemeriksaan jadi label".

Output di `hasil/`: `ranking.csv`, `antrean_pemeriksaan.csv` (risiko ≥ sedang dan keyakinan ≥ sedang), `lembar_scan/*.md`, `ranking_top.json` (untuk dashboard), `laporan_akurasi.md`.

### Hasil (top-10%, tanpa label saat menilai)

| | Data dev (seed 42) | Data holdout (seed 2026) | Target |
|---|---|---|---|
| Precision@10% | 69,4% | **68,4%** | ≥ 70% |
| Lift vs acak | 4,63× | **4,56×** | ≈ 4,7× |
| Salah tandai UMKM patuh | 2,5% | **2,7%** | ≤ 5% |
| Iuran tertangkap per 100 pemeriksaan | Rp7,9 M vs Rp0,63 M acak | Rp7,7 M vs Rp0,53 M acak | > acak |

Generator dikalibrasi ke upah BPS Sakernas Agustus 2025 (urutan sektor ρ = 0,90), lalu kedua dataset dibuat ulang dengan seed injeksi baru. Mesin tidak disetel ulang setelahnya, jadi kedua kolom adalah data yang belum pernah dilihat. Kelemahan yang sudah diketahui:
- Recall modus sulit masih rendah (`potong_sebagian` ±18%, `daftar_sebagian` ±37%)
- Kalkulator estimasi Rp baru berkorelasi 0,34 (log) dengan kerugian sebenarnya
- Salah tandai di usaha menengah/besar ±6%, sebagian besar dari usaha padat karya sah yang membayar UMK

Siklus umpan balik (belajar dari 500 hasil pemeriksaan + 250 audit acak) menaikkan precision putaran berikutnya dari ±22% menjadi 25–27%, dan iuran yang tertangkap ikut naik.

## Lapisan machine learning (`ml/`)

```bash
python -m engine --data data_holdout --out hasil_holdout   # world holdout
python -m ml                                                # training + validasi -> ml/artefak/, hasil/ml_prediksi.csv
python dashboard/build_dashboard.py                         # dashboard/index.html (model berjalan di browser)
```

- **Model peluang pelanggaran:** HistGradientBoosting (250 pohon, 17 fitur mentah) dengan monotonic constraint sesuai logika domain. Sengaja tidak memakai skor rules, sehingga menjadi second opinion yang independen.
- **Label hanya dari hasil pemeriksaan:** 500 prioritas teratas + 250 audit acak di world dev. Bias seleksi dikoreksi dengan inverse propensity weighting.
- **Kalibrasi:** isotonic pada prediksi out-of-fold. Stacking logistic menggabungkan ML dan persentil rules menjadi peluang terbukti.
- **Rentang Rp:** conformalized quantile regression yang dilatih dari pelanggar terbukti.
- **Di browser:** model diekspor ke [ml/artefak/model_payray.json](ml/artefak/model_payray.json) dan dievaluasi oleh JavaScript, termasuk atribusi fitur (Saabas) dan what-if. Ada parity check terhadap Python.
- **Panduan untuk orang awam:** tab Panduan di dashboard (analogi, cara membaca kolom dan grafik, glosarium, FAQ) dan tur interaktif 10 langkah (tombol "Tur 1 menit", atau `?tur=0`).
- **Data quality:** 17 pemeriksaan input ([ml/quality.py](ml/quality.py)). Laporan lengkap ada di [ml/artefak/laporan_ml.md](ml/artefak/laporan_ml.md).

| Holdout (top-10%) | Rules + IF | Model ML | **Gabungan** |
|---|---|---|---|
| Precision (CI 95%) | 68,4% (63–73) | 80,2% (75–86) | **82,2% (77–87)** |
| PR-AUC / ROC-AUC | 0,598 / 0,783 | 0,640 / 0,824 | **0,716 / 0,837** |
| Salah tandai UMKM patuh | 2,7% | 3,1% | **2,7%** |

Jika rules dan ML sama-sama menandai, precision mencapai 95,1% (n = 327). Hasil lain:
- Kalibrasi: ECE 0,035.
- Rentang Rp 80%: coverage 84% di holdout. Galat median turun dari 78% (kalkulator) ke 40%.
- Antrean nilai harapan (peluang × Rp) menangkap Rp17,9 M per 100 pemeriksaan (2,3× rules), dengan precision 52%.

## Generator data sintetis

```bash
pip install -r requirements.txt
python -m generator --out data                      # 5.000 badan usaha, ±35 detik
python -m generator --out data --n-employers 500    # versi kecil untuk iterasi
python -m generator.validate data                   # validasi ulang tanpa generate
python -m pytest
```

Prototype ini 100% sintetis. Tidak ada data peserta riil, dan `worker_id` adalah pseudonim (hash berkunci), bukan NIK.

### Cara kerja

1. **`world.py` membangun dunia nyata.** Semua pemberi kerja jujur: upah riil, rekrutmen, turnover, kenaikan merit, dan penyesuaian ke UMK tiap tahun. Sekitar 12% sengaja dibuat **hard negative**, yaitu patuh tapi tampak mencurigakan:
   - `padat_karya_umk`: industri padat karya yang sah membayar 85–97% pekerja tepat di UMK
   - `umkm_bawah_umk`: usaha mikro/kecil yang sah membayar di bawah UMK (PP 36/2021)
   - `phk_massal_sah`: PHK massal sungguhan, dengan sebagian korban pindah ke PBPU
   - `upah_seragam_sah`: usaha kecil dengan upah seragam
2. **`inject.py` menyisipkan pelanggaran secara blind** pada 15% badan usaha dengan seed rahasia. Setiap modus punya varian mudah dan sulit:

   | Modus | Mudah | Sulit |
   |---|---|---|
   | Upah | `lapor_umk` (semua dilaporkan = UMK), `upah_beku` (upah tak pernah diperbarui sampai jatuh di bawah UMK) | `potong_sebagian` (hanya pekerja bergaji tinggi dipotong 15–40%, tetap ≥ UMK) |
   | Headcount | 35–60% pekerja didaftarkan | 75–90% didaftarkan |
   | Status | 25–50% pekerja dipindah ke PBPU dalam 1 bulan | 8–18% tersebar 2–4 bulan |

   Sekitar 25% pelanggar punya dua modus sekaligus.
3. **`export.py` menulis output** dengan pemisahan akses (lihat di bawah).
4. **`validate.py` menulis `data/laporan_validasi.md`** berisi invarian, cek kebocoran label dari metadata, dan baseline aturan naif yang harus dikalahkan model.

### Protokol blind

| Folder | Siapa yang boleh baca |
|---|---|
| `data/publik/` | Semua (data "yang dilihat BPJS") |
| `data/referensi/` | Semua (UMK, sektor, benchmark upah ala Sakernas) |
| `data/label/` | **Hanya evaluator / penyisip pelanggaran** |

Penyisip menjalankan `python -m generator --inject-seed <angka rahasia>` dan menyimpan folder `label/` terpisah. Seed injeksi tidak ditulis ke `manifest.json`. Di PostgreSQL, pemisahan ini berupa skema `publik`, `referensi`, dan `label` dengan peran berbeda (lihat [db/schema.sql](db/schema.sql)):

```bash
pip install "psycopg[binary]"
python scripts/load_postgres.py --dsn postgresql://user:pass@localhost/payray            # tim model
python scripts/load_postgres.py --dsn postgresql://user:pass@localhost/payray_eval --with-labels
```

### Kamus data

**publik/employers.csv**: `employer_id`, `nama`, `kbli`, `nama_sektor`, `padat_karya`, `kode_wilayah`, `skala_usaha` (mikro/kecil/menengah/besar), `tahun_berdiri`, `tk_oss` (rencana tenaga kerja di NIB/OSS)

**publik/workers.csv**: pekerja yang terdaftar PPU: `worker_id`, `employer_id`, `tgl_masuk`, `tgl_keluar`, `tahun_lahir`, `jenis_kelamin`

**publik/wage_history.csv**: `worker_id`, `employer_id`, `tahun`, `upah_dilaporkan`, `bulan_aktif`

**publik/mutations.csv**: `mutation_id`, `worker_id`, `employer_id`, `tanggal`, `jenis` (DAFTAR_PPU / KELUAR_PPU), `segmen_tujuan` (PBPU / NONAKTIF / PPU_LAIN), `tgl_segmen_baru`, `alasan`

**referensi/benchmark_upah.csv**: median upah per sektor × wilayah × tahun, simulasi survei dengan galat ±3%. `median_upah` kosong jika `n_sampel` < 30. Wilayah ini harus mendapat keyakinan rendah.

**label/labels.csv**: `is_violator`, `modus`, `kesulitan` (mudah/sulit/hard_negative/normal), `hard_negative_type`, jumlah pekerja tersembunyi/dipindah/dipotong, `iuran_tak_tertagih_tahun_terakhir`, `iuran_tak_tertagih_total`. Kerugian kebenaran = iuran riil − iuran dilaporkan, sehingga pemberi kerja patuh selalu tepat 0.

**label/**: `hidden_workers.csv`, `moved_workers.csv`, dan `upah_riil.csv` untuk menguji akurasi kalkulator estimasi.

### Hasil run default (seed 42)

- 5.000 badan usaha, 450 ribu pekerja terdaftar, 1,28 juta baris upah
- 750 pelanggar (469 mudah, 281 sulit), 512 hard negative
- Aturan naif terbaik mencapai precision@10% 52,8%. Model GBM cepat dengan ±15 fitur mencapai **83,8%** (lift 5,6×, salah tandai UMKM 2,0%), dengan recall kasus sulit hanya 11%. Artinya target di CLAUDE.md bisa dicapai, tetapi data tidak trivial.

### Angka yang wajib diverifikasi sebelum submit

Semua ada di [generator/config.py](generator/config.py) dan [generator/reference.py](generator/reference.py):
- Tarif iuran PPU 5% (4% + 1%) dan plafon upah Rp12.000.000 (Perpres 64/2020)
- UMK 2024 per wilayah (perkiraan dari SK Gubernur) dan faktor kenaikan tahunan
- Pengecualian upah minimum UMKM (PP 36/2021)

## Struktur & cara jalan lokal (v2)

| Folder | Isi |
|---|---|
| `api/` | Backend FastAPI (auth, antrean, scan sheet, inspeksi, rescore) |
| `web/` | Frontend live: HTML/CSS/JS vanilla, di-serve API |
| `web-static/` | Build read-only untuk GitHub Pages (`scripts/build_static.py`) |
| `db/migrations/` | Migrasi SQL forward-only `NNN_*.sql` |
| `scripts/` | Seeder, migrasi, smoke test, build statis, eval |
| `tests/` | pytest (unit + integrasi ke DB `*_test`) |
| `design-system/payray/` | `MASTER.md`, acuan tunggal UI |
| `engine/`, `ml/`, `generator/` | Mesin scan, model, generator data sintetis |

Cara jalan lokal:
1. `cp .env.example .env`, lalu isi `PAYRAY_NIK_KEY` (≥ 32 byte).
2. `docker compose up -d` (Postgres 16 di `127.0.0.1:54329`, DB `payray_dev` + `payray_test`). Pakai `127.0.0.1`, bukan `localhost`: di Windows `localhost` resolve ke `::1` dan koneksi menggantung.
3. `pip install -r requirements.txt`
4. `python scripts/migrate.py` (forward-only, objek dimiliki `payray_migrator`), lalu `python -m generator --out data --seed 42 --inject-seed 4242`, `scripts/seed.py`, `scripts/seed_users.py`, `scripts/bootstrap_batch.py`.
5. `uvicorn api.main:app --reload`, buka `http://localhost:8000`.

Aturan agent: [AGENTS.md](AGENTS.md). Rencana: [plankit/PRD.md](plankit/PRD.md).

### Versi terpasang (TC-7)

Diverifikasi 2026-10-14 di venv lokal. Sumber kebenaran: `requirements.txt`.

| Komponen | Versi |
|---|---|
| Python | 3.12.4 (image `python:3.12-slim`) |
| PostgreSQL | 16.15 (`postgres:16`) |
| fastapi | 0.143.0 |
| uvicorn | 0.54.0 |
| psycopg[binary] | 3.3.6 |
| psycopg-pool | 3.3.3 |
| numpy | 2.5.4 |
| pandas | 3.0.6 |
| scikit-learn | 1.9.1 |
| scipy | 1.18.1 |
| pytest | 9.1.1 |
| httpx | 0.28.1 |
| ruff | 0.17.0 |
| mypy | 2.4.0 |
| pip-audit | 2.10.1 |
| bandit | 1.9.4 |

`requirements-scrape.txt` hanya untuk scraper portal BPJS, tidak dipakai API.

## Deploy & ukuran (v2)

- API + web live: `render.yaml` (Docker, free plan). Secret di dashboard Render: `DATABASE_URL` (login `payray_app`), `PAYRAY_NIK_KEY`.
- Pages statis: `.github/workflows/deploy-pages.yml` (manual; tidak otomatis di push agar tidak menimpa dashboard v1). Secret `PAGES_DATABASE_URL` memakai role khusus `payray_pages` (migrasi 007, `scripts/provision_pages_role.py`), bukan owner. Variabel `PAYRAY_LIVE_URL`.
- Backup: `.github/workflows/backup.yml` harian 02:00 WIB, `pg_dump --format=custom` (client 18), **dienkripsi AES-256 sebelum diunggah** karena repo publik, artefak 7 hari. Secret `BACKUP_DATABASE_URL` dan `BACKUP_PASSPHRASE`.
- Ukuran terukur lokal (2026-10-14, data dev 5.000 BU, cabang demo 3.137 BU): halaman Pages statis 1.912 KB mentah, **199 KB transfer gzip** (target M-10 ≤ 2 MB); bundle live HTML+CSS+JS tanpa font 25,5 KB gzip (target ≤ 150 KB); font 45 KB (target ≤ 200 KB). Pengukuran DevTools throttling 4G di Pages menunggu deploy pertama.
- Lokal: `python scripts/dev_server.py` (API sebagai `payray_app`), `python -m http.server 8766 --directory web-static` untuk mode statis.

## Production database (Neon) · 2026-10-14

- Project Neon `payray-healthkathon` (`spring-sea-12428949`), region AWS ap-southeast-1 (Singapore), **Postgres 18** (lokal/CI tetap Postgres 16; SQL kompatibel).
- Migrasi 001–006 bersih. Seed: 5.000 BU, 269.931 pekerja (NIK HMAC dengan key production terpisah), user demo, batch published kedua cabang, baseline 2026-09 dan 2026-10.
- **KILL-2 dicek di Neon: LULUS.** `scripts/check_permissions.py`: `payray_officer` dan `payray_scoring` mendapat permission denied di `label.ground_truth` dan `label.inspection_outcome`. Catatan: owner Neon bukan superuser, jadi migrasi 006 memberi `payray_migrator` hak SET ke role operasional.
- Smoke test API (dijalankan lokal, konek ke Neon sebagai `payray_app`): 5/5 lulus.
- Render: pembuatan web service ditolak (402, akun perlu kartu pembayaran terdaftar walau paket free). Deploy menunggu.
- Secret production hanya di `.env` lokal (`NEON_OWNER_URL`, `PROD_DATABASE_URL`, `PROD_NIK_KEY`, `PROD_DEMO_PASSWORD`, `PROD_APP_PASSWORD`), tidak di repo.
