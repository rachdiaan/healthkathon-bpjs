# Gate Fase 3 (t33) · 2026-10-14

Cek lokal: `pytest` 101 passed, ruff bersih, mypy 0 error (45 file), `pip-audit` 0 vulnerability, `sha256sum -c` artefak = `ml/FROZEN.txt`.

| Exit criteria | Status | Bukti |
|---|---|---|
| EC-3.1 `data/SOURCES.md` memuat URL bps.go.id, tanggal akses, rujukan batas upah + PP 36/2021, status verifikasi | Sebagian | File ada; semua item berstatus "belum diverifikasi". Angka tabel bps.go.id belum diunduh (ditunda user: "data diurus nanti") |
| EC-3.2 `ml/FROZEN.txt` di-commit sebelum file blind dibuat | Siap | Commit 7d87c4a (2026-10-14 10:09 WIB). Belum ada data blind; bukti timestamp lengkap setelah PM menginjeksi |
| EC-3.3 `docs/eval-blind.md` dari satu kali run | Belum | `scripts/eval_blind.py` siap (menolak run kedua, menolak tanpa blind, cek model_version = FROZEN). Menunggu injeksi PM + rescore + publish |
| EC-3.4 Paritas BUG-8 ke referensi terbaru + GR-5 | Lulus | `ml/reference_scores.json` diregenerasi (identik), `tests/test_scoring.py`; GR-5 lulus untuk 5.000 BU |
| EC-3.5 KILL-4 dan KILL-5 dicek | Belum | Dicek otomatis oleh `eval_blind.py`. Validation (bukan klaim): lift 5,57×, Spearman 0,595 |
| Audit dependensi + secret scan | Lulus | `pip-audit` 0 (layanan PyPI); gitleaks menunggu push berikutnya |

## Urutan sisa (oleh orang, bukan agent)

1. PM: `PAYRAY_BLIND_SEED=… PAYRAY_BLIND_INJECT_SEED=… python scripts/inject_blind.py` (seed di password manager PM).
2. Lead: rescore + publish batch kedua cabang lewat Dasbor Supervisor (model = FROZEN).
3. Lead/DS: `python scripts/eval_blind.py` sekali. Bila KILL-5 terpicu: `PAYRAY_RP_MODE=band` di Render, catat di README.
4. Lead: trigger `deploy-pages`.

## Go/No-Go

Belum bisa diputuskan: KILL-4/KILL-5 menunggu satu kali run blind. Tidak ada perubahan model yang boleh dilakukan setelah injeksi (BR-20, GR-11).
