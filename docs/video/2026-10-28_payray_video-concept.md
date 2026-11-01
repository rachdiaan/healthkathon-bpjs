# PayRay: Konsep Video Branding Motion (50 detik)

Draft konsep sebelum produksi. Dibangun di Remotion (`F:\PlusVideo`, Remotion 4.0.539), template baru `PayRayPromo`.

## 1. Ringkasan

| Item | Keputusan |
|---|---|
| Durasi | 50 detik, 30 fps = 1.500 frame |
| Format utama | 1920x1080 (16:9) untuk pitch, YouTube, layar juri. Varian 9:16 menyusul setelah master disetujui |
| Bahasa | Indonesia, istilah teknis tetap (precision, Isolation Forest) |
| Penonton | Juri Healthkathon 2026, tim BPJS Kesehatan, pengunjung demo |
| Tujuan | Dalam 50 detik penonton paham masalahnya, cara PayRay bekerja, buktinya, lalu membuka demo |
| Kalimat kunci | "Periksa yang tepat, lebih dulu." |

## 2. Konsep kreatif: "Satu sinar, satu tarikan kamera"

PayRay = Pay + X-Ray. Seluruh video dibangun dari satu elemen: **sinar scan** (garis horizontal turqoise dengan glow tipis). Sinar ini bukan dekorasi. Ia menjadi alat cerita:

- Saat sinar lewat di atas laporan upah, lapisan tersembunyi muncul (upah riil, pekerja tak terdaftar, mutasi ke PBPU).
- Saat pindah adegan, sinar menjadi wipe transisi.
- Di akhir, sinar runtuh menjadi garis bawah wordmark PayRay.

Kamera terasa seperti satu kali ambil (one-take): tidak ada potongan keras. Setiap adegan lahir dari adegan sebelumnya lewat morph, zoom-through, atau match cut. Ini membuat video 50 detik terasa utuh dan mahal tanpa butuh footage.

Nada: tenang, presisi, bisa dipercaya. Bukan "AI menangkap penipu". Pesan etisnya terlihat: PayRay **mengurutkan prioritas, bukan menuduh**.

## 3. Identitas visual

Diambil dari token produk yang sudah ada (`web/tokens.css` v3.1 mode gelap + deck), bukan warna baru.

| Peran | Warna | Sumber |
|---|---|---|
| Latar | `#0A1413` | tokens.css dark `--bg` |
| Permukaan kartu | `#111D1C` | `--sf` |
| Garis/border | `#22302F` | `--ln` |
| Teks utama | `#EEF5F4` | `--ink` |
| Teks sekunder | `#93A3A1` | `--mu` |
| Sinar scan, aksen utama | `#2FC0B4` (turqoise) | `--pb` |
| Sorotan skor, CTA | `#C9D93A` (hijau kuning) | `--sa` |
| Peringatan (hanya di adegan masalah) | `#F0A35E` | `--am` |

- Font: Montserrat 700 untuk judul dan angka besar, Inter untuk teks UI dan keterangan. File woff2 sudah ada di `healthkathon-bpjs/web/fonts/` (OFL).
- Tekstur: grid tipis 40px opacity 4%, noise film 3%, vignette. Kesan layar rontgen tanpa terlihat medis berlebihan.
- Logo: belum ada file logo. Wordmark "PayRay" dibuat tipografis (Montserrat 700) dengan sinar sebagai garis bawah. Bila tim punya logo, tinggal ganti.

## 4. Token gerak (dipakai konsisten di semua adegan)

| Token | Nilai | Dipakai untuk |
|---|---|---|
| `ease.out` | `Easing.bezier(0.16, 1, 0.3, 1)` | Teks dan elemen masuk |
| `ease.inOut` | `Easing.bezier(0.65, 0, 0.35, 1)` | Gerak kamera, morph |
| `ease.in` | `Easing.bezier(0.7, 0, 0.84, 0)` | Elemen keluar, tarikan sebelum zoom-through |
| `spring.ui` | `{ damping: 200 }` | Kartu UI, baris antrean (tanpa pantul) |
| `spring.pop` | `{ damping: 12, stiffness: 140 }` | Badge, tag, tombol CTA (pantul kecil) |
| Stagger teks | 3 frame per kata | Kinetic typography |
| Stagger baris | 4 frame per baris | Antrean, daftar alasan |
| Durasi masuk standar | 18 frame (0,6 s) | Hampir semua entrance |

