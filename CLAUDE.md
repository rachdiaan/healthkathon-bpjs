# PayRay — Konteks Proyek (Healthkathon 2026)

> File konteks untuk Claude Code. Taruh di root repo. Berisi ringkasan keputusan dari sesi diskusi di claude.ai.

## Ringkasan
**PayRay** (Pay + X-Ray), "rontgen kepatuhan pemberi kerja untuk JKN". Sistem skor risiko berbasis AI yang memberi skor ke semua badan usaha, sehingga petugas pemeriksa BPJS Kesehatan memeriksa yang paling berisiko lebih dulu. PayRay **tidak menuduh**: outputnya daftar prioritas pemeriksaan beserta alasannya.

- Lomba: Healthkathon 2026 · tema "Detect Smarter, Protect JKN"
- Kategori: **Peserta JKN & Pemberi Kerja** (aturan: 1 tim = 1 kategori)
- Sub-kategori: Under-reporting Upah, Pendaftaran Pekerja Sebagian, Misklasifikasi Status Kerja
- Aturan data: **data peserta riil dilarang**. Prototype 100% data sintetis + data publik.
- Pitch deck: maks 20 slide, 9 komponen wajib. Draft saat ini 17 slide.

## Kenapa ide ini dipilih
Ada 6 kandidat ide (3 per kategori). Hasil ranking: KodeJujur 25, Notif Layanan 25, RAPOR 24, RujukGraph 23, Iuran Watch 21, JejakNIK 21.
Tim memilih RAPOR (yang kemudian diganti nama jadi PayRay) karena paling realistis untuk tim engineer, datanya aman (publik + sintetis), dan dampaknya mudah dihitung dalam rupiah.

## Masalah
Iuran PPU = 5% dari upah (4% pemberi kerja, 1% pekerja), dengan plafon upah iuran (cek angka terbaru). Tiga modus kebocoran:
1. Upah dilaporkan setara UMK, padahal upah riil lebih tinggi
2. Hanya sebagian karyawan yang didaftarkan
3. Pekerja dipindah ke PBPU (segmen mandiri) supaya perusahaan lepas dari porsi 4%

## Tiga modul scan
**Scan Upah**
- Bunching: % karyawan tepat di UMK jauh di atas pola wajar sektornya
- Upah seragam: hampir semua karyawan dilaporkan dengan upah identik
- Kenaikan upah selalu persis sama dengan kenaikan UMK, tidak pernah lebih
- Upah stagnan sampai turun di bawah UMK (pola terpisah)
- Upah jauh di bawah median sektor dan wilayah (BPS)

**Scan Headcount**
- Jumlah pekerja dibandingkan skala usaha (NIB/OSS) dan pola sektor (KBLI)
- Fase lanjut: dicocokkan dengan kepesertaan BPJS Ketenagakerjaan (butuh kerja sama antarinstansi)

**Scan Status**
- Klaster perpindahan PPU ke PBPU dari satu pemberi kerja dalam waktu berdekatan
- Cek "pekerja masih aktif bekerja" butuh data BPJS TK, jadi masuk **fase lanjut**, bukan prototype

## Arsitektur teknis
- Stack: Python, FastAPI, PostgreSQL, scikit-learn, dashboard web
- Mesin scan:
  - aturan bisnis transparan (menangkap pola yang sudah dikenal)
  - Isolation Forest (menangkap kombinasi anomali yang belum dirumuskan)
  - skor gabungan + reason code (SHAP sebagai pelengkap)
- Output:
  - ranking risiko per badan usaha
  - lembar hasil scan berisi skor, keyakinan, dan 2–3 alasan utama
  - antrean pemeriksaan
  - hasil pemeriksaan petugas masuk lagi sebagai label baru
- Kalkulator estimasi iuran tak tertagih:
  `min(upah_wajar, plafon) - min(upah_dilaporkan, plafon)` × 5% × jumlah pekerja × 12, ditambah pekerja yang dipindah ke PBPU
