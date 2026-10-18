# PayRay Design System: MASTER

> **Revisi v3 (2026-10-17): gaya konsol Meridian menggantikan "dark x-ray".** Acuan visual utama sekarang konsol Meridian: netral monokrom (terang + gelap, toggle di topbar), aksen amber `--sa` dan hijau `--gn`, kartu radius 20px, rail ikon kiri (bar bawah di < 1000px), font Inter (self-hosted, variable). Pola inti: badge kepastian angka (● Data batch, ◐ Hasil hitungan, ○ Perkiraan) dan drawer "asal angka" (berdasarkan apa, cara menghitung, kapan bisa meleset, yang boleh diputuskan). Token aktif ada di `web/tokens.css`; komponen di `web/ui.js`. Bagian di bawah ini (token v2) hanya arsip; prinsip produk "mengurutkan, bukan menuduh" tetap berlaku. Batasan teknis tetap: tanpa `innerHTML` (GR-14), tanpa atribut `style` (CSP `style-src 'self'`, pakai CSSOM lewat `h(..., { style: {...} })`).

Acuan tunggal UI PayRay v2 (PRD §12). Nilai token di sini identik dengan `plankit/tokens.json` dan `web/tokens.css`. Ubah token hanya lewat file ini, lalu salin ke `web/tokens.css`.

## Kategori & arah

Tool operasional internal pemerintahan untuk triage/worklist. Gaya "dark x-ray": latar gelap kebiruan seperti film rontgen, satu aksen lime untuk sinyal penting, tipografi tegas, data padat tapi rapi. Prinsip produk: **mengurutkan, bukan menuduh.** Tidak ada warna "bahaya" untuk melabeli BU.

## Dial

| Dial | Nilai | Artinya |
|---|---|---|
| DESIGN_VARIANCE | 3 | Konsisten dan bisa ditebak. Alat kerja, bukan landing page. |
| MOTION_INTENSITY | 2 | Transisi fokus/hover ≤ 150 ms dan skeleton saja. |
| VISUAL_DENSITY | 7 | 10 baris antrean muat tanpa scroll di 1440 px. |

## Token

| Token | Nilai |
|---|---|
| `--color-bg` | `#0B0F14` |
| `--color-surface` | `#141B23` |
| `--color-text` | `#E8EEF2` |
| `--color-muted` | `#9AA7B2` |
| `--color-primary` | `#C6F432` |
| `--color-on-primary` | `#0B0F14` |
| `--color-border` | `#27323D` |
| `--color-warning` | `#F2B84B` |
| `--color-danger` | `#FF7A6B` |
| `--color-info` | `#6CC9E8` |
| `--font-heading` | `Montserrat` |
| `--font-body` | `Source Sans 3` |
| `--text-sm` | `14px` |
| `--text-base` | `16px` |
| `--text-lg` | `20px` |
| `--text-xl` | `28px` |
| `--text-display` | `40px` |
| `--weight-regular` | `400` |
| `--weight-bold` | `700` |
| `--leading-tight` | `1.2` |
| `--leading-normal` | `1.5` |
| `--space-xs` | `4px` |
| `--space-sm` | `8px` |
| `--space-md` | `16px` |
| `--space-lg` | `24px` |
| `--space-xl` | `32px` |
| `--space-2xl` | `48px` |
| `--radius-sm` | `4px` |
| `--radius-md` | `8px` |
| `--radius-lg` | `16px` |

Aturan pemakaian:
- `--color-primary` (lime) hanya untuk aksi primer, fokus, dan bar skor. Tidak untuk glow atau dekorasi.
- `--color-warning`, `--color-danger`, `--color-info` hanya untuk banner mode statis, error form, dan badge UMKM. Tidak pernah untuk melabeli BU berperingkat tinggi.
- Spasi kelipatan 4. Radius 4–8 untuk elemen kerja, 16 hanya untuk kartu metrik dan drawer.
- Font self-host di `web/fonts/` (subset latin, woff2, OFL): Montserrat 700 untuk heading dan angka besar, Source Sans 3 400/700 untuk body dan tabel.

## Kontras (WCAG 2.x, dihitung dari token)