Semua animasi lewat `useCurrentFrame()` + `interpolate()`/`spring()`. Tanpa CSS transition.

## 5. Storyboard dan timestamp

Total 10 adegan. Frame dihitung di 30 fps.

| # | Waktu | Frame | Adegan |
|---|---|---|---|
| 1 | 0:00–0:03 | 0–90 | Hook: sinar pertama |
| 2 | 0:03–0:08 | 90–240 | Rontgen pertama: masalah terungkap |
| 3 | 0:08–0:12,5 | 240–375 | Skala masalah |
| 4 | 0:12,5–0:16 | 372–486 | Brand reveal |
| 5a | 0:16–0:20 | 480–600 | Modul 01 Scan Upah |
| 5b | 0:20–0:24 | 600–720 | Modul 02 Scan Headcount |
| 5c | 0:24–0:28 | 720–840 | Modul 03 Scan Status |
| 6 | 0:28–0:31 | 840–930 | Mesin skor |
| 7 | 0:31–0:38 | 930–1140 | Produk: antrean dan lembar hasil scan |
| 8 | 0:38–0:43 | 1140–1290 | Bukti |
| 9 | 0:43–0:45,5 | 1290–1366 | Kepercayaan |
| 10 | 0:45,5–0:50 | 1362–1500 | CTA |

### Copy deck (sumber tunggal semua teks layar)

Bila deskripsi adegan di bawah berbeda, copy deck ini yang berlaku. Disunting dengan no-ai-slop (tanpa kontras biner, tanpa kalimat penutup "mendalam", angka konkret), ux-copy (CTA diawali kata kerja, istilah sama dengan UI `web/`), dan struktur konten pemasaran (hook, masalah, solusi, bukti, CTA). Angka contoh diambil dari `dashboard/index.html` (keluaran asli mesin, data sintetis), bukan dikarang.

