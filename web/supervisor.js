// Dasbor Supervisor (Alur C): metrik tim, batch rescore + publish, audit log.
import { api } from "./api.js";
import { h, clear, icon } from "./dom.js";
import { toast } from "./app.js";
import { wib, period as periodLabel } from "./format.js";
import { resetQueueMemory } from "./queue.js";

const POLL_MS = 3000;
const POLL_MAX_MS = 5 * 60 * 1000;
const STATUS = { running: "Berjalan", ready: "Siap", published: "Dipublikasikan", failed: "Gagal", archived: "Diarsipkan" };
const ACTIONS = ["", "auth.login", "auth.login_failed", "auth.logout", "scan_sheet.view", "inspection.submit",
  "inspection.supersede", "inspection.cancel", "inspection.list", "batch.create", "batch.publish",
  "export.queue_csv", "audit.read", "authz.denied"];
const ui = { tab: "batch", period: null, poll: null };

function months(n = 6) {
  const now = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit" }).format(new Date());
  let [y, m] = now.split("-").map(Number);
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push(`${y}-${String(m).padStart(2, "0")}`);
    m -= 1;
    if (m === 0) { m = 12; y -= 1; }
  }
  return out;
}

const pct = (v) => `${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;

function card(label, value, foot, opts = {}) {
  return h("div", { class: `metric${opts.muted ? " is-muted" : ""}` },
    h("span", { class: "k" }, label),
    h("span", { class: "metric-v num" }, value),
    h("span", { class: "muted small" }, foot));
}

function metricCards(m) {
  const enough = !m.insufficient;
  const nText = `n = ${m.n_decided} keputusan · ${m.n_inconclusive} tidak dapat disimpulkan`;
  return [
    card("Hit rate", enough ? pct(m.hit_rate) : "Data belum cukup (n < 10)", nText, { muted: !enough }),
    card(m.baseline_label, m.baseline !== null ? pct(m.baseline) : "Belum dihitung",
      m.computed_at ? `dihitung ${wib(m.computed_at)}` : "jalankan compute_baseline.py"),
    card("Lift", enough ? (m.lift !== null ? `${m.lift.toLocaleString("id-ID")}×` : "n/a") : "Data belum cukup (n < 10)",
      "hit rate ÷ baseline acak", { muted: !enough }),
    card("Coverage top-10", pct(m.coverage_top10), "BU rank 1–10 batch aktif yang sudah diperiksa periode ini"),
  ];
}

async function renderMetrics(box, p) {
  clear(box).append(...Array.from({ length: 4 }, () => h("div", { class: "metric" }, h("span", { class: "sk" }), h("span", { class: "sk sk-title" }))));
  try {
    const m = await api(`/metrics?period=${p}`);
    clear(box).append(...metricCards(m));
  } catch (e) {
    clear(box).append(h("div", { class: "notice error", role: "alert" }, icon("alert"), h("span", {}, `Metrik gagal dimuat: ${e.message}`)));
  }
}

function confirmPublish(b) {
  return new Promise((resolve) => {
    const ok = h("button", { class: "btn btn-primary", type: "button" }, "Publikasikan");
    const no = h("button", { class: "btn btn-ghost", type: "button" }, "Batal");
    const dlg = h("dialog", { class: "confirm", "aria-labelledby": "confirm-title", "aria-describedby": "confirm-desc" },
      h("h2", { id: "confirm-title" }, "Publikasikan batch?"),
      h("p", { id: "confirm-desc" }, `Antrean semua petugas cabang ini akan diganti dengan batch ${periodLabel(b.period)}. Batch lama diarsipkan.`),
      h("div", { class: "form-actions" }, ok, no));
    document.body.append(dlg);
    const done = (v) => { dlg.close(); dlg.remove(); resolve(v); };
    ok.addEventListener("click", () => done(true));
    no.addEventListener("click", () => done(false));
    dlg.addEventListener("cancel", (e) => { e.preventDefault(); done(false); });
    dlg.showModal();
    no.focus();
  });
}

async function renderBatches(panel, refreshMetrics) {
  clear(panel);
  const sel = h("select", { id: "rescore-period" }, months().map((p) => h("option", { value: p }, periodLabel(p))));
  const run = h("button", { class: "btn btn-primary", type: "button" }, "Jalankan rescore");
  const status = h("div", { class: "batch-status", "aria-live": "polite" });
  const tbody = h("tbody", {});
  panel.append(
    h("div", { class: "toolbar" },
      h("div", { class: "field inline" }, h("label", { for: "rescore-period" }, "Periode"), sel), run),
    status,
    h("div", { class: "table-wrap" }, h("table", { class: "data" },
      h("caption", { class: "visually-hidden" }, "Daftar batch rescore cabang"),
      h("thead", {}, h("tr", {}, ["ID", "Periode", "Status", "BU diskor", "Dibuat", "Selesai / publikasi", "Aksi"].map((t) => h("th", { scope: "col" }, t)))),
      tbody)));

  const load = async () => {
    const { items } = await api("/rescore-batches");
    clear(tbody);
    if (!items.length) tbody.append(h("tr", {}, h("td", { colspan: 7, class: "empty" }, "Belum ada batch.")));
    for (const b of items) {
      const action = b.status === "ready" ? h("button", { class: "btn btn-secondary", type: "button", onclick: () => publish(b) }, "Publikasikan") : null;
      tbody.append(h("tr", {},
        h("td", { class: "num" }, b.id), h("td", {}, periodLabel(b.period)),
        h("td", {}, h("span", { class: `badge s-${b.status}` }, STATUS[b.status] || b.status),
          b.error && h("span", { class: "muted small block" }, b.error)),
        h("td", { class: "num" }, b.n_scored?.toLocaleString("id-ID") ?? "-"),
        h("td", {}, wib(b.created_at)), h("td", {}, wib(b.published_at || b.finished_at)),
        h("td", {}, action || h("span", { class: "muted small" }, "-"))));
    }
  };

  async function publish(b) {
    if (!(await confirmPublish(b))) return;
    try {
      await api(`/rescore-batches/${b.id}/publish`, { method: "POST" });
      toast(`Batch ${periodLabel(b.period)} dipublikasikan`);
      resetQueueMemory();
      clear(status);
      await load();
      refreshMetrics();
    } catch (e) { toast(e.message); }
  }

  function showSummary(b) {
    const s = b.summary || {};
    clear(status).append(h("div", { class: "notice" }, icon("check"),
      h("span", {}, `Batch ${periodLabel(b.period)} siap: ${b.n_scored.toLocaleString("id-ID")} BU diskor`,
        s.new_in_top10 !== null && s.new_in_top10 !== undefined ? `, ${s.new_in_top10} BU baru masuk 10 teratas dibanding batch aktif.` : "."),
      h("button", { class: "btn btn-primary", type: "button", onclick: () => publish(b) }, "Publikasikan")));
  }

  // Polling tiap 3 detik, berhenti saat ready/failed atau 5 menit (Alur C).
  function poll(id) {
    clearInterval(ui.poll);
    const t0 = Date.now();
    ui.poll = setInterval(async () => {
      if (Date.now() - t0 > POLL_MAX_MS) {
        clearInterval(ui.poll);
        clear(status).append(h("div", { class: "notice error" }, icon("alert"), h("span", {}, "Rescore belum selesai setelah 5 menit. Muat ulang daftar batch nanti.")));
        return;
      }
      try {
        const b = await api(`/rescore-batches/${id}`);
        if (b.status === "running") return;
        clearInterval(ui.poll);
        await load();
        if (b.status === "ready") showSummary(b);
        else clear(status).append(h("div", { class: "notice error" }, icon("alert"), h("span", {}, `Rescore gagal: ${b.error || "tanpa pesan"}`)));
      } catch { /* coba lagi di putaran berikutnya */ }
    }, POLL_MS);
  }

  run.addEventListener("click", async () => {
    run.disabled = true;
    try {
      const b = await api("/rescore-batches", { method: "POST", body: { period: sel.value } });
      clear(status).append(h("div", { class: "notice" }, h("span", { class: "spinner-dot", "aria-hidden": "true" }), h("span", {}, `Batch #${b.id} berjalan. Status diperbarui tiap 3 detik.`)));
      await load();
      poll(b.id);
    } catch (e) {
      clear(status).append(h("div", { class: "notice error", role: "alert" }, icon("alert"), h("span", {}, e.message)));
    } finally { run.disabled = false; }
  });
  try { await load(); } catch (e) { clear(tbody).append(h("tr", {}, h("td", { colspan: 7, class: "empty" }, e.message))); }
}

