# PayRay: Informasi Menyeluruh

Rontgen kepatuhan pemberi kerja untuk JKN. Healthkathon 2026, tema "Detect Smarter, Protect JKN".

Dokumen ini merangkum konsep, mesin deteksi, data, hasil, arsitektur, keamanan, status, dan keterbatasan PayRay. Sumber: `CLAUDE.md`, `README.md`, `docs/BUKTI_PROPOSAL.md`, `PayRay_Penjelasan_Lengkap.txt`, dan kode di `engine/`, `ml/`, `generator/`, `api/`, `db/`. Semua angka performa berasal dari **data simulasi**, bukan data peserta riil.

---

## 1. Ringkasan

PayRay (Pay + X-Ray) adalah sistem skor risiko berbasis AI untuk badan usaha pemberi kerja peserta JKN. Sistem memberi skor ke semua badan usaha, lalu petugas pemeriksa BPJS Kesehatan memeriksa yang paling berisiko lebih dulu.

Keluaran PayRay adalah daftar prioritas pemeriksaan, bukan tuduhan. Setiap skor datang dengan tingkat keyakinan, alasan yang bisa dibaca, dan estimasi potensi iuran tak tertagih dalam rupiah. Keputusan pemeriksaan dan sanksi tetap di tangan petugas.

Kalimat kunci: "PayRay membantu petugas memeriksa yang tepat, lebih dulu."

| Item | Isi |
|---|---|
| Kategori lomba | Peserta JKN & Pemberi Kerja (satu tim, satu kategori) |
| Sub-kategori | Under-reporting upah, pendaftaran pekerja sebagian, misklasifikasi status kerja |
| Aturan data | Data peserta riil dilarang. Prototype memakai data sintetis dan data publik |
| Pitch deck | Maksimal 20 slide, 9 komponen wajib. Revisi saat ini 20 slide |
| Repo | https://github.com/rachdiaan/healthkathon-bpjs (publik) |
| Demo statis | https://rachdiaan.github.io/healthkathon-bpjs/ |

---

## 2. Asal-usul ide dan nama

Ada enam kandidat ide, tiga per kategori:

- Peserta JKN & Pemberi Kerja: RAPOR, JejakNIK, Iuran Watch
- Fasilitas Kesehatan: KodeJujur, Notif Layanan, RujukGraph

Skor ranking: KodeJujur 25, Notif Layanan 25, RAPOR 24, RujukGraph 23, Iuran Watch 21, JejakNIK 21. Tim memilih RAPOR (kemudian diganti nama menjadi PayRay) karena paling realistis untuk tim engineer, datanya aman (publik + sintetis), dan dampaknya mudah dihitung dalam rupiah.

Metafora nama: rontgen memperlihatkan yang tersembunyi di balik kulit, PayRay memperlihatkan upah dan pekerja yang tersembunyi di balik laporan. Skor risiko adalah hasil scan, kartu risiko adalah lembar hasil scan, dan tiga modul adalah tiga sudut pandang scan.

---

## 3. Masalah yang diselesaikan

Iuran PPU (Pekerja Penerima Upah) adalah 5% dari upah: 4% ditanggung pemberi kerja, 1% dipotong dari upah pekerja. Dasar upah memiliki batas bawah (UMK/UMP, dengan pengecualian usaha mikro dan kecil) dan batas atas (di kode: Rp12.000.000 per bulan). Setiap rupiah upah yang tidak dilaporkan, dan setiap pekerja yang tidak didaftarkan, langsung mengurangi iuran yang masuk ke dana JKN.

Tiga modus kebocoran:

1. **Under-reporting upah.** Upah dilaporkan setara UMK, padahal upah riil lebih tinggi.
2. **Pendaftaran pekerja sebagian.** Hanya sebagian karyawan yang didaftarkan sebagai PPU.
3. **Misklasifikasi status kerja.** Pekerja yang masih bekerja dipindahkan ke PBPU (segmen mandiri) supaya perusahaan lepas dari porsi 4%.

Ketiga modus sering muncul bersamaan di satu badan usaha. Karena itu ketiganya digabung dalam satu solusi.

### Skala masalah (bukti publik)

