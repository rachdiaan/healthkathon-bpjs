// Ringkasan batch aktif: KPI dengan asal angka, alasan terbanyak di 10% teratas, sebaran keyakinan.
import { api } from "./api.js";
import { h, clear, icon, svg } from "./dom.js";
import { setBatch, state } from "./app.js";
import { rpShort, period } from "./format.js";
import { card, kpi, insight, legend, openInfo, hbar, num, pct, bd } from "./ui.js";
import { REASONS, reasonModule, CONF, MODULES } from "./catalog.js";

const CONF_INFO = {
  tinggi: "Data BU lengkap dan pola serupa sering terbukti di hasil pemeriksaan. Aman didahulukan.",
  sedang: "Sebagian data pembanding tipis, atau dua metode (aturan dan model) tidak sepakat penuh.",
  rendah: "Data sedikit, misalnya wilayah dengan sedikit BU sejenis. Tidak diprioritaskan sebelum datanya dilengkapi.",
};

function scoreChart(hist) {
  const max = Math.max(...hist, 1), H = 150, y = (v) => 170 - (v / max) * H;
  const ticks = [0, 0.5, 1].map((t) => Math.round(max * t));
  return h("div", { class: "chw" }, svg("svg", { viewBox: "0 0 640 210", role: "img", "aria-label": "Sebaran skor risiko seluruh BU di batch" },
    ticks.map((v) => [svg("line", { x1: 40, x2: 636, y1: y(v), y2: y(v), class: "gl" }),
      svg("text", { x: 0, y: y(v) + 4, class: "tx" }, num(v))]),
    hist.map((v, i) => {
      const x = 50 + i * 58;
      return [svg("rect", { x, y: y(v), width: 44, height: Math.max(1, 170 - y(v)), rx: 5, class: i >= 7 ? "c1" : i >= 4 ? "c2" : "c3" },
        svg("title", {}, `Skor ${i * 10}–${i * 10 + 9}: ${num(v)} BU`)),
      svg("text", { x: x + 22, y: 190, "text-anchor": "middle", class: "tx" }, `${i * 10}`)];
    }),
    svg("text", { x: 636, y: 206, "text-anchor": "end", class: "tx" }, "skor (0–100)")));
}

function reasonInfo(code, n, top) {
  const [label, mod, what, miss] = REASONS[code] || [code, "", "Alasan dari mesin scan.", "-"];
  return { t: `${label}: ${num(n)} dari ${num(top)} BU prioritas`, c: "d",
    s: `${MODULES[mod]?.[0] || "Mesin scan"}. ${what}`,
    h: "Dihitung dari dua alasan teratas tiap BU di 10% antrean teratas. Satu BU bisa punya dua alasan.",
    w: miss, u: "Menentukan jenis pemeriksaan yang perlu disiapkan tim, misalnya slip gaji atau daftar hadir." };
}

