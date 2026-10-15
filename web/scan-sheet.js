// Scan Sheet satu BU (Alur A langkah 5–7). Kembali via tombol atau Esc dengan posisi antrean tetap.
import { api } from "./api.js";
import { h, clear, icon, svg } from "./dom.js";
import { go } from "./app.js";
import { rp, CONF_LABEL } from "./format.js";

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
  median_upah_peer: ["Median upah BU sejenis (sektor, kab/kota)", "rp"],
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

function miniBar(value, max, label) {
  const w = 120;
  const fill = max > 0 ? Math.max(2, Math.round((value / max) * w)) : 2;
  return svg("svg", { width: w, height: 6, viewBox: `0 0 ${w} 6`, role: "img", "aria-label": label, class: "mini-bar" },
    svg("rect", { x: 0, y: 0, width: w, height: 6, rx: 3, class: "score-track" }),
    svg("rect", { x: 0, y: 0, width: fill, height: 6, rx: 3, class: "score-fill" }));
}

function evidenceList(ev) {
  const entries = Object.entries(ev || {});
  if (!entries.length) return null;
  return h("dl", { class: "evidence" }, entries.map(([k, v]) => {
    const [label, kind] = EVIDENCE_LABEL[k] || [k, typeof v === "number" ? "x" : "text"];
    return h("div", {}, h("dt", {}, label), h("dd", { class: "num" }, fmt(v, kind)));
  }));
}

function rpBlock(d) {
  if (d.rp.mode === "band") {
    return h("div", { class: "kv" }, h("span", { class: "k" }, "Estimasi iuran tak tertagih"),
      h("span", { class: "v" }, `Band ${d.rp.band}`), h("span", { class: "muted small" }, "indikatif, bukan tagihan"));
  }
  return h("div", { class: "kv" }, h("span", { class: "k" }, "Estimasi iuran tak tertagih / tahun"),
    h("span", { class: "v num" }, h("span", { class: "nw" }, rp(d.rp.low)), " – ", h("span", { class: "nw" }, rp(d.rp.high))),
    h("span", { class: "muted small" }, "indikatif, bukan tagihan"));
}

function back() {
  go("#/antrean");
}

function onKey(e) {
  if (e.key === "Escape" && !document.querySelector(".drawer-open")) back();
}