| Pasangan | Warna | Rasio | Lulus ≥ 4.5:1 |
|---|---|---|---|
| text / bg | #E8EEF2 / #0B0F14 | 16.42:1 | ya |
| text / surface | #E8EEF2 / #141B23 | 14.82:1 | ya |
| muted / bg | #9AA7B2 / #0B0F14 | 7.82:1 | ya |
| muted / surface | #9AA7B2 / #141B23 | 7.06:1 | ya |
| onPrimary / primary | #0B0F14 / #C6F432 | 15.00:1 | ya |
| primary / surface (teks chip skor) | #C6F432 / #141B23 | 13.53:1 | ya |
| warning / surface (teks chip) | #F2B84B / #141B23 | 9.69:1 | ya |
| danger / surface (error form) | #FF7A6B / #141B23 | 6.81:1 | ya |
| info / surface (badge UMKM) | #6CC9E8 / #141B23 | 9.22:1 | ya |
| onPrimary / warning (banner statis) | #0B0F14 / #F2B84B | 10.74:1 | ya |

## Layout 6 layar

- **Login:** kartu tengah 400 px. Logo PayRay, field username + password, tombol primary "Masuk", footnote "Data sintetis, Healthkathon 2026".
- **Antrean:** top bar (logo, periode batch, waktu publikasi WIB, chip mode `Live`/`Statis`, menu user). Tabel full-width: Rank | BU & sektor | Skor (bar + angka) | Confidence | Alasan utama (≤ 2 chip) | Rp indikatif | Status. Tombol "10 berikutnya" di bawah. ≤ 768 px: daftar kartu, urutan field sama.
- **Scan Sheet:** ≥ 1024 px dua kolom. Kiri 8/12: header BU (rank, skor, confidence, rentang Rp + "indikatif, bukan tagihan", badge UMKM + penjelasan), lalu reason code (kalimat + bukti angka + mini-bar SVG). Kanan 4/12: checklist per reason, tombol "Catat hasil inspeksi", tabel pekerja ter-flag (token 8 karakter). < 1024 px satu kolom. Copy tetap: "Prioritas pemeriksaan, bukan tuduhan."
- **Form Inspeksi:** drawer kanan ≥ 1024 px, halaman penuh < 1024 px. Field vertikal, error di bawah field, Simpan + Batal.
- **Riwayat Saya:** Tanggal | BU | Rank saat dipilih | Status | Aksi (Koreksi bila ≤ 7 hari), toggle "Tampilkan koreksi".
- **Dasbor Supervisor:** 4 kartu metrik (Hit rate, Baseline acak, Lift, Coverage top-10) dengan `n` dan "Data belum cukup (n < 10)". Tab Batch dan Audit Log.
- **Banner mode statis:** strip penuh di atas top bar, latar `--color-warning`, teks `--color-on-primary`.

## Anti-pattern (dilarang)

- Kata "pelanggar", "curang", "fraud" untuk BU. Pakai "prioritas pemeriksaan" dan "indikasi".
- Ikon sirene/peringatan merah untuk BU berperingkat tinggi.
- Gauge/speedometer, 3D, gambar x-ray dekoratif di belakang teks.
- Angka Rp tunggal tanpa rentang dan label indikatif, atau total Rp agregat.
- Confidence rendah atau badge UMKM yang hanya ada di tooltip.
- Status yang dibedakan hanya dengan warna, tanpa teks/ikon.
- Glow lime, gradient dekoratif, kartu bertumpuk bayangan tebal.
- Animasi auto-play, carousel, modal bertumpuk.
- Emoji sebagai ikon. Icon font.

## Pre-delivery checklist (wajib per layar)

- [ ] Ikon SVG inline (tanpa emoji, tanpa icon font)
- [ ] Kontras teks ≥ 4.5:1 (text/bg, muted/bg, onPrimary/primary, teks di chip)
- [ ] Fokus keyboard terlihat (outline 2 px `primary`, offset 2 px) di semua elemen interaktif; seluruh alur A–C bisa dilakukan dengan keyboard
- [ ] `prefers-reduced-motion: reduce` mematikan semua transisi
- [ ] Tidak ada label atau chip terpotong (reason code panjang di-wrap, bukan ellipsis tanpa title)
- [ ] Responsif di 375, 768, 1024, 1440 px tanpa scroll horizontal (kecuali tabel audit log di 375 px, dalam scroll container berlabel)
- [ ] Form punya `<label>` terhubung, error diumumkan via `aria-live="polite"`