| # | Elemen | Teks |
|---|---|---|
| 1 | Judul | Di laporan, semua pekerja dibayar persis UMK. |
| 1 | Kartu | Laporan upah · Januari · 8 baris "Rp3.500.000 = UMK" · label "Ilustrasi" |
| 2 | Tag 1–3 (urutan sesuai lintasan sinar) | Upah riil lebih tinggi · 2 pekerja dipindah ke PBPU · 3 pekerja tidak didaftarkan |
| 2 | Keterangan | Selisihnya adalah iuran JKN yang tidak pernah masuk. |
| 3 | Angka | 47.024.587 |
| 3 | Label + sumber | peserta PPU badan usaha · Portal Data BPJS Kesehatan, 30 Sep 2026 |
| 3 | Keterangan | Petugas tidak bisa memeriksa semuanya. Mereka perlu tahu harus mulai dari mana. |
| 4 | Kicker | Healthkathon 2026 · Detect Smarter, Protect JKN |
| 4 | Wordmark + tagline | PayRay · Rontgen kepatuhan pemberi kerja untuk JKN. |
| 5 | Judul bagian | Tiga modul scan untuk setiap badan usaha |
| 5a | Modul | 01 · Scan Upah: Upah menumpuk tepat di UMK, dan naiknya selalu sama dengan kenaikan UMK. (grafik berlabel "Ilustrasi") |
| 5b | Modul | 02 · Scan Headcount: Terdaftar 48 pekerja. Rencana tenaga kerja di OSS: 112. |
| 5c | Modul | 03 · Scan Status: 24 pekerja pindah dari PPU ke PBPU dalam 3 bulan, tanpa PHK. |
| 5b–c | Tag | PT Cahaya Mandiri · data sintetis |
| 6 | Dua aliran | 7 aturan transparan (Bunching di UMK · Kenaikan = kenaikan UMK · Upah beku · Di bawah UMK (usaha wajib) · Upah atas rendah vs sektor · Terdaftar vs rencana OSS · Klaster pindah ke PBPU, dari `engine/rules.py`) · Isolation Forest + model ML terkalibrasi: "Menangkap kombinasi anomali yang belum dirumuskan sebagai aturan." |
| 6 | Keterangan | Dua cara menilai, satu skor, lengkap dengan tingkat keyakinan. |
| 7 | Panel | Antrean pemeriksaan · Kota Medan · Diurutkan dari skor risiko tertinggi |
| 7 | Kolom | # · Badan usaha · Skor · Rp indikatif / thn |
| 7 | Baris | 1 PT Surya Agung 98,7 Rp18 jt · 2 PT Cahaya Mandiri 98,5 Rp212 jt · 3 PT Surya Mandiri 98,3 Rp240 jt · 4 PT Harapan Raya 98,1 Rp2,57 M · 5 PT Cahaya Sentosa 98,0 Rp54 jt |
| 7 | Lembar hasil scan | PT Cahaya Mandiri · Industri kulit & alas kaki · 49 pekerja dilaporkan · data sintetis · Skor 98,5 · Keyakinan: tinggi |
| 7 | Alasan | "Alasan, urut dari kontribusi terbesar": 1. 24 pekerja keluar PPU lalu terdaftar PBPU ≤30 hari, dalam 3 bulan, bukan PHK (46%) · 2. Terdaftar rata-rata 48 pekerja, rencana tenaga kerja di OSS 112 (43%) · 3. Kombinasi pola tidak biasa dibanding usaha seskala |
| 7 | Estimasi | Estimasi iuran tak tertagih / tahun: ± Rp212 jt · Kerugian sebenarnya di simulasi: Rp215 jt |
| 7 | Tombol + toast | Catat hasil inspeksi → Tersimpan · jadi label baru |
| 7 | Keterangan 1–3 | Antrean siap tiap periode. Petugas mulai dari skor tertinggi. · Setiap skor punya alasan yang bisa dibaca dan estimasi dalam rupiah. · Hasil pemeriksaan masuk kembali sebagai label baru untuk model. |
| 8 | Judul | Diuji pada data simulasi yang tidak dipakai saat penyetelan |
| 8 | Angka | 82,2%: badan usaha di 10% skor teratas memang melanggar · 5,5×: lebih tepat daripada memilih acak · 2,7%: UMKM patuh yang salah ditandai |
| 8 | Footnote | Data simulasi (holdout seed 2026). Uji blind final menyusul. |
| 9 | Judul | PayRay mengurutkan. Petugas memutuskan. |
| 9 | Chip | NIK dipseudonimisasi · Akses sesuai peran · Audit log tiap aksi · Aturan terpisah untuk UMKM |
| 10 | Lockup | PayRay · Periksa yang tepat, lebih dulu. |
| 10 | CTA | Coba demo PayRay → · payray.onrender.com |
| 10 | Kredit | Tim Plan with Us · Healthkathon 2026 |

Perubahan dari draft pertama:
- "Mengurutkan, bukan menuduh" diganti "PayRay mengurutkan. Petugas memutuskan." Pesannya sama, tapi menyebut siapa melakukan apa, tanpa pola kontras biner.
- "Tapi rontgen menunjukkan cerita lain" dibuang (klise). Tag temuan sudah bercerita sendiri; keterangannya diganti akibat konkret: iuran yang tidak masuk.
- Modul 02 dan 03 sekarang memakai angka asli PT Cahaya Mandiri, sehingga lembar hasil scan di adegan 7 adalah badan usaha yang sama. Penonton melihat satu kasus dari deteksi sampai keputusan.
- Skor ditulis 98,5 sesuai data (deck membulatkan ke 99, CLAUDE.md menulis 98). Antrean memakai urutan asli wilayah Kota Medan, di mana PT Cahaya Mandiri peringkat 2.
- Label tombol dan judul kolom memakai label UI asli ("Catat hasil inspeksi", "Rp indikatif", "Diurutkan dari skor risiko tertinggi").
- Angka 82,2% diterjemahkan ke bahasa awam: "badan usaha di 10% skor teratas memang melanggar".