- Keamanan: enkripsi, akses berbasis peran, audit log, NIK dipseudonimisasi

## Generator data sintetis (deliverable pertama)
- 5.000 badan usaha, 15% disisipi pelanggaran, label diketahui
- Atribut: sektor (KBLI), wilayah (UMK), skala usaha, daftar pekerja + riwayat upah multi-tahun, riwayat mutasi PPU/PBPU
- Wajib ada **hard negative**: badan usaha patuh yang terlihat mencurigakan (sektor padat karya yang sah di UMK, UMKM yang sah di bawah UMK)
- Penyisipan pelanggaran dilakukan *blind* oleh anggota yang tidak membangun model, supaya hasil evaluasi tidak melingkar
- Precision dilaporkan terpisah untuk kasus mudah dan kasus sulit

## Metrik target (semua pada data simulasi)
| Metrik | Target |
|---|---|
| Precision@top-10% | ≥ 70% |
| Lift vs pemilihan acak | ≈ 4,7× (baseline acak = prevalensi 15%) |
| Iuran terselamatkan per 100 pemeriksaan | dihitung kalkulator, dibandingkan dengan pemilihan acak |
| Waktu menyusun daftar target | dari hitungan hari menjadi menit |
| Salah tandai UMKM | ≤ 5% |

## Etika & bias
- UU PDP: analisis agregat per badan usaha, NIK dipseudonimisasi
- Usaha mikro/kecil dikecualikan dari upah minimum (PP 36/2021), jadi aturan deteksi dibedakan per skala usaha
- Skor diberi tingkat keyakinan. Wilayah dengan data sedikit mendapat keyakinan rendah dan tidak diprioritaskan.
- Human-in-the-loop: PayRay hanya mengurutkan prioritas, keputusan pemeriksaan dan sanksi tetap di petugas

## Rencana 8 minggu
| Minggu | Deliverable |
|---|---|
| 1–2 | Generator data sintetis + data benchmark publik |
| 3–4 | Tiga modul scan + skor gabungan + reason code |
| 5–6 | Dashboard, lembar hasil scan, kalkulator estimasi |
| 7 | Laporan akurasi + uji bias per skala usaha |
| 8 | Video demo + proposal final |

Fase lanjut: pilot di 1 Kantor Cabang dengan data riil berizin (±3 bulan), integrasi BPJS TK & OSS (±6 bulan), lalu skala nasional.

## Tim: Plan with Us
- Rachdian Habi Yahya: Ketua Tim · Data Scientist (pemodelan, evaluasi, uji bias). Mahasiswa S2 Digital Business Strategy, Telkom University. linkedin.com/in/rachdiaaan. Kontak tim: rachdiaaan@gmail.com
- Rifqi Sigwan Nugraha: Lead Engineer, Backend & AI. Lulusan IT Telkom University, co-founder Plus The Site. Skill: Python, FastAPI, PostgreSQL, multi-agent AI.
- Muhammad Al Ghani: Product Manager (kebutuhan petugas, alur kerja, desain dashboard, proposal & demo). UI/UX Designer di Torch.id. linkedin.com/in/muhammad-al-ghani
- Tidak ada Domain Expert di tim, jadi validasi aturan lewat konsultasi pakar HR-payroll/jaminan sosial bila memungkinkan.

## Status pitch deck & to-do revisi
Desain: tema rontgen gelap + aksen hijau limau, font Montserrat + Source Sans.

