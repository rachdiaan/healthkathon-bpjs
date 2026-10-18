# Gate Fase 1 (t16) · 2026-10-14

| Exit criteria | Status | Bukti |
|---|---|---|
| EC-1.1 Migrasi bersih di DB kosong lokal, CI, Neon; versi di README | Lulus | Lokal + DB uji (`tests/conftest.py`), CI (job test + build di PR #1), Neon production (001–007 bersih). Versi di README |
| EC-1.2 CI 7 stage hijau di `main`; AGENTS.md/CLAUDE.md berisi GR-6..13 | Lulus | 7 stage hijau + GitGuardian lulus di PR rachdiaan/healthkathon-bpjs#1. Merge ke `main` (74bf815) tanpa review anggota lain atas keputusan pemilik akun; CI 7 job hijau di `main` (run 38675642911). GR ada di kedua file |
| EC-1.3 SEC-1..7, 10, 11, 13, 14 | Lulus | `tests/test_queue.py`, `test_scan_sheet.py`, `test_db_permissions.py`, `test_auth.py`, `test_middleware.py`, `test_seed.py`; SEC-4 UI di `docs/ui-checklist.md`; SEC-13 `pip-audit` 0 temuan; SEC-14 run 38495683953 gagal di gitleaks seperti diharapkan |
| EC-1.4 BUG-2, 4, 5, 8, 9 | Lulus | `tests/test_scoring.py`, `tests/test_queue.py` |
| EC-1.5 API live di Render + smoke production | Belum | t13 terblokir (akun Render/Neon). Smoke lulus 5/5 terhadap image Docker lokal |
| EC-1.6 Checklist §12 Login, Antrean, Scan Sheet | Lulus | `docs/ui-checklist.md` |
| EC-1.7 MASTER.md berisi token §12 | Lulus | `design-system/payray/MASTER.md` |
| EC-1.8 KILL-1 (3 penguji) dan KILL-2 (Neon) | Sebagian | **KILL-2 lulus di Neon** (`check_permissions.py` 4/4, juga untuk `payray_pages`). KILL-1: skrip siap di `docs/usability.md`, butuh 3 penguji manusia |
| Audit dependensi + secret scan | Lulus | `pip-audit`: tidak ada vulnerability; gitleaks hijau di PR #1 |

## Go/No-Go

KILL-1 dan KILL-2 belum bisa dicek (butuh 3 penguji dan akun Neon). Atas instruksi user ("lanjut build feature dulu"), pembangunan Fase 2 dilanjutkan dengan syarat: KILL-1 dan KILL-2 wajib dicek sebelum deploy production, dan hasilnya ditulis di sini.
