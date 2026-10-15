// Layar Antrean (Alur A). Posisi scroll dan halaman yang sudah dimuat disimpan di memori modul,
// supaya kembali dari Scan Sheet tidak mengulang dari atas.
import { api, MODE } from "./api.js";
import { h, clear, icon, svg } from "./dom.js";
import { go, state, renderTopbar } from "./app.js";
import { rpShort, wib, period, CONF_LABEL } from "./format.js";

const mem = { batchId: null, items: [], cursor: null, scrollY: 0, focusId: null };

export function rememberScroll(employerId) {
  mem.scrollY = window.scrollY;
  mem.focusId = employerId;
}

function scoreBar(score) {
  const w = 64;
  return h("span", { class: "score" },
    svg("svg", { width: w, height: 6, viewBox: `0 0 ${w} 6`, "aria-hidden": "true", class: "score-bar" },
      svg("rect", { x: 0, y: 0, width: w, height: 6, rx: 3, class: "score-track" }),
      svg("rect", { x: 0, y: 0, width: Math.max(2, Math.round(score * w)), height: 6, rx: 3, class: "score-fill" })),
    h("span", { class: "num" }, Math.round(score * 100)));
}

function confChip(bucket) {
  return h("span", { class: `chip conf conf-${bucket}` }, h("span", { class: "dot", "aria-hidden": "true" }), CONF_LABEL[bucket]);
}

function rpCell(it) {
  if (it.rp_low === null || it.rp_low === undefined) {
    return [h("span", {}, `Band ${it.rp_band}`), h("span", { class: "muted small" }, "indikatif")];
  }
  return [h("span", { class: "num" }, `${rpShort(it.rp_low)} – ${rpShort(it.rp_high)}`),
    h("span", { class: "muted small" }, "indikatif / tahun")];
}

function statusCell(it) {
  return it.inspection_status === "submitted"
    ? h("span", { class: "status done" }, icon("check"), "Sudah diperiksa")
    : h("span", { class: "status" }, "Belum diperiksa");
}

function row(it) {
  const open = () => { rememberScroll(it.employer_id); go(`#/bu/${it.employer_id}`); };
  const link = h("a", { href: `#/bu/${it.employer_id}`, class: "bu-name", onclick: (e) => { e.preventDefault(); open(); } }, it.name);
  const tr = h("tr", { dataset: { id: it.employer_id }, onclick: (e) => { if (e.target.closest("a,button")) return; open(); } },
    h("td", { class: "rank num", "data-label": "Rank" }, it.rank),
    h("td", { class: "bu", "data-label": "BU & sektor" },
      link,
      h("span", { class: "muted small" }, it.sector),
      (it.sme_protection || it.verify_first) && h("span", { class: "chips" },
        it.sme_protection && h("span", { class: "chip info" }, icon("shield"), "Perlindungan UMKM padat karya"),
        it.verify_first && h("span", { class: "chip warn" }, icon("alert"), "Verifikasi data dulu"))),
    h("td", { "data-label": "Skor" }, scoreBar(it.score)),
    h("td", { "data-label": "Confidence" }, confChip(it.confidence_bucket)),
    h("td", { class: "reasons", "data-label": "Alasan utama" },
      h("ul", { class: "reason-list" }, it.reasons.slice(0, 2).map((r) => h("li", { title: r.text }, r.text)))),
    h("td", { class: "rp", "data-label": "Rp indikatif" }, rpCell(it)),
    h("td", { "data-label": "Status" }, statusCell(it)));
  return tr;
}

function skeleton(n = 10) {
  return Array.from({ length: n }, () => h("tr", { class: "skeleton", "aria-hidden": "true" },
    Array.from({ length: 7 }, () => h("td", {}, h("span", { class: "sk" })))));
}

function table(body) {
  return h("div", { class: "table-wrap" },
    h("table", { class: "data queue" },
      h("caption", { class: "visually-hidden" }, "Antrean prioritas pemeriksaan, diurutkan dari skor tertinggi"),
      h("thead", {}, h("tr", {},
        ["Rank", "BU & sektor", "Skor", "Confidence", "Alasan utama", "Rp indikatif", "Status"].map((t) => h("th", { scope: "col" }, t)))),
      body));
}

export async function renderQueue(main) {
  clear(main);
  document.title = "Antrean · PayRay";
  const tbody = h("tbody", {});
  const more = h("button", { class: "btn btn-secondary", type: "button", hidden: true }, "10 berikutnya", icon("arrowRight"));
  const errorBox = h("div", { class: "notice error", hidden: true, role: "alert" });
  const count = h("span", { class: "muted small" });
  const head = h("div", { class: "page-head" },
    h("div", {}, h("h1", {}, "Antrean prioritas pemeriksaan"),
      h("p", { class: "muted" }, "Diurutkan dari skor tertinggi. Prioritas pemeriksaan, bukan tuduhan.")),
    MODE === "live" && h("a", { class: "btn btn-ghost", href: "/api/queue.csv", download: true }, icon("download"), h("span", {}, "Ekspor CSV")));
  main.append(head, errorBox, table(tbody), h("div", { class: "table-foot" }, count, more));

  const paint = () => {
    clear(tbody);
    tbody.append(...mem.items.map(row));
    more.hidden = !mem.cursor;
    count.textContent = mem.items.length ? `Menampilkan ${mem.items.length} BU teratas` : "";
  };
  const empty = () => {
    clear(tbody);
    tbody.append(h("tr", {}, h("td", { colspan: 7, class: "empty" },
      h("strong", {}, "Belum ada batch terpublikasi untuk cabang ini."),
      h("span", { class: "muted" }, "Antrean muncul setelah supervisor menjalankan dan memublikasikan rescore."))));
  };
  const fail = (e) => {
    errorBox.hidden = false;
    clear(errorBox).append(icon("alert"), h("span", {}, `Antrean gagal dimuat: ${e.message}`),
      h("button", { class: "btn btn-ghost", type: "button", onclick: () => renderQueue(main) }, "Coba lagi"));
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
    state.batch = { id: page.batch.id, periodLabel: period(page.batch.period), publishedLabel: wib(page.batch.published_at) };
    renderTopbar();
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