### Adegan 1. Hook (0:00–0:03, f 0–90)

- f 0–12: layar gelap total, hanya noise film.
- f 12–36: sinar scan menggambar dari tengah ke kiri dan kanan (`scaleX` 0 → 1, `ease.out`), glow membesar lalu mengecil.
- f 30–60: teks "Laporan upah terlihat rapi." masuk per kata (stagger 3, `translateY` 24 → 0, blur 8 → 0).
- **Kamera:** push-in pelan dari `scale 1.00` ke `1.06` sepanjang adegan (`ease.inOut`).
- **SFX:** whoosh pendek di f 12.

### Adegan 2. Rontgen pertama (0:03–0:08, f 90–240)

- f 90–120: teks hook naik keluar. Dari bawah muncul kartu "Laporan Upah PT Contoh" berisi 8 baris pekerja, semua tertulis Rp 2.500.000 (UMK). Rapi dan seragam.
- f 120–200: sinar scan menyapu kartu dari atas ke bawah. Di bawah sinar, lapisan rontgen terungkap lewat clip-path yang mengikuti posisi sinar:
  - angka upah berganti ke upah riil (Rp 4,2 jt, Rp 5,8 jt, dan seterusnya) dengan warna turqoise
  - 3 baris "hantu" muncul (pekerja tidak didaftarkan), garis putus-putus
  - 2 baris bergeser ke kolom kanan berlabel PBPU
- f 170–230: tiga tag muncul dengan `spring.pop`, stagger 8 frame: "Upah dilaporkan = UMK", "Pekerja tidak didaftarkan", "Dipindah ke PBPU". Warna amber.
- Teks: "Tapi rontgen menunjukkan cerita lain."
- **Kamera:** dolly turun mengikuti sinar (`translateY` 0 → -120px) dengan kemiringan 3D (`rotateX` 10° → 4°, perspective 1600px). Rasanya seperti mesin scan bergerak di atas dokumen.
- **SFX:** dengung scan rendah selama sapuan, pop kecil per tag.

### Adegan 3. Skala masalah (0:08–0:12, f 240–360)

- **Morph:** kartu laporan mengecil menjadi satu ubin kecil (`scale` 1 → 0,04, `ease.inOut`). Bersamaan, ubin-ubin lain muncul di sekitarnya membentuk grid ribuan badan usaha (render 40x24 ubin, stagger dari tengah keluar berdasarkan jarak).
- f 280–340: penghitung angka naik ke "47.024.587" (Montserrat 700, `ease.out`), label "peserta PPU badan usaha". Sumber kecil di bawah: "Portal Data BPJS Kesehatan, 30 Sep 2026".
- f 320–355: "Petugas tidak bisa memeriksa semuanya." Ubin-ubin berkedip acak (sebagian kecil saja menyala amber), memperlihatkan bahwa pemilihan acak itu buta.
- **Kamera:** pull-back besar (zoom out `scale` 1,0 → 0,35 pada grid), sedikit rotasi `rotateZ` -2° → 0°.
- **SFX:** whoosh panjang pada pull-back.

### Adegan 4. Brand reveal (0:12–0:16, f 360–480)

- f 360–390: **zoom-through**: seluruh ubin tertarik ke titik tengah (gaya magnet, `ease.in`), menyatu menjadi satu titik terang.
- f 390–405: titik meledak menjadi sinar scan horizontal selebar layar (flash putih 4 frame, opacity maks 0,6).
- f 400–440: **morph wordmark:** "Pay" masuk dari kiri, "X-Ray" dari kanan. Huruf "X-" menyusut dan hilang (`scaleX` 1 → 0, opacity 1 → 0) sehingga dua kata menyatu jadi "PayRay". Sinar turun menjadi garis bawah wordmark.
- f 430–470: tagline "Rontgen kepatuhan pemberi kerja untuk JKN" masuk per kata. Kicker kecil di atas: "Healthkathon 2026 · Detect Smarter, Protect JKN".
- **Kamera:** diam total setelah flash (kontras dengan gerak sebelumnya, memberi napas pada logo), lalu drift halus `scale` 1,00 → 1,02.
- **SFX:** sting saat flash.

