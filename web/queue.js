// Antrean (Alur A). Posisi scroll dan halaman yang sudah dimuat disimpan di memori modul,
// supaya kembali dari lembar hasil scan tidak mengulang dari atas.
import { api, MODE } from "./api.js";
import { h, clear, icon } from "./dom.js";
import { go, setBatch } from "./app.js";
import { rpShort } from "./format.js";
import { bd, card, clickRow, labelRows, legend, disclaimer } from "./ui.js";
import { CONF } from "./catalog.js";

const mem = { batchId: null, items: [], cursor: null, scrollY: 0, focusId: null };

export function rememberScroll(employerId) {
  mem.scrollY = window.scrollY;
  mem.focusId = employerId;
}

export const scoreCell = (score) => h("span", { class: "ev" },
  h("span", { class: "fit", "aria-hidden": "true" }, h("i", { style: { width: `${Math.max(3, Math.round(score * 100))}%` } })),
  h("b", {}, Math.round(score * 100)));

export const confBadge = (bucket) => bd(CONF[bucket]?.[1] || "d", CONF[bucket]?.[0] || bucket);

export function flags(it) {
  if (!it.sme_protection && !it.verify_first) return null;
  return h("span", { class: "tags" },
    it.sme_protection && h("span", { class: "b g" }, icon("shield"), "Perlindungan UMKM"),
    it.verify_first && h("span", { class: "b a" }, icon("alert"), "Verifikasi data dulu"));
}

function rpCell(it) {
  if (it.rp_low === null || it.rp_low === undefined) return [h("span", {}, `Band ${it.rp_band}`), h("small", {}, "indikatif")];
  return [h("span", {}, `${rpShort(it.rp_low)} – ${rpShort(it.rp_high)}`), h("small", {}, "indikatif / tahun")];
}

const statusCell = (it) => it.inspection_status === "submitted"
  ? h("span", { class: "b g" }, icon("check"), "Sudah diperiksa")
  : h("span", { class: "b" }, "Belum diperiksa");

function row(it) {
  const open = () => { rememberScroll(it.employer_id); go(`#/bu/${it.employer_id}`); };
  const tr = h("tr", { dataset: { id: it.employer_id } },
    h("td", { class: "num" }, h("b", {}, it.rank)),
    h("td", {}, h("a", { href: `#/bu/${it.employer_id}`, class: "nm", onclick: (e) => { e.preventDefault(); open(); } }, it.name),
      h("small", {}, it.sector), flags(it)),
    h("td", {}, scoreCell(it.score)),
    h("td", {}, confBadge(it.confidence_bucket)),
    h("td", {}, h("ul", { class: "rl" }, it.reasons.slice(0, 2).map((r) => h("li", { title: r.text }, r.text)))),
    h("td", {}, rpCell(it)),
    h("td", {}, statusCell(it)));
  return clickRow(tr, open);
}

const skeleton = (n = 8) => Array.from({ length: n }, () => h("tr", { "aria-hidden": "true" },
  Array.from({ length: 7 }, () => h("td", {}, h("span", { class: "sk" })))));

const COLS = ["#Rank", "Badan usaha & sektor", "Skor", "Keyakinan", "Alasan utama", "Rp indikatif", "Status"];

export async function renderQueue(main) {
  clear(main);
  document.title = "Antrean · PayRay";
  const tbody = h("tbody", {});
  const tbl = h("table", { class: "rsp" },
    h("caption", { class: "visually-hidden" }, "Antrean prioritas pemeriksaan, diurutkan dari skor tertinggi"),
    h("thead", {}, h("tr", {}, COLS.map((c) => h("th", { scope: "col", class: c.startsWith("#") ? "num" : null }, c.replace(/^#/, ""))))),
    tbody);
  const more = h("button", { class: "btn l", type: "button", hidden: true }, "10 berikutnya", icon("right", 16));
  const errorBox = h("div", { class: "notice error", hidden: true, role: "alert" });
  const count = h("span", { class: "fn" });
  const actions = [
    MODE === "live" && h("a", { class: "btn l", href: "/api/queue.csv", download: true }, icon("download", 16), "Ekspor CSV"),
  ];
  main.append(errorBox,
    card("Diurutkan dari skor risiko tertinggi", [
      h("div", { class: "tw" }, tbl),
      h("div", { class: "ch", style: { margin: "14px 0 0" } }, count, more),
      disclaimer(),
    ], actions),
    legend());

  const paint = () => {
    clear(tbody).append(...mem.items.map(row));
    labelRows(tbl);
    more.hidden = !mem.cursor;
    count.textContent = mem.items.length ? `Menampilkan ${mem.items.length} BU teratas. Klik baris untuk membuka lembar hasil scan.` : "";
  };
  const empty = () => {
    clear(tbody).append(h("tr", {}, h("td", { colspan: 7, class: "empty" },
      h("strong", {}, "Belum ada batch terpublikasi untuk cabang ini."),
      "Antrean muncul setelah supervisor menjalankan dan memublikasikan rescore.")));
  };
  const fail = (e) => {
    errorBox.hidden = false;
    clear(errorBox).append(icon("alert"), h("span", {}, `Antrean gagal dimuat: ${e.message}`),
      h("button", { class: "btn l", type: "button", onclick: () => renderQueue(main) }, "Coba lagi"));
  };

  more.addEventListener("click", async () => {
    more.disabled = true;
    try {
      const page = await api(`/queue?limit=10&cursor=${encodeURIComponent(mem.cursor)}`);
      mem.items.push(...page.items);
      mem.cursor = page.next_cursor;
      paint();
      tbody.querySelector(`tr[data-id="${page.items[0]?.employer_id}"] a`)?.focus();
    } catch (e) { fail(e); } finally { more.disabled = false; }
  });

  if (mem.items.length) {
    paint();
    // Langsung (bukan rAF): rAF tidak berjalan di tab tersembunyi, scroll harus tetap pulih.
    window.scrollTo(0, mem.scrollY);
    tbody.querySelector(`tr[data-id="${mem.focusId}"] a`)?.focus({ preventScroll: true });
    return;
  }
  tbody.append(...skeleton());
  try {
    const page = await api("/queue?limit=10");
    if (!page.batch) { empty(); return; }
    setBatch(page.batch);
    Object.assign(mem, { batchId: page.batch.id, items: page.items, cursor: page.next_cursor });
    paint();
  } catch (e) {
    clear(tbody);
    fail(e);
  }
}

export function markInspected(employerId) {
  for (const it of mem.items) if (it.employer_id === employerId) it.inspection_status = "submitted";
}

export function resetQueueMemory() {
  Object.assign(mem, { batchId: null, items: [], cursor: null, scrollY: 0, focusId: null });
}
