// Lembar hasil scan satu BU (Alur A langkah 5–7). Kembali via tombol atau Esc dengan posisi antrean tetap.
import { api } from "./api.js";
import { h, clear, icon } from "./dom.js";
import { go } from "./app.js";
import { rp } from "./format.js";
import { bd, card, openInfo, disclaimer, table } from "./ui.js";
import { REASONS, reasonLabel, reasonModule } from "./catalog.js";
import { confBadge, flags } from "./queue.js";

const EVIDENCE_LABEL = {
  porsi_tepat_umk: ["Pekerja tepat di UMK", "pct"],
  porsi_atas_umk: ["Pekerja di atas UMK", "pct"],
  porsi_bawah_umk: ["Pekerja di bawah UMK", "pct"],
  porsi_naik_sama_umk: ["Kenaikan = kenaikan UMK", "pct"],
  porsi_upah_beku: ["Pekerja upah tidak naik", "pct"],
  pasangan_kenaikan: ["Data upah antar-tahun (pasang)", "int"],
  n_pekerja: ["Pekerja dilaporkan", "int"],
  n_pekerja_awal: ["Rata-rata pekerja terdaftar", "int"],
  tk_oss: ["Rencana tenaga kerja OSS", "int"],
  rasio_headcount_oss: ["Terdaftar / rencana OSS", "pct"],
  p90_rasio_umk: ["Upah 10% teratas / UMK", "x"],
  median_upah: ["Median upah dilaporkan", "rp"],
  umk_terakhir: ["UMK kab/kota", "rp"],
  benchmark_upah: ["Median upah sektor (benchmark)", "rp"],
  klaster_pbpu_n: ["Pekerja pindah ke PBPU", "int"],
  klaster_pbpu_porsi: ["Porsi pindah ke PBPU", "pct"],
  skala_usaha: ["Skala usaha", "text"],
  persentil_anomali: ["Persentil anomali", "pct"],
  median_upah_peer: ["Median upah BU sejenis", "rp"],
  rasio_upah_peer: ["Upah vs BU sejenis", "pct"],
};