Revisi dari review:
- [ ] Slide 7: ganti alasan "upah tidak naik 3 tahun" karena bertentangan dengan "92% tepat di UMK". Ganti dengan "kenaikan upah selalu persis = kenaikan UMK". Masukkan juga pekerja yang pindah ke PBPU ke dalam estimasi Rp.
- [ ] Slide 2: lunakkan klaim "proaktif ke semua, bukan sampel". Ganti pembeda jadi: alasan yang bisa dibaca + estimasi dalam rupiah + perlindungan UMKM.
- [ ] Slide 6: tandai "pekerja masih aktif" sebagai fase lanjut
- [ ] Slide 8: tambah plafon upah di rumus kalkulator, dan 1–2 kalimat "kenapa AI, bukan aturan saja"
- [ ] Slide 10: hapus penanda "Saat ini: Ide"
- [ ] Slide 13: isi lift ≈ 4,7× dan salah tandai UMKM ≤ 5%
  - Bukti awal (data sintetis seed 42, model GBM cepat berlabel, BELUM blind, belum mesin final): precision@10% 83,8%, lift 5,6×, salah tandai UMKM 2,0%, top-100 menangkap iuran Rp7,79 M/thn vs Rp0,67 M acak (11,7×)
- [ ] Slide 4: angka "285 jt+ per 1 Juni 2026" tidak konsisten dengan portal resmi (282,8 jt per 30 Sep 2026). Pilih satu dan cantumkan tanggal + sumber
- [ ] Slide 9: tambah baris "Kepesertaan per segmen · Portal Data BPJS Kesehatan · Publik (sudah diambil)". Benchmark upah BPS di generator masih simulasi, jadi perlu ambil data BPS asli
- [ ] Slide 15: tambah footer yang konsisten dengan slide lain
- [ ] Tambah 3 slide: Desain validasi data sintetis · Hasil & demo (screenshot asli) · Alur kerja petugas

Placeholder yang masih kosong:
- Slide 4: estimasi Rp iuran PPU tak tertagih + jumlah badan usaha, **wajib dengan sumber resmi** (laporan BPJS / BPK)
  - Sudah ada (resmi, Portal Data BPJS Kesehatan, rekap 30 Sep 2026): **PPU–Badan Usaha 47.024.587 peserta (16,6% dari 282,8 juta)**, PBPU 32.040.621. Lihat `data_publik/bpjs_portal/RINGKASAN.md`.
  - Masih kurang: jumlah badan usaha terdaftar dan nilai iuran/tunggakan PPU. Portal tidak menyediakan, jadi ambil dari Laporan Pengelolaan Program / LHP BPK.
- Slide 10: link demo, video, repo

Cek regulasi sebelum submit: tarif & plafon iuran PPU terbaru, pengecualian upah minimum UMKM (PP 36/2021).

## Bukti untuk proposal
Semua angka siap pakai per slide, beserta sumber dan status verifikasinya, ada di `docs/BUKTI_PROPOSAL.md`. Temuan kunci:
- BPK IHPS II 2025: pendapatan iuran PPU BU & PN Rp31,61 T "tidak dapat diyakini kebenarannya", karena tidak didukung data memadai. Ini BUKAN angka kebocoran; jangan dibingkai begitu. PDF IHPS masih perlu dicek.
- Tulungagung (ANTARA, Jun 2026): baru 416 dari 1.092 badan usaha terdata yang mendaftarkan pekerjanya.
- Upah BPS Sakernas Agustus 2025 per lapangan usaha: `data_publik/bps/` (sekunder via CNBC, perlu dicocokkan ke bps.go.id).

## Status
- [x] Pitch deck revisi 20 slide: `docs/deck/PayRay_Healthkathon2026_revisi.pptx` + `.pdf` (generator: `docs/deck/build_deck.js`, font Montserrat + Source Sans 3)
- [x] Generator data sintetis (`generator/`, lihat README.md): dunia jujur → injeksi blind → CSV publik/referensi/label + laporan validasi. Loader PostgreSQL di `scripts/load_postgres.py`.
- [x] Scrape Portal Data BPJS Kesehatan (`scripts/scrape_bpjs_portal.py` → `data_publik/bpjs_portal/`): kepesertaan per segmen, faskes, 16 artikel, 75 dataset Statistik JKN 2014–2018 (XLSX → CSV + kamus).
- [ ] Penyisipan final oleh anggota non-model dengan `--inject-seed` rahasia (data di `data/` saat ini bukan blind)
- [x] Minggu 3–4: mesin scan `engine/` (7 aturan transparan dalam 3 modul + Isolation Forest + skor gabungan + keyakinan + reason code + estimasi Rp + simulasi umpan balik). Setelah kalibrasi upah ke BPS (ρ = 0,90) dan regenerasi data: holdout 68,4% / lift 4,56× / salah tandai UMKM 2,7%; dev 69,4% / 4,63× / 2,5%. Mesin tidak disetel ulang setelah regenerasi.
  - Kelemahan: recall potong_sebagian ±20%, daftar_sebagian ±35%; kalkulator Rp berkorelasi 0,34; salah tandai menengah/besar 6–7% (padat karya sah).
  - Contoh slide 7: `hasil/lembar_scan/BU04224.md` (PT Cahaya Mandiri, skor 98, estimasi Rp212 jt vs kerugian sebenarnya Rp215 jt).