async function renderAudit(panel) {
  clear(panel);
  const action = h("select", { id: "f-action" }, ACTIONS.map((a) => h("option", { value: a }, a || "Semua aksi")));
  const actor = h("input", { id: "f-actor", type: "number", min: 1, inputmode: "numeric", placeholder: "ID" });
  const from = h("input", { id: "f-from", type: "date" });
  const to = h("input", { id: "f-to", type: "date" });
  const tbody = h("tbody", {});
  const more = h("button", { class: "btn btn-secondary", type: "button", hidden: true }, "Muat lebih lama");
  const form = h("form", { class: "toolbar wrap" },
    h("div", { class: "field inline" }, h("label", { for: "f-action" }, "Aksi"), action),
    h("div", { class: "field inline" }, h("label", { for: "f-actor" }, "ID pelaku"), actor),
    h("div", { class: "field inline" }, h("label", { for: "f-from" }, "Dari"), from),
    h("div", { class: "field inline" }, h("label", { for: "f-to" }, "Sampai"), to),
    h("button", { class: "btn btn-secondary", type: "submit" }, "Terapkan"));
  panel.append(form,
    h("div", { class: "scroll-x", tabindex: 0, role: "region", "aria-label": "Tabel audit log, geser ke samping" },
      h("table", { class: "data audit" },
        h("caption", { class: "visually-hidden" }, "Audit log cabang"),
        h("thead", {}, h("tr", {}, ["Waktu", "Pelaku", "Peran", "Aksi", "Objek", "Detail"].map((t) => h("th", { scope: "col" }, t)))),
        tbody)),
    h("div", { class: "table-foot" }, h("span", {}), more));
  let cursor = null;
  const params = () => {
    const q = new URLSearchParams({ limit: "50" });
    if (action.value) q.set("action", action.value);
    if (actor.value) q.set("actor_id", actor.value);
    if (from.value) q.set("from", from.value);
    if (to.value) q.set("to", to.value);
    if (cursor) q.set("cursor", cursor);
    return q;
  };
  const load = async (append) => {
    if (!append) { cursor = null; clear(tbody); }
    try {
      const r = await api(`/audit-events?${params()}`);
      for (const e of r.items) {
        tbody.append(h("tr", {},
          h("td", { class: "nw" }, wib(e.at)), h("td", {}, e.actor || "-"), h("td", {}, e.role || "-"),
          h("td", { class: "mono" }, e.action), h("td", {}, e.resource ? `${e.resource} ${e.resource_id ?? ""}` : "-"),
          h("td", { class: "mono small detail" }, e.detail ? JSON.stringify(e.detail) : "")));
      }
      if (!tbody.children.length) tbody.append(h("tr", {}, h("td", { colspan: 6, class: "empty" }, "Tidak ada event untuk filter ini.")));
      cursor = r.next_cursor;
      more.hidden = !cursor;
    } catch (e) { clear(tbody).append(h("tr", {}, h("td", { colspan: 6, class: "empty", role: "alert" }, e.message))); }
  };
  form.addEventListener("submit", (e) => { e.preventDefault(); load(false); });
  more.addEventListener("click", () => load(true));
  await load(false);
}

