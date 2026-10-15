// Referensi paritas BUG-8: menjalankan evaluator browser (disalin apa adanya dari
// dashboard/template.html: sigmoid, rawPredict, interp, predict) atas input yang diekspor Python.
// node ml/reference_eval.mjs <inputs.json> <ml/reference_scores.json>
import { readFileSync, writeFileSync } from "node:fs";

const [, , inPath, outPath] = process.argv;
// File model berisi literal NaN (bukan JSON standar); browser memuatnya sebagai literal JS, jadi di sini juga.
const MODEL = new Function(`return (${readFileSync(new URL("./artefak/model_payray.json", import.meta.url), "utf8")});`)();
const inputs = JSON.parse(readFileSync(inPath));

const sigmoid = (z) => 1 / (1 + Math.exp(-z));
function rawPredict(x, phi) {
  let s = MODEL.base;
  for (const t of MODEL.trees) {
    let i = 0;
    s += t.v[0];
    while (!t.leaf[i]) {
      const f = t.f[i], xv = x[f];
      const j = (xv === null || Number.isNaN(xv)) ? (t.m[i] ? t.l[i] : t.r[i]) : (xv <= t.t[i] ? t.l[i] : t.r[i]);
      if (phi) phi[f] += t.v[j] - t.v[i];
      s += t.v[j] - t.v[i];
      i = j;
    }
  }
  return s;
}
function interp(x, xs, ys) {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  let lo = 0, hi = xs.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
  return ys[lo] + (ys[hi] - ys[lo]) * (x - xs[lo]) / ((xs[hi] - xs[lo]) || 1);
}
function predict(x, pr) {
  const raw = rawPredict(x);
  const p = sigmoid(raw);
  const pm = interp(p, MODEL.kalibrasi.x, MODEL.kalibrasi.y);
  const z = Math.max(-9.21, Math.min(9.21, raw));
  const pg = sigmoid(MODEL.stack.ml * z + MODEL.stack.aturan * pr + MODEL.stack.c);
  return { raw, pm, pg };
}

const rows = inputs.rows.map((r) => ({ ...r, score_js: predict(r.x, r.pr).pg }));
rows.sort((a, b) => (b.score_js - a.score_js) || (a.employer_id - b.employer_id));
rows.forEach((r, k) => { r.rank_js = k + 1; });
writeFileSync(outPath, JSON.stringify({ source: inputs.source, model_sha256: inputs.model_sha256, rows }));
console.log(`${rows.length} skor referensi ditulis ke ${outPath}`);