- [x] Dashboard HTML statis `dashboard/` (antrean + lembar hasil scan + label umpan balik ke CSV). Build: `python dashboard/build_dashboard.py`. Tangkapan layar ada di deck slide 12.
- [ ] Berikutnya: API FastAPI + PostgreSQL di belakang dashboard; perbaiki kalkulator Rp (korelasi 0,30–0,36); video demo.
- Repo: https://github.com/rachdiaan/healthkathon-bpjs (PUBLIK; data/, hasil/, label tidak di-commit)
- Demo (GitHub Pages, branch main / root): https://rachdiaan.github.io/healthkathon-bpjs/ → redirect ke `dashboard/`. Sudah diisi di slide 13; tinggal video demo.
- [x] Lapisan ML (`ml/`): HistGB monoton dari 750 hasil pemeriksaan (IPW) + stacking + isotonic + CQR Rp + 17 data quality checks. Holdout: P@10% 82,2% (rules 68,4%), dua metode sepakat 95,1%, ECE 0,035, coverage Rp 84%. Model diekspor ke JSON dan berjalan di browser (dashboard tab Validasi model / Kualitas data / Metodologi).

## Guardrail agent (PRD §20, GR-6 sampai GR-13)

- [GR-6] Agent hanya mengerjakan scope task yang diberikan. Perubahan di luar file/FR task → stop dan laporkan → enforced by review PR
- [GR-7] Agent tidak boleh menambah dependency yang tidak ada di §18 → enforced by review PR + diff `requirements.txt` di CI (gagal bila berubah tanpa label `deps-approved`)
- [GR-8] Agent tidak boleh meng-commit secret (`.env`, `PAYRAY_NIK_KEY`, seed blind, password) dan hanya mengedit `.env.example` → enforced by gitleaks + `.gitignore`
- [GR-9] Agent tidak boleh menonaktifkan, men-skip, atau melonggarkan tes (`skip`, `xfail`, menurunkan ambang) → enforced by CI grep `pytest.mark.skip|xfail` + review
- [GR-10] Agent tidak boleh menjalankan migrasi destruktif (`DROP`, `TRUNCATE`, `DELETE` tanpa WHERE, ubah tipe kolom) atau menghapus data kecuali task menyebutnya eksplisit → enforced by CI grep di `db/migrations/` + review
- [GR-11] Agent tidak boleh membaca, menjalankan, atau me-retune apa pun memakai data `holdout`/`blind` di luar `scripts/eval_blind.py` → enforced by review + `ml/FROZEN.txt` check di CI (hash artefak harus cocok setelah Fase 3 dibekukan)
- [GR-12] Bila keputusan yang dibutuhkan tidak ada di dokumen ini, agent berhenti dengan status `blocked` dan menulis pertanyaannya di PR → enforced by review
- [GR-13] Tes tidak pernah jalan terhadap DB selain `*_test` → enforced by guard di `tests/conftest.py`

## Konvensi branch & merge

- `main` terproteksi. Kerja di branch `feat/<task-id>-<slug>` (mis. `feat/t3-migrations`).
- PR wajib CI hijau + 1 review anggota tim lain.
- Squash merge ke `main`.