export async function renderScanSheet(main, employerId) {
  clear(main);
  document.removeEventListener("keydown", onKey);
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange", () => document.removeEventListener("keydown", onKey), { once: true });
  window.scrollTo(0, 0);

  const backBtn = h("button", { class: "btn btn-ghost", type: "button", onclick: back }, icon("arrowLeft"), h("span", {}, "Kembali ke antrean"), h("kbd", {}, "Esc"));
  main.append(h("div", { class: "sheet-nav" }, backBtn), h("div", { class: "sheet-skeleton", "aria-busy": "true" },
    h("span", { class: "sk sk-title" }), h("span", { class: "sk" }), h("span", { class: "sk" })));

  let d;
  try {
    d = await api(`/employers/${employerId}/scan-sheet`);
  } catch (e) {
    main.lastChild.remove();
    main.append(h("div", { class: "notice error", role: "alert" }, icon("alert"),
      h("span", {}, e.status === 404 ? "BU ini tidak ada di antrean cabang Anda." : `Scan sheet gagal dimuat: ${e.message}`)));
    backBtn.focus();
    return;
  }
  main.lastChild.remove();
  const maxContrib = Math.max(...d.reasons.map((r) => r.contribution), 0.0001);

  const header = h("section", { class: "sheet-head", "aria-labelledby": "bu-title" },
    h("div", { class: "sheet-title" },
      h("span", { class: "rank-badge num", "aria-label": `Rank ${d.rank}` }, `#${d.rank}`),
      h("div", {},
        h("h1", { id: "bu-title" }, d.employer.name),
        h("p", { class: "muted" }, `${d.employer.sector} · kab/kota ${d.employer.kab_kota} · ${d.employer.reported_headcount.toLocaleString("id-ID")} pekerja PPU dilaporkan`))),
    h("div", { class: "sheet-stats" },
      h("div", { class: "kv" }, h("span", { class: "k" }, "Skor prioritas"),
        h("span", { class: "v num" }, Math.round(d.score * 100), h("span", { class: "muted small" }, " / 100")),
        miniBar(d.score, 1, `Skor ${Math.round(d.score * 100)} dari 100`)),
      h("div", { class: "kv" }, h("span", { class: "k" }, "Confidence"),
        h("span", { class: `chip conf conf-${d.confidence_bucket}` }, h("span", { class: "dot", "aria-hidden": "true" }), CONF_LABEL[d.confidence_bucket])),
      rpBlock(d)),
    (d.sme_protection || d.verify_first) && h("div", { class: "sme" },
      d.sme_protection && h("div", { class: "sme-badge" },
        h("span", { class: "chip info" }, icon("shield"), "Perlindungan UMKM padat karya"),
        h("p", {}, "Usaha kecil di sektor padat karya. Badge ini tidak mengubah peringkat; pendekatan pembinaan lebih dulu sebelum pemeriksaan.")),
      d.verify_first && h("span", { class: "chip warn" }, icon("alert"), "Verifikasi data dulu")),
    h("p", { class: "disclaimer" }, "Prioritas pemeriksaan, bukan tuduhan."));

  const reasons = h("section", { class: "sheet-reasons", "aria-labelledby": "reasons-title" },
    h("h2", { id: "reasons-title" }, "Alasan, urut dari kontribusi terbesar"),
    h("ol", { class: "reason-detail" }, d.reasons.map((r) => h("li", {},
      h("div", { class: "reason-top" },
        h("p", { class: "reason-text" }, r.text),
        h("span", { class: "contrib" }, miniBar(r.contribution, maxContrib, `Kontribusi relatif ${Math.round((r.contribution / maxContrib) * 100)}%`))),
      h("span", { class: "code" }, r.code),
      evidenceList(r.evidence)))));

  let n = 0;
  const checklist = h("section", { class: "panel", "aria-labelledby": "check-title" },
    h("h2", { id: "check-title" }, "Checklist pemeriksaan"),
    d.reasons.filter((r) => r.checklist.length).map((r) => h("fieldset", { class: "check-group" },
      h("legend", {}, r.code),
      r.checklist.map((c) => {
        const id = `chk-${n++}`;
        return h("div", { class: "check" }, h("input", { type: "checkbox", id }), h("label", { for: id }, c));
      }))),
    h("p", { class: "muted small" }, "Centang hanya bantu ingat di layar ini, tidak disimpan."));

  const inspectBtn = h("button", { class: "btn btn-primary btn-block", type: "button", id: "btn-inspect",
    disabled: d.inspection_status === "submitted" }, icon("clipboard"),
  d.inspection_status === "submitted" ? "Sudah diperiksa periode ini" : "Catat hasil inspeksi");
  inspectBtn.addEventListener("click", async () => {
    const { openInspectionForm } = await import("./inspection-form.js");
    openInspectionForm(d, inspectBtn);
  });

  const workers = h("section", { class: "panel", "aria-labelledby": "workers-title" },
    h("h2", { id: "workers-title" }, `Pekerja ter-flag (${d.flagged_workers.length})`),
    d.flagged_workers.length
      ? h("div", { class: "workers-scroll", tabindex: 0, role: "region", "aria-label": "Daftar pekerja ter-flag" },
        h("table", { class: "data workers" },
          h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Token"), h("th", { scope: "col" }, "Indikasi"))),
          h("tbody", {}, d.flagged_workers.map((w) => h("tr", {}, h("td", { class: "mono" }, w.nik_token8), h("td", {}, w.reason))))))
      : h("p", { class: "muted small" }, "Tidak ada pekerja yang ter-flag."),
    h("p", { class: "muted small" }, "Token = 8 karakter pertama pseudonim NIK (HMAC). NIK asli tidak disimpan."));

  main.append(h("div", { class: "sheet-grid" },
    h("div", { class: "sheet-main" }, header, reasons),
    h("aside", { class: "sheet-side", "aria-label": "Tindakan pemeriksaan" }, inspectBtn, checklist, workers)));
  document.title = `${d.employer.name} · PayRay`;
  document.getElementById("bu-title").setAttribute("tabindex", "-1");
  document.getElementById("bu-title").focus({ preventScroll: true });
}
