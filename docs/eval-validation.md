# Evaluasi model, set `validation`

Run 2026-10-14 setelah t30: rentang Rp dikalibrasi di set train (faktor 0,50–3,22), fitur relatif sektor-wilayah `rasio_upah_peer` (FR-36) dipakai sebagai bukti di alasan upah. Aturan tambahan berbasis fitur itu diuji di validation dan dibuang karena P@10% turun 1 BU dan recall potong_sebagian tidak berubah. PERINGATAN: model ML (ml/artefak/model_payray.json) dilatih dari hasil pemeriksaan di dunia sintetis yang sama (seed 42), jadi angka validation ini optimistis; angka yang boleh diklaim hanya hasil blind (docs/eval-blind.md).

Definisi metrik: PRD [BR-19]. N = BU di set, K = ceil(0,10 × N).

| Metrik | Nilai | Target PRD |
|---|---|---|
| P@10% | 88.3% (K = 103 dari N = 1022) | - |
| Lift vs prevalensi (15.8%) | 5.57× | ≥ 2× (KILL-4) |
| False flag padat karya patuh di top 10% | 0.9% (3 dari 332) | ≤ 3% (M-7) |
| Spearman Rp (rp_point vs kerugian sebenarnya, BU tidak patuh) | 0.595 | ≥ 0,50 (M-4) |
| Pearson Rp | 0.9049 | dilaporkan |
| Kerugian sebenarnya di dalam rentang rp_low–rp_high | 35.8% | dilaporkan |

## Recall per tipe (top 10%)

| Modus | n kasus | Recall |
|---|---|---|
| lapor_umk (under_reported_wage) | 29 | 62.1% |
| upah_beku (under_reported_wage) | 29 | 100.0% |
| potong_sebagian (potong_sebagian) | 31 | 25.8% |
| daftar_sebagian (partial_registration) | 78 | 56.4% |
| pindah_pbpu (ppu_to_pbpu_shift) | 24 | 79.2% |

Target M-5/M-6: recall pemotongan upah parsial ≥ 35%, pendaftaran parsial ≥ 50%. Target, bukan klaim.

```json
{
 "n": 1022,
 "k": 103,
 "prevalensi": 0.1585,
 "p_at_10": 0.8835,
 "lift": 5.57,
 "recall": {
  "lapor_umk (under_reported_wage)": {
   "n": 29,
   "recall_top10": 0.6207
  },
  "upah_beku (under_reported_wage)": {
   "n": 29,
   "recall_top10": 1.0
  },
  "potong_sebagian (potong_sebagian)": {
   "n": 31,
   "recall_top10": 0.2581
  },
  "daftar_sebagian (partial_registration)": {
   "n": 78,
   "recall_top10": 0.5641
  },
  "pindah_pbpu (ppu_to_pbpu_shift)": {
   "n": 24,
   "recall_top10": 0.7917
  }
 },
 "false_flag_padat_karya": {
  "n_patuh_padat_karya": 332,
  "di_top10": 3,
  "rate": 0.009
 },
 "rp": {
  "n_noncompliant": 162,
  "spearman": 0.595,
  "pearson": 0.9049,
  "coverage_rentang": 0.358
 }
}
```