| Fakta | Angka | Sumber | Status |
|---|---|---|---|
| Peserta JKN | 282,8 juta (30 Sep 2026) | Portal Data BPJS Kesehatan | Primer |
| Peserta PPU Badan Usaha | 47.024.587 (16,6%) | Portal Data BPJS Kesehatan | Primer |
| Peserta PBPU | 32.040.621 | Portal Data BPJS Kesehatan | Primer |
| Pendapatan iuran PPU BU & PN yang "tidak dapat diyakini kebenarannya" | Rp31,61 T | BPK, IHPS II 2025, via Monitor Indonesia (15 Jun 2026) | Sekunder, PDF IHPS belum dicek |
| Badan usaha terdata di Tulungagung yang mendaftarkan pekerjanya | 416 dari 1.092 (38%) | ANTARA Jatim, 20 Jun 2026 | Sekunder, bukti lokal |

Catatan framing: angka Rp31,61 T **bukan** nilai kebocoran. Artinya kebenaran pendapatan iuran PPU tidak bisa dipastikan dari data yang ada. Celah verifikasi itulah yang diisi PayRay. Jumlah badan usaha terdaftar secara nasional dan nilai tunggakan iuran PPU belum tersedia di portal, sehingga harus diambil dari Laporan Pengelolaan Program atau LHP BPK.

---

## 4. Cara kerja

Perubahan alur kerja:

- **Sebelum:** pilih target dulu berdasarkan informasi terbatas, lalu periksa.
- **Sesudah:** scan semua badan usaha otomatis tiap periode, lalu petugas memilih dari skor tertinggi.

Alur end-to-end:

1. Data masuk: kepesertaan dan upah PPU per badan usaha, UMK, benchmark upah sektor-wilayah (BPS), skala usaha dan KBLI.
2. Tiga modul scan menghitung sinyal.
3. Isolation Forest mencari kombinasi anomali yang tidak tertangkap aturan.
4. Sinyal digabung menjadi skor 0 sampai 100, tingkat keyakinan, dan alasan utama.
5. Kalkulator menghitung estimasi potensi iuran tak tertagih.
6. Dashboard menampilkan ranking dan lembar hasil scan.
7. Petugas menjadwalkan pemeriksaan atau menandai wajar.
8. Hasil pemeriksaan kembali menjadi label untuk melatih ulang model.

---

## 5. Tiga modul scan

Mesin transparan ada di `engine/rules.py`: **7 aturan dalam 3 modul**. Pembanding selalu badan usaha sejenis (sektor KBLI × skala usaha). Aturan dibedakan per skala usaha karena UMKM dikecualikan dari upah minimum (PP 36/2021).

| Modul | Aturan | Bobot | Yang dideteksi |
|---|---|---|---|
| Upah | `bunching_umk` | 0,8 | Porsi karyawan tepat di UMK jauh di atas pola sektor sejenis, atau tidak ada satu pun di atas UMK pada usaha ≥ 10 orang |
| Upah | `naik_sama_umk` | 0,5 | Kenaikan upah selalu persis sama dengan kenaikan UMK |
| Upah | `upah_beku` | 0,9 | Upah tidak naik saat UMK naik |
| Upah | `bawah_umk_wajib` | 0,9 | Upah di bawah UMK pada usaha menengah/besar yang wajib UMK |
| Upah | `upah_atas_rendah` | 0,6 | Upah 10% teratas jauh di bawah sektor-wilayah sejenis (pemotongan selektif), plus selisih terhadap benchmark BPS |
| Headcount | `headcount_oss` | 0,9 | Rata-rata pekerja terdaftar jauh di bawah rencana tenaga kerja di OSS/NIB |
| Status | `klaster_pbpu` | 0,9 | Pekerja keluar PPU lalu terdaftar PBPU dalam ≤ 30 hari, berkelompok dalam 3 bulan, bukan karena PHK |

Detail penting:

- Aturan upah butuh minimal 5 pekerja (beberapa 8 atau 10), supaya usaha sangat kecil tidak salah ditandai.
- `headcount_oss` memberi bobot keandalan lebih rendah untuk usaha 1 sampai 3 orang.
- Perbandingan dengan kepesertaan BPJS Ketenagakerjaan (sinyal headcount terkuat) **tidak ada di prototype**. Itu butuh kerja sama antarinstansi dan masuk fase lanjut.
- Cek "pekerja masih aktif bekerja" untuk modul status juga butuh data BPJS TK, sehingga masuk fase lanjut.