### Adegan 5. Tiga modul scan (0:16–0:28, f 480–840)

Struktur bersama: indikator modul di kiri atas (01 / 02 / 03, yang aktif bertambah terang dan garis progres mengisi). Visual data di tengah, satu kalimat keterangan di bawah. Satu set elemen grafis yang sama **dimorph** antar modul, bukan diganti.

**5a. Scan Upah (f 480–600)**
- Wordmark naik dan mengecil ke pojok kiri atas (jadi logo kecil yang menetap sampai adegan 9).
- Histogram distribusi upah 24 batang tumbuh dari bawah (stagger 2 frame, `spring.ui`).
- Garis vertikal UMK menyala turqoise. Satu batang tepat di garis UMK memanjang jauh melebihi yang lain (bunching), disorot hijau kuning.
- Label mini: "Bunching di UMK" dan "Kenaikan upah = kenaikan UMK, tidak pernah lebih" (grafik garis kecil, dua garis berimpit).
- **Kamera:** rack focus masuk (blur 12px → 0), orbit halus `rotateY` -6° → 0°.

**5b. Scan Headcount (f 600–720)**
- **Morph:** 24 batang histogram berkumpul dan menyusun ulang jadi 2 batang besar: "Didaftarkan 120" vs "Wajar untuk skala & sektor ini 340". Batang turqoise vs batang garis putus-putus.
- Ikon gedung kecil + label "NIB/OSS · KBLI".
- **Kamera:** truck (geser) ke kanan 80px mengikuti batang kedua yang lebih tinggi.

**5c. Scan Status (f 720–840)**
- **Morph:** dua batang pecah menjadi titik-titik (partikel pekerja), tersusun di kolom PPU.
- Satu klaster titik (sekitar 30%) mengalir bersamaan ke kolom PBPU dalam satu bulan, di sepanjang garis waktu yang bergerak. Jalur alirannya kurva Bezier.
- Label: "Klaster perpindahan PPU → PBPU dari satu pemberi kerja".
- **Kamera:** tilt turun mengikuti aliran, lalu pull-back sedikit untuk transisi.
- **SFX:** satu pop kecil per modul saat label muncul.

### Adegan 6. Mesin skor (0:28–0:31, f 840–930)

- Dua aliran masuk dari kiri dan kanan:
  - kiri: daftar 7 aturan transparan (centang muncul berurutan)
  - kanan: diagram pohon kecil "Isolation Forest + model ML terkalibrasi"
- **Morph:** kedua aliran menyatu ke tengah membentuk dial skor melingkar. Angka di dial menghitung 0 → 98, busur terisi hijau kuning.
- Teks: "Aturan transparan + AI = satu skor, lengkap dengan keyakinan."
- **Kamera:** push-in ke dial (`scale` 1 → 1,3), dial menjadi pintu ke adegan berikut.

### Adegan 7. Produk (0:31–0:38, f 930–1140)

Menampilkan UI PayRay versi motion (digambar ulang dalam React dengan token yang sama dengan `web/`, bukan screenshot).

- f 930–960: **morph** dial mengecil jadi chip skor "98", yang menempel ke baris peringkat #1.
- f 950–1010: antrean prioritas terbangun: 7 baris masuk dari bawah (stagger 4, `spring.ui`), tiap baris berisi peringkat, nama badan usaha (sintetis), bar skor, estimasi Rp. Judul panel: "Antrean pemeriksaan · Cabang 1".
- f 1010–1040: **kamera dolly** masuk ke baris #1, baris lain memudar dan blur.
- f 1030–1100: **morph:** baris #1 membesar (shared element) menjadi lembar hasil scan:
  - "PT Cahaya Mandiri (sintetis) · Skor 98 · Keyakinan tinggi"
  - 3 alasan muncul berurutan dengan centang: upah 92% pekerja tepat di UMK, kenaikan upah selalu sama dengan kenaikan UMK, satu alasan Scan Status (angka menyusul)
  - kartu estimasi "Rp212 jt / tahun potensi iuran tak tertagih" (penghitung naik)
