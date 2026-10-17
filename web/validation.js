// Validasi model: dibaca dari data/validasi.json (salinan ml/artefak/validasi.json, artefak beku).
import { h, clear, icon, svg } from "./dom.js";
import { card, kpi, legend, openInfo, clickRow, table, hbar, pct, num, bd } from "./ui.js";
import { rpShort } from "./format.js";

let cache = null;
const load = () => (cache = cache || fetch("data/validasi.json", { cache: "no-cache" }).then((r) => {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}));

const METHODS = [
  ["PayRay gabungan (stacking)", "PayRay gabungan", "l1"],
  ["Model ML (dari hasil pemeriksaan)", "Model ML saja", "l2"],
  ["Aturan + Isolation Forest", "Aturan + Isolation Forest", "l3"],
  ["Acak", "Pemilihan acak", "la"],
];
const STEP = 50;

function curve(perb, holdout) {
  const W = 640, H = 230, x0 = 40, x1 = 630, y0 = 196, y1 = 14;
  const n = perb[METHODS[0][0]].kurva_precision.length;
  const x = (i) => x0 + (i / (n - 1)) * (x1 - x0), y = (v) => y0 - v * (y0 - y1);
  const topIdx = Math.round(holdout * 0.1 / STEP) - 1;
  return h("div", { class: "chw" }, svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Presisi menurut jumlah BU teratas yang diperiksa" },
    [0, 0.25, 0.5, 0.75, 1].map((v) => [svg("line", { x1: x0, x2: x1, y1: y(v), y2: y(v), class: "gl" }), svg("text", { x: 0, y: y(v) + 4, class: "tx" }, `${v * 100}%`)]),
    svg("line", { x1: x(topIdx), x2: x(topIdx), y1: y1, y2: y0, class: "mk" }),
    svg("text", { x: x(topIdx) + 6, y: y1 + 10, class: "tx" }, "10% teratas"),
    METHODS.map(([k, label, cls]) => svg("polyline", { class: `ln ${cls}`, points: perb[k].kurva_precision.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ") }, svg("title", {}, label))),
    [0, 9, 19, 29].map((i, j, a) => svg("text", { x: x(i), y: 214, "text-anchor": j === 0 ? "start" : j === a.length - 1 ? "end" : "middle", class: "tx" }, num((i + 1) * STEP))),
    svg("text", { x: (x0 + x1) / 2, y: 228, "text-anchor": "middle", class: "tx" }, "jumlah BU teratas yang diperiksa")),
  h("p", { class: "lgd" }, METHODS.map(([, label, cls]) => h("span", {}, h("i", { class: { l1: "f1", l2: "f2", l3: "f3", la: "fa" }[cls] }), label))));
}

function methodInfo(label, m) {
  return { t: label, c: "d",
    s: "Diuji pada 5.000 BU holdout data sintetis yang tidak dipakai saat melatih atau menyetel model (prevalensi 15%).",
    h: [`Presisi 10% teratas ${pct(m.precision_top)} (selang 95%: ${pct(m.precision_ci95[0])}–${pct(m.precision_ci95[1])})`,
      `Recall 10% teratas ${pct(m.recall_top)}, recall kasus sulit ${pct(m.recall_sulit)}`,
      `Lift ${num(m.lift, 2)}× dibanding acak · ROC-AUC ${num(m.roc_auc, 3)} · PR-AUC ${num(m.pr_auc, 3)}`,
      `Salah tandai UMKM ${pct(m.salah_tandai_umkm)}`, `Iuran tertangkap per 100 pemeriksaan ${rpShort(m.iuran_per100)}`],
    hl: "Hasil uji", w: "Data sintetis dibuat tim sendiri. Angka di data riil hampir pasti lebih rendah; pilot di satu Kantor Cabang diperlukan.",
    u: "Cukup untuk memilih metode prototype. Belum cukup sebagai klaim akurasi di data peserta riil." };
}

export async function renderValidation(main) {
  clear(main);
  document.title = "Validasi model · PayRay";
  main.append(h("section", { class: "cd" }, h("span", { class: "sk t" })));
  let v;
  try { v = await load(); } catch (e) {
    clear(main).append(h("div", { class: "notice error", role: "alert" }, icon("alert"), h("span", {}, `Data validasi gagal dimuat: ${e.message}`)));
    return;
  }
  clear(main);
  const P = v.perbandingan, best = P[METHODS[0][0]], rules = P["Aturan + Isolation Forest"], rnd = P.Acak;
  const holdout = v.desain.holdout_n;

  main.append(h("div", { class: "row4" },
    kpi("Presisi 10% teratas", pct(best.precision_top), "d", `aturan saja ${pct(rules.precision_top)}, acak ${pct(rnd.precision_top)}`, methodInfo("PayRay gabungan (stacking)", best)),
    kpi("Lift vs pemilihan acak", `${num(best.lift, 1)}×`, "d", `target ≈ 4,7× · prevalensi ${pct(v.desain.holdout_prevalensi, 0)}`, {
      t: "Lift dibanding pemilihan acak", c: "d", s: `Holdout ${num(holdout)} BU sintetis.`,
      h: "Presisi 10% teratas ÷ prevalensi. Prevalensi 15% berarti pemilihan acak menemukan sekitar 15 dari 100 BU.",
      w: "Prevalensi di data riil berbeda dari 15%.", u: "Pembanding efisiensi pemeriksaan, belum klaim untuk data riil." }),
    kpi("Salah tandai UMKM", pct(best.salah_tandai_umkm), "d", "target ≤ 5% · acak 10,2%", {
      t: "Salah tandai usaha mikro dan kecil", c: "d",
      s: "UMKM patuh yang masuk 10% teratas. Aturan upah dibedakan per skala usaha (PP 36/2021).",
      h: "UMKM patuh di 10% teratas ÷ seluruh UMKM patuh.", w: "Sektor padat karya sah yang membayar tepat di UMK.",
      u: "Uji bias wajib sebelum pilot. Di atas 5% berarti aturan perlu disetel ulang." }),
    kpi("Kalibrasi (ECE)", num(v.kalibrasi.ece, 3), "d", `Brier ${num(v.kalibrasi.brier, 3)} · acak ${num(v.kalibrasi.brier_acak, 3)}`, {
      t: "Seberapa jujur skor sebagai peluang", c: "d", s: "Kalibrasi isotonic di atas skor gabungan.",
      h: "Expected calibration error: rata-rata selisih peluang prediksi dan proporsi teramati per kelompok skor. Makin kecil makin baik.",
      w: "Prevalensi data riil berbeda, sehingga kalibrasi perlu diulang saat pilot.", u: "Skor boleh dibaca sebagai peluang kasar, bukan kepastian." })));

  const agree = Object.entries(v.kesepakatan);
  main.append(h("div", { class: "g" },
    card("Presisi menurut kedalaman antrean", [curve(P, holdout),
      h("p", { class: "fn", style: { marginTop: "6px" } }, "Makin dalam antrean diperiksa, presisi turun. 10% teratas dipakai sebagai batas kerja.")]),
    card("Kesepakatan dua metode", [
      agree.map(([k, a]) => h("div", { class: "li" }, h("span", {}, k, h("small", {}, `${num(a.n)} BU`)), h("b", {}, pct(a.precision)))),
      h("p", { class: "fn", style: { marginTop: "10px" } }, "Bila aturan dan model sama-sama menandai, presisinya tertinggi. Keyakinan skor memakai kesepakatan ini.")])));

  const rows = h("tbody", {}, METHODS.concat([["Gabungan × estimasi Rp (nilai harapan)", "Gabungan × estimasi Rp", ""]]).map(([k, label]) => {
    const m = P[k];
    return clickRow(h("tr", {},
      h("td", {}, h("b", {}, label)),
      h("td", {}, pct(m.precision_top), h("small", {}, `${pct(m.precision_ci95[0])}–${pct(m.precision_ci95[1])}`)),
      h("td", {}, pct(m.recall_top)),
      h("td", {}, `${num(m.lift, 1)}×`),
      h("td", {}, pct(m.salah_tandai_umkm)),
      h("td", {}, rpShort(m.iuran_per100))), (tr) => openInfo(methodInfo(label, m), tr));
  }));
  main.append(card("Perbandingan metode di 10% teratas", [
    table(["Metode", "Presisi (selang 95%)", "Recall", "Lift", "Salah tandai UMKM", "Iuran per 100 pemeriksaan"], rows, "Perbandingan metode"),
    h("p", { class: "fn", style: { marginTop: "10px" } }, "Mengurutkan berdasarkan nilai harapan Rp menangkap iuran paling besar, tetapi presisinya turun. Antrean default tetap memakai skor gabungan.")]));

  const fair = v.fairness;
  const imp = v.importance.filter((x) => x.permutation > 0).slice(0, 8);
  const maxImp = imp[0]?.permutation || 1;
  main.append(h("div", { class: "g2" },
    card("Uji bias per skala usaha", table(["Skala", "BU", "Presisi", "Recall", "Salah tandai"],
      h("tbody", {}, fair.map((f) => h("tr", {}, h("td", {}, h("b", {}, f.skala[0].toUpperCase() + f.skala.slice(1))), h("td", {}, num(f.n)),
        h("td", {}, pct(f.precision)), h("td", {}, pct(f.recall)),
        h("td", {}, h("span", { class: `b ${f.salah_tandai > 0.05 ? "a" : "g"}` }, pct(f.salah_tandai)))))), "Uji bias per skala usaha")),
    card("Fitur paling berpengaruh", [
      imp.map((x) => hbar(x.fitur, x.permutation, maxImp, num(x.permutation, 3), "f1")),
      h("p", { class: "fn", style: { marginTop: "8px" } }, "Permutation importance: turunnya PR-AUC bila fitur diacak.")])));

  const dq = v.kualitas_data, pass = dq.filter((x) => x.status === "lulus").length;
  main.append(h("div", { class: "g2" },
    card(`Pemeriksaan kualitas data: ${pass} dari ${dq.length} lulus`, h("div", {}, dq.map((x) => h("div", { class: "li" },
      h("span", {}, x.nama, h("small", {}, x.temuan)), h("span", { class: `b ${x.status === "lulus" ? "g" : "a"}` }, x.status === "lulus" ? "Lulus" : x.status))))),
    card("Desain uji", h("div", {},
      [["Label dari hasil pemeriksaan", num(v.desain.label_dari_pemeriksaan)], ["Dari antrean prioritas", num(v.desain.top_prioritas)],
        ["Dari audit acak (bobot IPW)", num(v.desain.audit_acak)], ["BU holdout", num(holdout)], ["Fitur model", num(v.desain.fitur)],
        ["Stabilitas presisi (bootstrap)", `${pct(v.stabilitas.precision_mean)} ± ${pct(v.stabilitas.precision_sd)}`],
        ["Rentang Rp memuat nilai sebenarnya", pct(v.rupiah.coverage_holdout)]]
        .map(([k, val]) => h("div", { class: "li" }, h("span", {}, k), h("b", {}, val)))))));
  main.append(h("p", { class: "fn legend" }, bd("d"), "Semua angka di halaman ini dihitung pada data sintetis, bukan data peserta riil."), legend());
}
