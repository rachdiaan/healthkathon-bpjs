# AGENTS.md: PayRay v2

Aturan untuk coding agent di repo ini. Rencana lengkap: `plankit/PRD.md`, daftar task: `plankit/TASKS.md`.

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