- f 1090–1140: tombol "Catat hasil pemeriksaan" diklik oleh kursor (ripple), lalu panah melingkar kembali ke dial kecil: "Hasil pemeriksaan jadi label baru. Model makin tepat."
- **Kamera:** panel UI masuk dengan kemiringan 3D (`rotateY` -14° → -4°, `rotateX` 6° → 2°), lapisan parallax (bayangan, panel, chip) bergerak dengan kecepatan berbeda.
- **SFX:** klik kecil saat tombol ditekan, pop per alasan.

Catatan: teks dan angka adegan ini mengikuti copy deck (BU04224 dari `dashboard/index.html`). Baris yang di-zoom adalah peringkat 2, bukan 1, sesuai urutan asli.

### Adegan 8. Bukti (0:38–0:43, f 1140–1290)

- **Transisi:** sinar scan menyapu dari kiri ke kanan, menghapus UI dan membuka tiga kartu angka.
- Tiga angka besar menghitung naik, stagger 10 frame:
  - **82,2%** precision di 10% teratas
  - **5,5×** lebih tepat dibanding pemilihan acak (82,2% ÷ prevalensi 15%)
  - **2,7%** salah tandai UMKM patuh (target ≤ 5%)
- Footnote wajib, tetap terbaca: "Data simulasi, holdout seed 2026. Belum blind final."
- **Kamera:** diam, angka yang bergerak. Hanya parallax halus pada grid latar.
- **SFX:** tick halus selama hitungan, stamp kecil saat angka berhenti.

### Adegan 9. Kepercayaan (0:43–0:45, f 1290–1350)

- Kalimat besar: "Mengurutkan, bukan menuduh."
- Empat chip masuk berurutan (`spring.pop`): "NIK dipseudonimisasi", "Akses berbasis peran", "Audit log", "Perlindungan UMKM".
- Ikon siluet petugas kecil: "Keputusan tetap di petugas".
- **Kamera:** push-in pelan.

### Adegan 10. CTA (0:45–0:50, f 1350–1500)

- f 1350–1380: semua elemen tertarik ke tengah, logo kecil di pojok kembali ke tengah dan membesar (**morph** posisi logo).
- f 1370–1410: lockup akhir: wordmark PayRay + sinar garis bawah + tagline "Periksa yang tepat, lebih dulu."
- f 1400–1440: tombol CTA hijau kuning "Coba demo PayRay →" masuk dengan `spring.pop`, lalu bernapas (`scale` 1 → 1,03 → 1, satu siklus 40 frame).
- Di bawah tombol: `payray.onrender.com` (Inter, turqoise).
- Baris kredit kecil: "Tim Plan with Us · Healthkathon 2026".
- f 1440–1500: sinar scan terakhir lewat dari atas ke bawah, berhenti tepat di garis bawah wordmark, glow meredup. Hold 1 detik untuk thumbnail dan frame terakhir.
- **Kamera:** pull-back halus `scale` 1,08 → 1,00.
- **SFX:** sting penutup saat lockup.

## 6. Daftar gerak kamera

| Adegan | Gerak | Detail |
|---|---|---|
| 1 | Push-in | scale 1,00 → 1,06 |
| 2 | Dolly turun + tilt 3D | translateY 0 → -120, rotateX 10° → 4° |
| 3 | Pull-back besar | scale 1,0 → 0,35, rotateZ -2° → 0° |
| 4 | Zoom-through, lalu diam | titik pusat, flash, drift 1,00 → 1,02 |
| 5a | Rack focus + orbit | blur 12 → 0, rotateY -6° → 0° |
| 5b | Truck kanan | translateX 0 → -80 |
| 5c | Tilt turun + pull-back | mengikuti aliran titik |
| 6 | Push-in ke dial | scale 1 → 1,3 |
| 7 | Dolly ke baris #1 + panel 3D + parallax | rotateY -14° → -4° |
| 8 | Statis + parallax latar | angka yang bergerak |
| 9 | Push-in pelan | scale 1,00 → 1,04 |
| 10 | Pull-back halus | scale 1,08 → 1,00 |