---

## 6. Skor gabungan, keyakinan, dan reason code

**Skor.** Aturan digabung dengan noisy-OR, lalu dikombinasikan dengan Isolation Forest yang distandarkan per skala usaha. Hasilnya skor 0 sampai 100 dengan kategori Rendah, Sedang, Tinggi. Kategori selalu ditulis dalam teks, tidak hanya lewat warna.

**Tingkat keyakinan** (tinggi, sedang, rendah). Dihitung dari kelengkapan data dan kekuatan benchmark. Wilayah atau sektor dengan data sedikit (`n_sampel` < 30) mendapat keyakinan rendah dan tidak diprioritaskan. Antrean pemeriksaan hanya memuat risiko ≥ sedang **dan** keyakinan ≥ sedang.

**Reason code.** Setiap skor membawa tiga alasan utama dalam bahasa biasa. Contoh keluaran aturan: "92% karyawan dilaporkan tepat di UMK (median sektor sejenis 31%)". Lapis model dijelaskan lewat atribusi fitur, lalu diterjemahkan ke kalimat.

### Contoh lembar hasil scan nyata

`hasil/lembar_scan/BU04224.md`: PT Cahaya Mandiri, industri kulit dan alas kaki, 49 pekerja dilaporkan (data sintetis).

- Skor 98/100, keyakinan tinggi
- 24 pekerja keluar PPU lalu terdaftar PBPU ≤ 30 hari dalam 3 bulan (46% tenaga kerja), alasan bukan PHK
- Rata-rata pekerja terdaftar 48 orang, rencana tenaga kerja di OSS 112 orang (43%)
- Kombinasi pola tidak biasa dibanding usaha seskala
- Estimasi Rp212 juta per tahun, kerugian sebenarnya di data simulasi Rp215 juta per tahun

---

## 7. Kalkulator estimasi iuran tak tertagih

Rumus dasar:

```
min(upah_wajar, plafon) - min(upah_dilaporkan, plafon)  ×  5%  ×  jumlah pekerja  ×  12
```

Ditambah komponen untuk modul lain:

- **Headcount:** estimasi pekerja tidak terdaftar × upah acuan × 5% × 12.
- **Status:** pekerja yang dipindah ke PBPU × upah acuan × 4% × 12 (porsi pemberi kerja yang hilang).

"Upah wajar" diambil dari median sektor-wilayah. Output selalu disebut "estimasi" dan "potensi", bukan kerugian pasti. Angka rupiah membantu prioritas: usaha berskor sedang tapi berskala besar bisa layak diperiksa lebih dulu daripada usaha kecil berskor tinggi.

Keterbatasan: korelasi kalkulator rule-based dengan kerugian sebenarnya baru sekitar 0,34 (log). Lapisan ML menurunkan galat median dari 78% ke 40% lewat rentang kuantil (lihat bagian 8).

---

## 8. Lapisan machine learning (`ml/`)

Lapisan ini adalah second opinion yang independen dari aturan.

- **Model:** HistGradientBoosting, 250 pohon, 17 fitur mentah, dengan monotonic constraint sesuai logika domain. Sengaja tidak memakai skor rules.
- **Label hanya dari hasil pemeriksaan:** 500 prioritas teratas ditambah 250 audit acak di dunia dev. Bias seleksi dikoreksi dengan inverse propensity weighting (IPW).
- **Kalibrasi:** isotonic pada prediksi out-of-fold. Stacking logistic menggabungkan ML dan persentil rules menjadi peluang terbukti.
- **Rentang Rp:** conformalized quantile regression (CQR) dari pelanggar terbukti, rentang 80%.
- **Di browser:** model diekspor ke `ml/artefak/model_payray.json` dan dievaluasi oleh JavaScript, termasuk atribusi fitur (Saabas) dan simulasi what-if, dengan parity check terhadap Python.
- **Data quality:** 17 pemeriksaan input di `ml/quality.py`. Laporan di `ml/artefak/laporan_ml.md`.
- **Pembekuan:** artefak model dan interval Rp di-hash di `ml/FROZEN.txt` sebelum evaluasi blind. CI memeriksa hash.