export async function renderSummary(main) {
  clear(main);
  document.title = "Ringkasan · PayRay";
  const kpis = h("div", { class: "row4" }, Array.from({ length: 4 }, () => h("div", { class: "kp" }, h("span", { class: "sk" }), h("span"), h("span", { class: "sk t" }))));
  main.append(kpis);
  let s;
  try {
    s = await api("/summary");
  } catch (e) {
    clear(main).append(h("div", { class: "notice error", role: "alert" }, icon("alert"), h("span", {}, `Ringkasan gagal dimuat: ${e.message}`)));
    return;
  }
  if (!s.batch) {
    clear(main).append(card("Belum ada batch", h("p", { class: "fn" }, "Ringkasan muncul setelah supervisor menjalankan dan memublikasikan rescore.")));
    return;
  }
  setBatch(s.batch);
  const branch = state.me?.branch_name || "cabang ini";
  const p = period(s.batch.period);
  const rp100 = s.rp_top100;

  clear(kpis).append(
    kpi("Badan usaha dinilai", num(s.n), "m", `${branch}, batch ${p}`, {
      t: `${num(s.n)} badan usaha dinilai di batch ${p}`, c: "m",
      s: "Semua BU terdaftar di cabang ini pada batch yang sedang aktif. Tidak ada sampel: semua BU diberi skor.",
      h: "Jumlah baris skor risiko di batch yang dipublikasikan supervisor.",
      w: "Data BU baru belum masuk sebelum rescore berikutnya.", u: "Aman dipakai sebagai cakupan penilaian." }),
    kpi("Antrean prioritas", num(s.top_n), "d", "10% skor tertinggi", {
      t: `${num(s.top_n)} BU masuk 10% teratas`, c: "d",
      s: "Skor gabungan aturan transparan dan model yang belajar dari hasil pemeriksaan.",
      h: `10% dari ${num(s.n)} BU, dibulatkan ke atas. Di data uji sintetis, presisi 10% teratas 82,2% dibanding 15% bila dipilih acak.`,
      w: "Pola ketidakpatuhan baru yang belum pernah diperiksa. Karena itu sebagian kecil pemeriksaan tetap dipilih acak.",
      u: "Urutan kerja tim. Keputusan memeriksa tetap di petugas." }),
    rp100
      ? kpi("Estimasi iuran, 100 teratas", `${rpShort(rp100.low)}–${rpShort(rp100.high).replace("Rp ", "")}`, "a", "indikatif per tahun, bukan tagihan", {
        t: "Estimasi iuran tak tertagih di 100 BU teratas", c: "a",
        s: "Jumlah rentang estimasi tiap BU: selisih upah dilaporkan dengan upah wajar BU sejenis, ditambah pekerja yang dipindah ke PBPU.",
        h: "(min(upah wajar, plafon) − min(upah dilaporkan, plafon)) × 5% × pekerja × 12, dijumlah untuk rank 1–100.",
        w: "Kalkulator Rp lebih lemah dari skor risiko. Di data uji rentang memuat nilai sebenarnya pada sekitar 84% BU.",
        u: "Gambaran besarnya potensi. Jangan dipakai sebagai angka tagihan atau target." }, { small: true })
      : kpi("Estimasi iuran, 100 teratas", "Mode band", "a", "angka Rp disembunyikan", null, { small: true }),
    kpi("Sudah diperiksa", num(s.inspected), "m", `periode berjalan, dari ${num(s.n)} BU`, {
      t: `${num(s.inspected)} BU sudah diperiksa periode ini`, c: "m",
      s: "Inspeksi berstatus tersimpan di bulan berjalan (WIB).", h: "Hitung BU unik dengan inspeksi tersimpan.",
      w: "Inspeksi yang dicatat terlambat masuk ke periode tanggal pemeriksaannya.",
      u: "Memantau apakah antrean benar-benar dikerjakan." }));

  const codes = Object.entries(s.reason_codes_top).sort((a, b) => b[1] - a[1]);
  const maxCode = codes[0]?.[1] || 1;
  const reasonsCard = card("Alasan terbanyak di 10% teratas", [
    h("div", {}, codes.map(([code, n]) => hbar(REASONS[code]?.[0] || code, n, maxCode, `${num(n)} BU`, reasonModule(code)[1],
      (e) => openInfo(reasonInfo(code, n, s.top_n), e.currentTarget)))),
    h("p", { class: "lgd" }, [["Scan Upah", "f1"], ["Scan Headcount", "f2"], ["Scan Status", "fa"], ["Anomali / data", "f3"]]
      .map(([l, c]) => h("span", {}, h("i", { class: c }), l)))],
  h("a", { class: "btn l", href: "#/antrean" }, "Buka antrean"));

  const verify = s.verify_first, sme = s.sme_protection;
  const notes = card("Catatan penting", h("div", { class: "ins" },
    insight("a", "alert", `${num(verify)} BU perlu verifikasi data dulu`,
      "UMKM padat karya dengan keyakinan rendah. Lengkapi datanya sebelum diperiksa.", ["Lihat antrean", "#/antrean"]),
    insight("g", "shield", `${num(sme)} BU mendapat perlindungan UMKM`,
      "Usaha mikro dan kecil dikecualikan dari upah minimum (PP 36/2021). Badge tidak mengubah rank; dahulukan pembinaan.", ["Lihat aturannya", "#/cara-kerja"]),
    insight("g", "target", "Diuji di 5.000 BU sintetis",
      "Presisi 10% teratas 82,2%, lift 5,5× dibanding acak, salah tandai UMKM 2,7%.", ["Lihat validasi", "#/validasi"]),
    insight("a", "flag", "Skor bukan tuduhan",
      "PayRay hanya mengurutkan prioritas. Hasil pemeriksaan petugas masuk lagi sebagai label untuk model.", ["Cara kerja", "#/cara-kerja"])));

  const segs = Object.entries(CONF).map(([k, [label]]) => {
    const n = s.confidence[k] || 0;
    const b = h("button", { type: "button", "data-info": "", class: k === "sedang" ? "dk" : null, "aria-pressed": "false",
      style: { flex: String(Math.max(n, s.n * 0.06)) } }, h("b", {}, num(n)), h("span", {}, label));
    b.classList.add(k === "tinggi" ? "f1" : k === "sedang" ? "f3" : "fa");
    b.addEventListener("click", (e) => {
      segRow.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      openInfo({ t: `${label}: ${num(n)} BU (${pct(n / s.n)})`, c: "d", s: CONF_INFO[k],
        h: "Keyakinan dihitung dari kelengkapan data, jumlah BU pembanding di sektor dan wilayah yang sama, dan kesepakatan antara aturan dan model.",
        w: "Wilayah atau sektor baru dengan sedikit pembanding.",
        u: k === "rendah" ? "Jangan didahulukan. Lengkapi data lebih dulu." : "Boleh dipakai untuk menyusun urutan pemeriksaan." }, e.currentTarget);
    });
    return b;
  });
  const segRow = h("div", { class: "sg" }, segs);
  const confCard = card(`Seberapa yakin skornya: ${num(s.n)} BU`, [segRow,
    h("div", { class: "cats" },
      [["tinggi", "f1"], ["sedang", "f3"], ["rendah", "fa"]].map(([k, c]) => h("div", {},
        h("span", {}, CONF[k][0]), h("b", { class: "big", style: { display: "block" } }, pct((s.confidence[k] || 0) / s.n)),
        h("i", { class: c, style: { width: `${Math.max(3, ((s.confidence[k] || 0) / s.n) * 100)}%`, display: "block", height: "14px", borderRadius: "3px" } }),
        h("small", {}, `${num(s.confidence[k] || 0)} BU`))),
      h("div", {}, h("span", {}, "Perlindungan UMKM"), h("b", { class: "big", style: { display: "block" } }, pct(sme / s.n)),
        h("i", { class: "fg", style: { width: `${Math.max(3, (sme / s.n) * 100)}%`, display: "block", height: "14px", borderRadius: "3px" } }),
        h("small", {}, `${num(sme)} BU`)))]);

  main.append(
    h("div", { class: "g" }, reasonsCard, notes),
    h("div", { class: "g2" }, confCard,
      card("Sebaran skor risiko", [scoreChart(s.score_hist),
        h("p", { class: "fn", style: { marginTop: "6px" } }, "Sebagian besar BU berskor rendah. Antrean berfokus pada ekor kanan.", " ", bd("d"))])),
    legend());
}