Implementasi: satu komponen `<Camera>` yang membungkus "dunia" dan menerima keyframe `{frame, x, y, scale, rotateX, rotateY, rotateZ, blur}`, diinterpolasi dengan `ease.inOut`. Semua adegan berbagi kamera ini sehingga gerak terasa satu kali ambil.

## 7. Daftar morph dan transisi

| Dari | Ke | Teknik |
|---|---|---|
| Sinar | Garis pemisah hook | scaleX dari tengah |
| Lapisan laporan | Lapisan rontgen | clip-path mengikuti posisi sinar |
| Kartu laporan | Ubin grid | scale + posisi, grid tumbuh radial |
| Grid ubin | Satu titik | tarikan magnet ke pusat (`ease.in`) |
| Titik | Sinar | flash + scaleX |
| "Pay" + "X-Ray" | "PayRay" | huruf "X-" kolaps |
| Wordmark tengah | Logo pojok | posisi + scale, menetap |
| Histogram 24 batang | 2 batang headcount | interpolasi x, lebar, tinggi tiap rect |
| 2 batang | Partikel titik | batang dipecah jadi grid titik, lalu dilepas |
| 2 aliran (aturan + model) | Dial skor | konvergen ke pusat |
| Dial | Chip skor baris #1 | scale + posisi |
| Baris #1 | Lembar hasil scan | shared element: lebar, tinggi, radius, isi crossfade |
| UI | Kartu bukti | wipe sinar kiri ke kanan |
| Logo pojok | Lockup akhir | posisi + scale |

## 8. Inventaris motion (komponen yang akan dibuat)

- `ScanBeam`: sinar dengan glow, bisa horizontal/vertikal, posisi animasi, dipakai sebagai wipe
- `XRayReveal`: dua lapisan (laporan vs riil) dengan clip-path terikat ke posisi sinar
- `KineticText`: masuk per kata (translateY + blur + opacity), stagger bisa diatur
- `CountUp`: penghitung angka format Indonesia (titik ribuan, koma desimal, prefiks Rp)
- `TileGrid`: grid ubin dengan stagger radial dan tarikan magnet
- `Wordmark`: PayRay dengan morph "X-" dan sinar garis bawah
- `ModuleIndex`: indikator 01/02/03 dengan progres
- `MorphBars`: satu set rect yang diinterpolasi antar tata letak (histogram → headcount → partikel)
- `FlowDots`: partikel mengalir di jalur Bezier PPU → PBPU
- `ScoreDial`: busur SVG + angka
- `QueuePanel`, `ScanSheet`: UI produk dalam token PayRay
- `Cursor`: kursor dengan klik dan ripple
- `Chip`, `CTAButton`: `spring.pop` + napas
- `Backdrop`: grid, noise, vignette
- `Camera`: pembungkus dunia dengan keyframe

## 9. Audio

**Versi v4 (berlaku):** setiap penjelasan ditahan 1–1,5 detik lebih lama (14 jeda baca, total sekitar 20 detik), sehingga video menjadi sekitar 72,5 detik. Jeda dibuat dengan peta waktu global (`templates/PayRayPromo/timing.json` → `scripts/custom/payray_timing.py`): video melambat sampai 8% kecepatan lalu lanjut, jadi gerak kamera tetap hidup. SFX ikut bergeser otomatis, dan musik dibuat ulang di grid 120 BPM supaya lima hit (flash logo, produk, wipe bukti, CTA, outro plus.) tetap jatuh tepat di ketukan. Link CTA: `payray.onrender.com`.