---

## 9. Hasil evaluasi (data simulasi)

### Mesin aturan + Isolation Forest (top-10%, tanpa label saat menilai)

| Metrik | Dev (seed 42) | Holdout (seed 2026) | Target |
|---|---|---|---|
| Precision@10% | 69,4% | **68,4%** | ≥ 70% |
| Lift vs acak | 4,63× | **4,56×** | ≈ 4,7× |
| Salah tandai UMKM patuh | 2,5% | **2,7%** | ≤ 5% |
| Iuran tertangkap per 100 pemeriksaan | Rp7,9 M vs Rp0,63 M acak | Rp7,7 M vs Rp0,53 M acak (14,6×) | > acak |

Generator dikalibrasi ke upah BPS Sakernas Agustus 2025 (korelasi urutan sektor ρ = 0,90), lalu data dibuat ulang dengan seed injeksi baru. Mesin tidak disetel ulang setelah regenerasi.

### Lapisan ML (holdout, top-10%)

| | Rules + IF | Model ML | Gabungan |
|---|---|---|---|
| Precision (CI 95%) | 68,4% (63–73) | 80,2% (75–86) | **82,2% (77–87)** |
| PR-AUC / ROC-AUC | 0,598 / 0,783 | 0,640 / 0,824 | **0,716 / 0,837** |
| Salah tandai UMKM patuh | 2,7% | 3,1% | **2,7%** |

- Jika rules dan ML sama-sama menandai, precision 95,1% (n = 327).
- Kalibrasi: ECE 0,035.
- Rentang Rp 80%: coverage 84% di holdout.
- Antrean nilai harapan (peluang × Rp) menangkap Rp17,9 M per 100 pemeriksaan (2,3× rules), dengan precision 52%.

### Siklus umpan balik

Belajar dari 500 hasil pemeriksaan ditambah 250 audit acak menaikkan precision putaran berikutnya dari sekitar 22% menjadi 25–27%, dan iuran yang tertangkap ikut naik (Rp1,60 M ke Rp1,81 M).

### Kelemahan yang sudah diketahui

- Recall modus sulit rendah: `potong_sebagian` sekitar 18–20%, `daftar_sebagian` sekitar 35–37%.
- Kalkulator Rp rule-based berkorelasi 0,34 dengan kerugian sebenarnya.
- Salah tandai di usaha menengah/besar sekitar 6–7%, sebagian besar usaha padat karya sah yang membayar UMK.
- Recall maksimum di top-10% secara matematis 66,7% (750 pelanggar, 500 slot).

Catatan: data `data/` saat ini **bukan blind**. Penyisipan final oleh anggota non-model dengan `--inject-seed` rahasia masih tertunda.

---

## 10. Generator data sintetis

Dijalankan dengan `python -m generator --out data`. Menghasilkan 5.000 badan usaha, sekitar 450 ribu pekerja terdaftar, dan 1,28 juta baris riwayat upah (seed 42).

**Langkah:**

1. `world.py` membangun dunia jujur (upah riil, rekrutmen, turnover, kenaikan merit, penyesuaian UMK). Sekitar 12% sengaja dibuat **hard negative**: patuh tapi tampak mencurigakan.
2. `inject.py` menyisipkan pelanggaran secara **blind** pada 15% badan usaha dengan seed rahasia.
3. `export.py` menulis output dengan pemisahan akses.
4. `validate.py` menulis laporan validasi (invarian, cek kebocoran label, baseline aturan naif).

**Hard negative:**

| Tipe | Deskripsi |
|---|---|
| `padat_karya_umk` | Industri padat karya sah, 85–97% pekerja tepat di UMK |
| `umkm_bawah_umk` | Usaha mikro/kecil sah membayar di bawah UMK |
| `phk_massal_sah` | PHK massal sungguhan, sebagian korban pindah ke PBPU |
| `upah_seragam_sah` | Usaha kecil dengan upah seragam |

**Modus pelanggaran:**