function fmt(v, kind) {
  if (v === null || v === undefined) return "tidak ada data";
  if (kind === "pct") return `${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;
  if (kind === "x") return `${Number(v).toLocaleString("id-ID", { maximumFractionDigits: 2 })}×`;
  if (kind === "rp") return `Rp ${Math.round(v).toLocaleString("id-ID")}`;
  if (kind === "int") return Math.round(v).toLocaleString("id-ID");
  return String(v);
}

function evidenceList(ev) {
  const entries = Object.entries(ev || {});
  if (!entries.length) return null;
  return h("dl", { class: "evd" }, entries.map(([k, v]) => {
    const [label, kind] = EVIDENCE_LABEL[k] || [k, typeof v === "number" ? "x" : "text"];
    return h("div", {}, h("dt", {}, label), h("dd", {}, fmt(v, kind)));
  }));
}

const RP_INFO = {
  t: "Estimasi iuran tak tertagih per tahun", c: "a",
  s: "Upah wajar dari median BU sejenis (sektor dan kab/kota) dan benchmark upah sektor, dibanding upah yang dilaporkan. Ditambah pekerja yang dipindah ke PBPU.",
  h: "(min(upah wajar, plafon) − min(upah dilaporkan, plafon)) × 5% × jumlah pekerja × 12, ditambah porsi pekerja yang pindah ke PBPU. Ditampilkan sebagai rentang (interval konformal), dibulatkan ke Rp100.000.",
  w: "Upah wajar BU ini memang lebih rendah dari BU sejenis, atau data pekerja belum lengkap. Di data uji, rentang memuat nilai sebenarnya pada sekitar 84% BU.",
  u: "Dipakai untuk mengurutkan dan menyiapkan pemeriksaan. Bukan tagihan dan tidak boleh disampaikan ke pemberi kerja sebagai angka tagihan.",
};

function reasonInfo(r) {
  const [label, , what, miss] = REASONS[r.code] || [r.code, "", r.text, "-"];
  return { t: label, c: "d", s: what, sl: "Apa artinya", h: r.checklist?.length ? r.checklist : "Tidak ada checklist khusus.",
    hl: "Yang dicek saat pemeriksaan", w: miss, u: "Alasan ini dasar memilih BU untuk diperiksa, bukan bukti ketidakpatuhan." };
}

function back() {
  go("#/antrean");
}

function onKey(e) {
  if (e.key === "Escape" && !document.body.classList.contains("drawer-open")) back();
}

export async function renderScanSheet(main, employerId) {
  clear(main);
  document.removeEventListener("keydown", onKey);
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange", () => document.removeEventListener("keydown", onKey), { once: true });
  window.scrollTo(0, 0);

  const backBtn = h("button", { class: "back", type: "button", onclick: back }, icon("back", 16), "Kembali ke antrean", h("kbd", {}, "Esc"));
  const sk = h("section", { class: "cd", "aria-busy": "true" }, h("span", { class: "sk t" }), h("p", {}, " "), h("span", { class: "sk" }));
  main.append(backBtn, sk);

  let d;
  try {
    d = await api(`/employers/${employerId}/scan-sheet`);
  } catch (e) {
    sk.remove();
    main.append(h("div", { class: "notice error", role: "alert" }, icon("alert"),
      h("span", {}, e.status === 404 ? e.message || "BU ini tidak ada di antrean cabang Anda." : `Lembar hasil scan gagal dimuat: ${e.message}`)));
    backBtn.focus();
    return;
  }
  sk.remove();
  const maxContrib = Math.max(...d.reasons.map((r) => r.contribution), 0.0001);
  const e = d.employer;

  const head = h("section", { class: "cd" },
    h("div", { class: "ch" },
      h("div", {}, h("span", { class: "fn" }, `Rank #${d.rank} di antrean`),
        h("h2", { id: "bu-title", tabindex: -1, style: { fontSize: "22px", fontWeight: "600", letterSpacing: "-.02em", margin: "2px 0" } }, e.name),
        h("span", { class: "fn" }, `${e.sector} · kab/kota ${e.kab_kota}`)),
      flags(d)),
    h("div", { class: "stat4" },
      h("div", {}, h("span", { class: "k" }, "Skor prioritas"), h("b", {}, Math.round(d.score * 100), h("span", { class: "fn" }, " / 100")),
        h("span", { class: "fit", "aria-hidden": "true", style: { width: "100%" } }, h("i", { style: { width: `${Math.round(d.score * 100)}%` } }))),
      h("div", {}, h("span", { class: "k" }, "Keyakinan"), confBadge(d.confidence_bucket)),
      h("div", {}, h("span", { class: "k" }, "Pekerja PPU dilaporkan"), h("b", {}, e.reported_headcount.toLocaleString("id-ID"))),
      h("div", {}, h("span", { class: "k" }, "Jumlah alasan"), h("b", {}, d.reasons.length))),
    d.sme_protection && h("p", { class: "disc" }, icon("shield", 16),
      "Usaha kecil di sektor padat karya. Badge ini tidak mengubah peringkat; dahulukan pembinaan sebelum pemeriksaan."),
    disclaimer());

  const reasons = card("Alasan, urut dari kontribusi terbesar", h("ol", { class: "rsn" }, d.reasons.map((r) => {
    const [mod, fill] = reasonModule(r.code);
    const share = Math.round((r.contribution / maxContrib) * 100);
    return h("li", {},
      h("div", { class: "top" },
        h("div", {}, h("p", {}, r.text), h("span", { class: "tags" }, h("span", { class: "chip" }, mod), h("span", { class: "chip mono" }, r.code))),
        h("button", { class: "ar", type: "button", "aria-label": `Penjelasan alasan ${reasonLabel(r.code)}`, onclick: (ev) => openInfo(reasonInfo(r), ev.currentTarget) }, icon("arrow", 16))),
      h("div", { class: "hb", style: { padding: "0" } }, h("span", { class: "fn" }, "Kontribusi relatif"),
        h("i", { class: fill, style: { width: `${Math.max(2, share)}%` } }), h("b", {}, `${share}%`)),
      evidenceList(r.evidence));
  })));

  const inspectBtn = h("button", { class: "btn blk", type: "button", id: "btn-inspect",
    disabled: d.inspection_status === "submitted" }, icon("clipboard", 18),
  d.inspection_status === "submitted" ? "Sudah diperiksa periode ini" : "Catat hasil inspeksi");
  inspectBtn.addEventListener("click", async () => {
    const { openInspectionForm } = await import("./inspection-form.js");
    openInspectionForm(d, inspectBtn);
  });

  const rpBox = d.rp.mode === "band"
    ? [h("p", { class: "rp" }, `Band ${d.rp.band}`)]
    : [h("p", { class: "rp" }, rp(d.rp.low), " – ", rp(d.rp.high))];
  const rpCard = card("Estimasi iuran tak tertagih / tahun", [...rpBox,
    h("div", { class: "legend", style: { marginTop: "8px" } }, bd("a"), h("span", { class: "fn" }, "indikatif, bukan tagihan"))],
  h("button", { class: "ar", type: "button", "aria-label": "Asal angka estimasi iuran", onclick: (ev) => openInfo(RP_INFO, ev.currentTarget) }, icon("arrow", 16)));

  let n = 0;
  const checklist = card("Checklist pemeriksaan", [
    d.reasons.filter((r) => r.checklist.length).map((r) => h("fieldset", { class: "cg" },
      h("legend", {}, reasonLabel(r.code)),
      r.checklist.map((c) => {
        const id = `chk-${n++}`;
        return h("div", { class: "check" }, h("input", { type: "checkbox", id }), h("label", { for: id }, c));
      }))),
    h("p", { class: "fn" }, "Centang hanya bantu ingat di layar ini, tidak disimpan.")]);

  const workers = card(`Pekerja ter-flag (${d.flagged_workers.length})`, [
    d.flagged_workers.length
      ? h("div", { class: "wk", tabindex: 0, role: "region", "aria-label": "Daftar pekerja ter-flag" },
        table(["Token", "Indikasi"], h("tbody", {}, d.flagged_workers.map((w) => h("tr", {}, h("td", { class: "mono" }, w.nik_token8), h("td", {}, w.reason)))), "Pekerja ter-flag"))
      : h("p", { class: "fn" }, "Tidak ada pekerja yang ter-flag."),
    h("p", { class: "fn", style: { marginTop: "10px" } }, "Token = 8 karakter pertama pseudonim NIK (HMAC). NIK asli tidak disimpan.")]);

  main.append(h("div", { class: "g" },
    h("div", { class: "stack" }, head, reasons),
    h("aside", { class: "stack", "aria-label": "Tindakan pemeriksaan" },
      h("section", { class: "cd" }, inspectBtn, h("p", { class: "fn", style: { marginTop: "10px" } }, "Hasil pemeriksaan masuk kembali ke PayRay sebagai label baru untuk model.")),
      rpCard, checklist, workers)));
  document.title = `${e.name} · PayRay`;
  document.getElementById("bu-title").focus({ preventScroll: true });
}