**Versi v3 (dasar audio dan outro):** total 56 detik. Cerita tetap 50 detik, CTA ditahan 3 detik lebih lama (sampai frame 1585) supaya teks sempat terbaca, lalu ada outro 3 detik "Dibuat oleh plus. · plusthe.site" (frame 1585–1680). Sinar CTA menyusut jadi satu titik, lalu logo plus. digambar garis per garis dan terisi, mengikuti animasi logo di plusthe.site. Path SVG diambil dari situs itu, warna latar slate-950 `#020617`. Musik dan SFX disintesis sendiri lewat `F:\PlusVideo\scripts\custom\payray_audio.py`. Musiknya half-time sekitar 121 BPM: pad Am9–Fmaj7–Cmaj7–G6, bass berdenyut, motif bell FM, kick lembut, dan reverse swell sebelum setiap hit. Hit jatuh di frame 398, 932, 1140, 1362, dan 1585. Ada lebih dari 70 SFX interaksi: tick (baris, centang, tab), tap (tag, chip), ping (sorotan, angka terkunci), data (penghitung), klik mouse di tombol "Catat hasil inspeksi", chime sukses di "Tersimpan", chime di tombol CTA, air whoosh di setiap morph, boom di flash/wipe/CTA, dan sparkle di logo. Mix akhir: -15,9 LUFS, true peak -1,4 dBFS. Catatan di bawah ini adalah rencana awal.

- **SFX:** whoosh, pop, sting, stamp dari Kenney (CC0) dan whoosh sintetis yang sudah ada di `assets/brands/kale-cole/sfx/`. Tanpa kewajiban kredit.
- **Musik:** belum ada track yang cocok untuk brand teknologi. Yang tersedia di `assets/music/` ("Investigations", Kevin MacLeod) bernuansa detektif jenaka dan wajib kredit CC BY 4.0. Rekomendasi: tim memberikan satu track elektronik minimal bertempo sekitar 120 BPM berlisensi bebas royalti. Bila tidak ada, video dirender dengan SFX saja dulu, dan musik bisa ditambahkan tanpa mengubah animasi.
- **Voiceover:** tidak untuk versi 1. Teks layar sudah membawa seluruh cerita, dan video tetap jelas saat diputar tanpa suara (umum di media sosial dan ruang juri). VO bahasa Indonesia (edge-tts `id-ID-ArdiNeural`) bisa ditambahkan nanti di atas ketukan yang sama.

## 10. Klaim dan sumber yang tampil di layar

| Klaim | Sumber | Status |
|---|---|---|
| 47.024.587 peserta PPU badan usaha | Portal Data BPJS Kesehatan, 30 Sep 2026 | Primer |
| 82,2% precision@top-10% | Holdout seed 2026, lapisan gabungan | Data simulasi, wajib footnote |
| 5,5× vs acak | 82,2% ÷ 15% prevalensi | Turunan, data simulasi |
| 2,7% salah tandai UMKM | Holdout seed 2026 | Data simulasi |
| PT Cahaya Mandiri, skor 98,5, Rp212 jt, 3 alasan | `dashboard/index.html` (BU04224, keluaran mesin) | Sintetis, diberi label "data sintetis" |
| Antrean Kota Medan (5 baris) | `dashboard/index.html`, diurutkan dari `prio` | Sintetis |

Sengaja **tidak** dipakai: angka BPK Rp31,61 T (sumber sekunder, PDF IHPS belum dicek, dan mudah disalahbaca sebagai nilai kebocoran) serta klaim "dari hari ke menit" (target, belum diukur).

## 11. Rencana produksi

1. Template baru `templates/PayRayPromo/` di `F:\PlusVideo`: satu file per adegan + `shared/` untuk komponen di bagian 8, didaftarkan di `templates/Root.tsx`.
2. Font Montserrat 700 dan Inter disalin ke `assets/fonts/payray/` (folder `assets/brands/` read-only untuk agent; brand kit `payray` bisa dibuat tim nanti).
3. Bangun per adegan, cek tiap adegan lewat `npx remotion still` di frame kunci.
4. Render master: `node scripts/vid.mjs render-template --template PayRayPromo` → `output/payray/2026-10-28_payray_promo-50s.mp4` (H.264, CRF 18).
5. Setelah master disetujui: varian 9:16 dan versi dengan musik/VO.
6. Final disalin ke `OUTPUTS/healthkathon/`.