| Modus | Mudah | Sulit |
|---|---|---|
| Upah | `lapor_umk`, `upah_beku` | `potong_sebagian` (pekerja bergaji tinggi dipotong 15–40%, tetap ≥ UMK) |
| Headcount | 35–60% pekerja didaftarkan | 75–90% didaftarkan |
| Status | 25–50% dipindah ke PBPU dalam 1 bulan | 8–18% tersebar 2–4 bulan |

Sekitar 25% pelanggar punya dua modus sekaligus. Hasil run default: 750 pelanggar (469 mudah, 281 sulit) dan 512 hard negative. Aturan naif terbaik hanya mencapai precision@10% 52,8%.

**Protokol blind (pemisahan akses):**

| Folder / skema | Pembaca |
|---|---|
| `data/publik/` | Semua (yang "dilihat BPJS") |
| `data/referensi/` | Semua (UMK, sektor, benchmark upah) |
| `data/label/` | Hanya evaluator/penyisip pelanggaran |

Di PostgreSQL, pemisahan ini berupa skema dan peran berbeda, dan guard `GR-11` melarang agent membaca atau menyetel ulang memakai data holdout/blind di luar `scripts/eval_blind.py`.

`worker_id` adalah pseudonim (hash berkunci), bukan NIK.

---

## 11. Data publik yang sudah diambil

| Data | Sumber | Lokasi |
|---|---|---|
| Kepesertaan per segmen, faskes, 16 artikel | Portal Data BPJS Kesehatan | `data_publik/bpjs_portal/` |
| 75 dataset Statistik JKN 2014–2018 (XLSX → CSV + kamus) | DJSN via Portal Data BPJS | `data_publik/bpjs_portal/` |
| Upah buruh per lapangan usaha, Sakernas Agustus 2025 | BPS (sekunder via CNBC, perlu dicocokkan ke bps.go.id) | `data_publik/bps/` |

Scraper: `scripts/scrape_bpjs_portal.py`. Tren PPU: 24,3 juta (2014), 49,8 juta (2018), 68,4 juta PPU PN+BU (Sep 2026).

---

## 12. Arsitektur dan stack

**Stack:** Python 3.12, FastAPI, PostgreSQL 16 (lokal/CI) dan Postgres 18 di Neon (produksi), scikit-learn, HTML/CSS/JS vanilla untuk frontend.

Versi terpasang (diverifikasi 14 Okt 2026, sumber kebenaran `requirements.txt`): fastapi 0.143.0, uvicorn 0.54.0, psycopg 3.3.6, numpy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1, scipy 1.18.1, pytest 9.1.1.

| Folder | Isi |
|---|---|
| `generator/` | Generator data sintetis |
| `engine/` | Mesin scan: fitur, aturan, skor, evaluasi, umpan balik |
| `ml/` | Model ML, kalibrasi, rentang Rp, data quality, artefak |
| `api/` | Backend FastAPI: auth, antrean, lembar hasil scan, inspeksi, rescore, metrik |
| `web/` | Frontend live, di-serve oleh API |
| `web-static/` | Build read-only untuk GitHub Pages |
| `dashboard/` | Dashboard HTML statis v1 (model berjalan di browser) |
| `db/migrations/` | Migrasi SQL forward-only `001` sampai `007` |
| `scripts/` | Seeder, migrasi, smoke test, build statis, evaluasi |
| `tests/` | pytest (unit dan integrasi ke DB `*_test`) |
| `design-system/payray/` | `MASTER.md`, acuan tunggal UI |
| `plankit/` | PRD, daftar task, token desain |

### Endpoint API (`/api`)