export async function renderSupervisor(main) {
  clear(main);
  clearInterval(ui.poll);
  window.addEventListener("hashchange", () => clearInterval(ui.poll), { once: true });
  document.title = "Dasbor Supervisor · PayRay";
  ui.period = ui.period || months()[0];
  const sel = h("select", { id: "metric-period" }, months().map((p) => h("option", { value: p, selected: p === ui.period }, periodLabel(p))));
  const cards = h("div", { class: "metrics" });
  const refresh = () => renderMetrics(cards, ui.period);
  sel.addEventListener("change", () => { ui.period = sel.value; refresh(); });

  const panel = h("div", { class: "tab-panel", role: "tabpanel", id: "tabpanel", tabindex: 0 });
  const tabs = [["batch", "Batch rescore"], ["audit", "Audit log"]];
  const tabBtns = tabs.map(([id, label]) => h("button", { class: "tab", type: "button", role: "tab", id: `tab-${id}`,
    "aria-controls": "tabpanel", "aria-selected": String(ui.tab === id), tabindex: ui.tab === id ? 0 : -1 }, label));
  const select = (id) => {
    ui.tab = id;
    tabBtns.forEach((b, i) => { const on = tabs[i][0] === id; b.setAttribute("aria-selected", String(on)); b.tabIndex = on ? 0 : -1; });
    panel.setAttribute("aria-labelledby", `tab-${id}`);
    if (id === "batch") renderBatches(panel, refresh); else renderAudit(panel);
  };
  tabBtns.forEach((b, i) => {
    b.addEventListener("click", () => select(tabs[i][0]));
    b.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const j = (i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
      tabBtns[j].focus();
      select(tabs[j][0]);
    });
  });

  main.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Dasbor Supervisor"), h("p", { class: "muted" }, "Hit rate tim dibanding pemilihan acak, batch rescore, dan jejak aktivitas cabang.")),
      h("div", { class: "field inline" }, h("label", { for: "metric-period" }, "Periode metrik"), sel)),
    cards,
    h("div", { class: "tabs", role: "tablist", "aria-label": "Bagian dasbor" }, tabBtns),
    panel);
  refresh();
  select(ui.tab);
}
