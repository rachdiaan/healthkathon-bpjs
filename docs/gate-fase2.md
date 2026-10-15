# Gate Fase 2 (t28) · 2026-10-14

Semua cek lokal: `pytest` 95 passed (DB `payray_test`), ruff bersih, mypy 0 error (40 file), bandit tanpa temuan medium/high, `pip-audit` tanpa vulnerability, grep BR-1/GR-9/GR-10/GR-14 = 0.

| Exit criteria | Status | Bukti |
|---|---|---|
| EC-2.1 Alur B dan C end-to-end di production | Sebagian | Lulus lokal di browser dengan akun uji (`docs/ui-checklist.md` t19, t24). Production belum ada (t13 terblokir) |
| EC-2.2 SEC-8, SEC-9, SEC-12 | Lulus | `tests/test_static.py`, `tests/test_inspections.py::test_mass_assignment_rejected`, `tests/test_batches.py` (paralel 202+409, officer 403) |
| EC-2.3 BUG-1, 3, 6, 7, 10, 11 | Lulus | `tests/test_inspections.py` (BUG-1, 3, 10), `tests/test_batches.py` (BUG-6), `tests/test_static.py` + uji browser (BUG-7), `tests/test_metrics.py` (BUG-11) |
| EC-2.4 Pages statis dari batch published + banner; transfer ≤ 2 MB | Sebagian | Build + banner lulus lokal (server statis tanpa API), transfer 199 KB gzip. Deploy Pages menunggu secret DB production |
| EC-2.5 `backup.yml` sukses ≥ 1 kali | Belum | Workflow siap; butuh secret `BACKUP_DATABASE_URL` |
| EC-2.6 Checklist §12 Form Inspeksi, Riwayat, Dasbor Supervisor, Banner | Lulus | `docs/ui-checklist.md` |
| EC-2.7 KILL-3 (5 warm-up `/health` live) | Belum | Butuh URL Render |
| Audit dependensi + secret scan | Lulus | `pip-audit` 0; gitleaks hijau di PR fork #1 (commit lanjutan belum di-push) |

## Go/No-Go

KILL-3 belum bisa dicek tanpa deploy. KILL-6 belum jatuh tempo (tanggal demo day belum diketahui). Pembangunan Fase 3 dilanjutkan atas instruksi user; KILL-1, KILL-2, KILL-3 wajib dicek sebelum demo dan hasilnya ditulis di `docs/gate-fase1.md` dan file ini.