| Grup | Endpoint |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /me` |
| Antrean | `GET /queue`, `GET /queue.csv`, `GET /summary` |
| Lembar hasil scan | `GET /employers/{employer_id}/scan-sheet` |
| Inspeksi | `POST /inspections`, `GET /inspections`, `GET /inspections/mine`, `POST /inspections/{id}/supersede`, `POST /inspections/{id}/cancel` |
| Rescore | `POST /rescore-batches`, `GET /rescore-batches`, `GET /rescore-batches/{id}`, `POST /rescore-batches/{id}/publish` |
| Metrik dan audit | `GET /metrics`, `GET /audit-events` |

### Skema database

Empat skema di migrasi 001: `core`, `ops`, `label`, `audit`. Peran DB: `payray_app`, `payray_officer`, `payray_supervisor`, `payray_scoring`, `payray_migrator`, dan `payray_pages` (khusus build statis).

### Peran pengguna

- **Officer (petugas):** melihat antrean cabangnya, membuka lembar hasil scan, mencatat hasil pemeriksaan.
- **Supervisor:** peran tambahan untuk rescore batch, publikasi, dan metrik.
- Tidak ada self-registration. Akun demo dibuat per cabang oleh `scripts/seed_users.py`, ditambah akun tamu `pengunjung` (peran petugas, cabang 1) dengan password terpisah.

### UI

Gaya konsol "Meridian" dengan palet Kemenkes (turqoise dan hijau kuning). Tampilan mencakup Ringkasan, antrean, lembar hasil scan, Validasi, dan Cara kerja. Dashboard v1 punya tab Validasi model, Kualitas data, Metodologi, Panduan, dan tur interaktif 10 langkah.

---

## 13. Keamanan, privasi, dan etika

**Keamanan:**

- NIK dipseudonimisasi (HMAC dengan kunci `PAYRAY_NIK_KEY`, kunci produksi terpisah dari dev).
- Akses berbasis peran, diterapkan sampai level DB lewat `SET LOCAL ROLE`.
- Audit log untuk setiap aksi, termasuk `authz.denied`.
- Peran `payray_officer` dan `payray_scoring` ditolak akses ke `label.ground_truth` dan `label.inspection_outcome` (diuji di Neon dan lulus: KILL-2).
- Backup harian 02:00 WIB dengan `pg_dump`, dienkripsi AES-256 sebelum diunggah karena repo publik. Artefak disimpan 7 hari.
- CI: gitleaks, `pip-audit`, `bandit`, `ruff`, `mypy`, pemeriksaan hash model beku.

**Etika dan bias:**

- UU PDP: analisis agregat per badan usaha, NIK dipseudonimisasi.
- Aturan dibedakan per skala usaha karena UMKM dikecualikan dari upah minimum.
- Wilayah dengan data sedikit mendapat keyakinan rendah dan tidak diprioritaskan.
- Human-in-the-loop: PayRay hanya mengurutkan. Keputusan pemeriksaan dan sanksi di petugas.
- Mitigasi: salah tandai diatasi dengan ambang skor dan review petugas, model usang dengan retrain dari umpan balik, kebocoran data dengan minimisasi dan enkripsi.

---

## 14. Deploy dan operasi

| Komponen | Status |
|---|---|
| Neon (Postgres 18, Singapore) | Migrasi 001 sampai 006 bersih, seed 5.000 BU dan 269.931 pekerja, smoke test 5/5 lulus |
| Render (API + web live, `render.yaml`) | Web service ditolak (402, perlu kartu pembayaran terdaftar). Deploy menunggu |
| GitHub Pages (build statis) | Workflow manual `deploy-pages.yml`, memakai role `payray_pages` |
| Backup terenkripsi | Workflow `backup.yml` diperbaiki dan diverifikasi end-to-end pada 19 Okt 2026 |

Ukuran terukur lokal: halaman Pages statis 199 KB transfer gzip (target ≤ 2 MB), bundle live 25,5 KB gzip (target ≤ 150 KB), font 45 KB (target ≤ 200 KB).

Menjalankan lokal:

```bash
cp .env.example .env            # isi PAYRAY_NIK_KEY (≥ 32 byte)
docker compose up -d            # Postgres 16 di 127.0.0.1:54329
pip install -r requirements.txt
python scripts/migrate.py
python -m generator --out data --seed 42 --inject-seed 4242
python scripts/seed.py && python scripts/seed_users.py && python scripts/bootstrap_batch.py
uvicorn api.main:app --reload   # http://localhost:8000
python -m engine --data data --out hasil --evaluate
python -m ml
python -m pytest
```

Pakai `127.0.0.1`, bukan `localhost`: di Windows `localhost` resolve ke `::1` dan koneksi menggantung.

---

## 15. Guardrail pengembangan (agent)

Dari PRD §20, GR-6 sampai GR-13:

- **GR-6** Agent hanya mengerjakan scope task.
- **GR-7** Tidak menambah dependency di luar §18 (CI memeriksa diff `requirements.txt`).
- **GR-8** Tidak meng-commit secret (gitleaks + `.gitignore`).
- **GR-9** Tidak menonaktifkan, skip, atau melonggarkan tes.
- **GR-10** Tidak menjalankan migrasi destruktif tanpa perintah eksplisit.
- **GR-11** Tidak membaca, menjalankan, atau me-retune memakai data holdout/blind di luar `scripts/eval_blind.py`.
- **GR-12** Bila keputusan tidak ada di dokumen, berhenti dengan status `blocked`.
- **GR-13** Tes tidak pernah jalan terhadap DB selain `*_test`.

Konvensi: `main` terproteksi, kerja di branch `feat/<task-id>-<slug>`, PR wajib CI hijau dan satu review anggota lain, squash merge.

---

## 16. Pitch deck

File: `docs/deck/PayRay_Healthkathon2026_revisi.pptx` dan `.pdf`. Generator: `docs/deck/build_deck.js`.

- Tema rontgen gelap dengan aksen hijau limau. Font Montserrat (judul) dan Source Sans 3 (isi).
- 20 slide, memetakan 9 komponen wajib: identitas dan positioning, masalah dan urgensi, solusi, pendekatan teknis dan data, tingkat kematangan, rencana dan kelayakan, dampak dan manfaat, risiko dan etika, profil tim.
- Revisi sudah menambah slide desain validasi data sintetis, hasil dan demo, serta alur kerja petugas.

Item pitch deck yang perlu dicek ulang atau masih terbuka ada di bagian 18.

---

## 17. Rencana dan roadmap

**Rencana 8 minggu:**

| Minggu | Deliverable | Status |
|---|---|---|
| 1–2 | Generator data sintetis + data benchmark publik | Selesai |
| 3–4 | Tiga modul scan + skor gabungan + reason code | Selesai |
| 5–6 | Dashboard, lembar hasil scan, kalkulator | Selesai (dashboard statis + versi API) |
| 7 | Laporan akurasi + uji bias per skala usaha | Selesai |
| 8 | Video demo + proposal final | Video demo belum |

**Setelah kompetisi:**

- **Fase 1 (±3 bulan):** pilot di satu Kantor Cabang dengan data riil berizin, kalibrasi dengan hasil pemeriksaan.
- **Fase 2 (±6 bulan):** integrasi BPJS Ketenagakerjaan dan OSS, Scan Headcount versi penuh, Scan Status dengan cek pekerja aktif.
- **Fase 3 (bertahap):** skala nasional, scan rutin tiap periode, dashboard per wilayah.

Kebutuhan dari BPJS Kesehatan: akses data berizin, mitra Kantor Cabang, infrastruktur aman, pendampingan petugas pemeriksa.

---

## 18. Status dan yang masih terbuka

**Selesai:**

- Generator data sintetis dengan protokol blind dan laporan validasi
- Scraper dan data Portal BPJS
- Mesin scan (7 aturan, Isolation Forest, skor, keyakinan, reason code, estimasi Rp, simulasi umpan balik)
- Lapisan ML (HistGB, stacking, isotonic, CQR, 17 data quality checks)
- Dashboard statis v1 dan aplikasi v2 (API FastAPI + PostgreSQL + frontend)
- Pitch deck revisi 20 slide
- Backup terenkripsi, CI, migrasi, dan tes

**Masih terbuka:**

- Penyisipan final oleh anggota non-model dengan `--inject-seed` rahasia, untuk evaluasi blind sungguhan
- Deploy API live (Render menolak pembuatan service)
- Video demo
- Perbaikan kalkulator Rp rule-based (korelasi 0,30–0,36)
- Ambil data upah BPS asli dari bps.go.id (benchmark di generator masih simulasi yang dikalibrasi)
- Isi slide 4: jumlah badan usaha terdaftar dan nilai iuran/tunggakan PPU dari Laporan Pengelolaan Program atau LHP BPK
- Cek PDF IHPS II 2025 untuk angka Rp31,61 T
- Merge PR #2 (`chore/t4-done`) menunggu review

**Regulasi yang wajib dicek sebelum submit:**

- Tarif iuran PPU 5% (4% + 1%): Perpres 82/2018 jo. 64/2020 jo. 59/2024
- Plafon upah Rp12.000.000: Perpres 59/2024 Pasal 32 ayat (1), belum diverifikasi ke teks resmi
- Pengecualian upah minimum untuk usaha mikro/kecil: PP 36/2021 jo. PP 51/2023 jo. PP 49/2025, perlu dicek apakah ada perubahan
- Nilai UMK 2024 per wilayah di generator adalah perkiraan, bukan dari SK Gubernur resmi

Semua konstanta regulasi ada di `engine/params.py` dan `generator/config.py`, dengan catatan sumber dan status verifikasi.

---

## 19. Tim "Plan with Us"

| Nama | Peran |
|---|---|
| Rachdian Habi Yahya | Ketua Tim, Data Scientist (pemodelan, evaluasi, uji bias). Mahasiswa S2 Digital Business Strategy, Telkom University |
| Rifqi Sigwan Nugraha | Lead Engineer, Backend & AI. Lulusan IT Telkom University, co-founder Plus The Site. Python, FastAPI, PostgreSQL, multi-agent AI |
| Muhammad Al Ghani | Product Manager (kebutuhan petugas, alur kerja, desain dashboard, proposal dan demo). UI/UX Designer di Torch.id |

Kontak tim: rachdiaaan@gmail.com. Tim tidak punya Domain Expert, sehingga aturan deteksi perlu divalidasi lewat konsultasi pakar HR-payroll atau jaminan sosial.

---

## 20. Kekuatan dan kelemahan jujur

**Kekuatan:**

- Masalah nyata, dampak mudah dikonversi ke rupiah
- Data aman (publik + sintetis), tidak melanggar aturan lomba
- AI tepat guna dan bisa dijelaskan: reason code, atribusi fitur, kalibrasi, dan rentang Rp
- Penanganan UMKM dan tingkat keyakinan menunjukkan kematangan
- Protokol blind, hard negative, dan pelaporan kelemahan terbuka

**Kelemahan:**

- Inovasi sedang: pencocokan data lintas instansi adalah konsep yang sudah dikenal. Pembeda ada di eksekusi (skor menyeluruh, alasan terbaca, estimasi rupiah, perlindungan UMKM)
- Validitas pada data riil belum terbukti sampai pilot
- Scan Headcount dan Scan Status versi kuat bergantung pada integrasi data BPJS TK yang belum ada
- Evaluasi saat ini belum blind sungguhan
- Tidak ada anggota berlatar domain jaminan sosial
- Semua angka performa adalah hasil simulasi

---

## 21. FAQ singkat untuk juri

**Data sintetis tidak sama dengan data riil. Bagaimana tahu ini bekerja?**
Data sintetis membuktikan logika dan mengukur akurasi secara terkontrol, dengan kasus sulit yang sah disisipkan. Validasi sebenarnya ada di pilot Fase 1 dengan data berizin.

**Apa bedanya dengan pemeriksaan yang sudah ada?**
PayRay tidak menggantikan pemeriksaan. PayRay memperbaiki cara memilih siapa yang diperiksa: dari informasi terbatas menjadi scan menyeluruh dengan alasan dan nilai rupiah.

**Bagaimana kalau UMKM salah ditandai?**
Aturan dibedakan per skala usaha, ada tingkat keyakinan dan ambang skor, keputusan di petugas, dan salah tandai UMKM diukur khusus (2,7% di holdout, target ≤ 5%).

**Kenapa Isolation Forest, bukan hanya supervised?**
Label pelanggaran riil langka di awal. Isolation Forest tidak butuh label. Setelah ada hasil pemeriksaan, label itu melatih model ML supervised (sudah disimulasikan, precision naik ke 82,2%).

**Bagaimana dengan privasi pekerja?**
Analisis agregat per badan usaha, NIK dipseudonimisasi, enkripsi, akses berbasis peran sampai level DB, audit log. Prototype tidak menyentuh data riil.

**Kenapa integrasi BPJS Ketenagakerjaan tidak ada di prototype?**
Butuh kerja sama antarinstansi yang tidak bisa diklaim sekarang. Itu ditaruh di Fase 2 supaya rencana tetap jujur.
