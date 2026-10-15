# Pre-delivery checklist UI (PRD §12)

Dicek di browser pane lokal (Chromium) dengan data dev 5.000 BU. Sumber kebenaran desain: `design-system/payray/MASTER.md`.

## Login + Antrean (t12) · 2026-10-14

- [x] Ikon SVG inline (`web/dom.js` `icon()`), tanpa emoji, tanpa icon font
- [x] Kontras teks ≥ 4.5:1 (semua pasangan token ≥ 6,8:1, lihat MASTER.md)
- [x] Fokus keyboard terlihat (`:focus-visible` outline 2 px primary, offset 2 px). Login: Tab → username → password → Masuk, Enter mengirim. Antrean: nama BU berupa link, Enter membuka Scan Sheet; "10 berikutnya" dan "Keluar" berupa button
- [x] `prefers-reduced-motion: reduce` mematikan semua transisi (`web/base.css`)
- [x] Tidak ada label/chip terpotong: 0 chip overflow di 375 px. Alasan di tabel ≥ 769 px satu baris dengan elipsis + `title` berisi teks lengkap; di ≤ 768 px wrap penuh
- [x] Responsif tanpa scroll horizontal: 375 (scrollWidth 375), 768 (753 = client), 1024 (1009 = client), 1440 (1425 = client). 10 baris muat tanpa scroll di 1440×900 (baris ke-10 berakhir di y = 821)
- [x] Form login: `<label for>` terhubung, error diumumkan lewat `aria-live="polite"`
- [x] SEC-4: nama BU `<img src=x onerror=alert(1)>` tampil sebagai teks literal, 0 elemen `img` terbentuk

## Scan Sheet (t15) · 2026-10-14

- [x] Ikon SVG inline (panah kembali, perisai UMKM, clipboard, peringatan); mini-bar skor dan kontribusi berupa SVG inline dengan `aria-label`
- [x] Kontras: semua teks memakai token yang lulus ≥ 4.5:1; badge rank `onPrimary/primary` 15:1
- [x] Fokus keyboard: judul BU menerima fokus saat terbuka; tombol "Kembali ke antrean" + `Esc`; checklist berupa checkbox berlabel; tabel pekerja dalam region scroll yang bisa difokus
- [x] `prefers-reduced-motion` dari `base.css` berlaku
- [x] Tidak ada teks terpotong: alasan wrap penuh, rentang Rp dikunci per nilai (`nowrap`) sehingga tidak patah di tengah angka; 0 elemen overflow di 375 px
- [x] Responsif: 1024 px dua kolom (619 / 310 px), 768 dan 375 px satu kolom, scrollWidth = clientWidth di semua lebar
- [x] Copy tetap "Prioritas pemeriksaan, bukan tuduhan."; badge UMKM selalu tampil bersama penjelasan "tidak mengubah peringkat, pendekatan pembinaan lebih dulu" (tidak hanya di tooltip)
- [x] Alur A: klik rank di antrean membuka Scan Sheet BU itu; `Esc` kembali dengan scroll yang sama (y = 1200 → 1200) dan fokus di baris BU yang tadi dibuka

## Form Inspeksi + Riwayat Saya (t19) · 2026-10-14

- [x] Ikon SVG inline (check di status, info di notice)
- [x] Kontras: token yang sama; error form `--color-danger` di surface 6,8:1
- [x] Keyboard: drawer `role="dialog" aria-modal`, fokus pertama di tanggal, Tab terkunci di dalam drawer, `Esc` menutup drawer tanpa meninggalkan Scan Sheet, fokus kembali ke tombol pemicu
- [x] `prefers-reduced-motion` dari `base.css`
- [x] Tidak ada label terpotong; label outcome/jenis temuan wrap
- [x] Responsif: drawer 480 px menempel kanan di 1440 px, layar penuh 375 px (scrollWidth = clientWidth); Riwayat jadi daftar bertumpuk ≤ 768 px
- [x] Semua input/textarea punya `<label for>`; radio/checkbox dalam `<fieldset><legend>`; error lokal dan 422 server tampil di bawah field (`aria-invalid`) dan diumumkan lewat `aria-live="polite"`
- [x] BUG-3 di UI: klik ganda + dblclick tombol Simpan = 1 POST (Idempotency-Key dibuat sekali per form)
- [x] BR-1: label outcome "Ditemukan indikasi ketidakpatuhan" (teks Alur B memuat "pelanggaran", yang gagal grep BR-1)

## Dasbor Supervisor (t24) · 2026-10-14

- [x] Ikon SVG inline (check, alert); badge status batch berisi teks, tidak hanya warna
- [x] Kontras token sama; badge memakai warna token di atas latar gelap (≥ 6,8:1)
- [x] Keyboard: tablist dengan `role="tab"`, `aria-selected`, roving tabindex, panah kiri/kanan berpindah tab; dialog publish memakai `<dialog>` modal, fokus awal di "Batal", `Esc` membatalkan
- [x] `prefers-reduced-motion` dari `base.css`; indikator "berjalan" statis (tanpa animasi)
- [x] Kartu n < 10 menampilkan "Data belum cukup (n < 10)" untuk Hit rate dan Lift, bukan angka
- [x] Responsif: 4 kartu di 1440 px (326 px), 2 kolom ≤ 1024 px, 1 kolom ≤ 768 px; tabel audit di 375 px dalam scroll container berlabel "Tabel audit log, geser ke samping" (satu-satunya scroll horizontal yang diizinkan); halaman scrollWidth = clientWidth
- [x] Semua filter/select punya `<label for>`
- [x] Alur C diuji: supervisor masuk langsung ke dasbor; batal di dialog = 0 POST, konfirmasi = 1 POST publish, batch lama jadi "Diarsipkan"; rescore ditolak 429 dengan pesan jelas; polling tiap 3 detik berhenti setelah "Siap"

## Banner + mode statis (t26) · 2026-10-14

- [x] Ikon SVG inline (info) di banner
- [x] Kontras banner: `onPrimary` di atas `warning` = 10,74:1
- [x] Keyboard: link "Buka versi live" bisa difokus; tombol "Ekspor CSV" dan "Hapus data lokal" (dengan konfirmasi) di Riwayat
- [x] `prefers-reduced-motion` dari `base.css`
- [x] Banner wrap di layar sempit, tidak terpotong
- [x] Responsif: strip penuh di atas top bar di semua lebar
- [x] Teks FR-31: "Mode statis: data batch <periode>, dibuat <generated_at WIB>. Form inspeksi tersimpan lokal, bukan ke server." + link live
- [x] Diuji di server file statis tanpa API: 0 request ke path `/api`; inspeksi tersimpan di localStorage dan menandai baris "Sudah diperiksa"; snapshot tanpa `generated_at` menampilkan pesan error, bukan antrean
