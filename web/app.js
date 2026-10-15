// PayRay frontend: router hash sederhana. Tanpa framework, tanpa build step.
import { api, ApiError, MODE } from "./api.js";
import { h, clear, icon } from "./dom.js";
import { renderLogin } from "./login.js";
import { renderQueue, resetQueueMemory } from "./queue.js";

const main = document.getElementById("main");
const topbar = document.getElementById("topbar");
export const state = { me: null, batch: null };

export function go(hash) {
  if (location.hash === hash) route();
  else location.hash = hash;
}

export function toast(text) {
  const el = document.getElementById("toast");
  el.textContent = text;
  el.classList.add("show");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.remove("show"), 3200);
}

function navLink(href, label) {
  const here = (location.hash || "#/antrean").startsWith(href);
  return h("a", { href, class: here ? "active" : null, "aria-current": here ? "page" : null }, label);
}

export function renderTopbar() {
  const { me, batch } = state;
  clear(topbar);
  topbar.hidden = !me;
  if (!me) return;
  topbar.append(
    h("a", { class: "brand", href: "#/antrean", "aria-label": "PayRay, ke antrean" }, h("span", { class: "brand-mark", "aria-hidden": "true" }), "PayRay"),
    h("div", { class: "batch-meta" },
      batch ? [h("span", {}, "Batch ", h("strong", {}, batch.periodLabel)), h("span", { class: "muted" }, `dipublikasikan ${batch.publishedLabel}`)]
        : h("span", { class: "muted" }, "Belum ada batch terpublikasi")),
    h("nav", { class: "nav", "aria-label": "Menu utama" },
      navLink("#/antrean", "Antrean"),
      me.role === "officer" && navLink("#/riwayat", "Riwayat Saya"),
      me.role === "supervisor" && navLink("#/supervisor", "Dasbor Supervisor")),
    h("span", { class: `chip chip-mode ${MODE}` }, MODE === "live" ? "Live" : "Statis"),
    h("div", { class: "user" },
      h("span", { class: "user-name" }, me.username, h("span", { class: "muted" }, ` · ${me.role === "officer" ? "Petugas" : "Supervisor"} · ${me.branch_name}`)),
      MODE === "live" && h("button", { class: "btn btn-ghost", type: "button", onclick: logout }, icon("logout"), h("span", {}, "Keluar"))),
  );
}

async function logout() {
  try { await api("/auth/logout", { method: "POST" }); } catch { /* sesi sudah habis */ }
  state.me = null;
  state.batch = null;
  resetQueueMemory();
  renderTopbar();
  go("#/login");
}

async function ensureMe() {
  if (state.me) return state.me;
  try {
    state.me = await api("/me");
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
  return state.me;
}

let staticReady = null;
async function staticBoot() {
  const store = await import("./static-store.js");
  const banner = document.getElementById("banner");
  try {
    const s = await store.loadSnapshot();
    clear(banner).append(h("div", { class: "static-banner", role: "note" },
      icon("info"), h("span", {}, store.bannerText(s)),
      s.live_url && h("a", { href: s.live_url, rel: "noopener" }, "Buka versi live")));
    return true;
  } catch (e) {
    clear(main).append(h("div", { class: "notice error", role: "alert" }, icon("alert"), h("span", {}, e.message)));
    return false;
  }
}

async function route() {
  if (MODE === "static") {
    staticReady = staticReady || staticBoot();
    if (!(await staticReady)) return;
    if (location.hash === "#/login") return go("#/antrean");
  }
  let hash = location.hash || "#/";
  const me = hash === "#/login" ? null : await ensureMe().catch(() => null);
  if (!me && hash !== "#/login") return go("#/login");
  if (me && (hash === "#/" || hash === "#")) {
    hash = me.role === "supervisor" ? "#/supervisor" : "#/antrean";
    history.replaceState(null, "", hash);
  }
  renderTopbar();
  main.focus({ preventScroll: true });
  if (hash === "#/login") return renderLogin(main);
  if (hash === "#/riwayat") {
    const { renderHistory } = await import("./history.js");
    return renderHistory(main);
  }
  if (hash === "#/supervisor" && me.role === "supervisor") {
    const { renderSupervisor } = await import("./supervisor.js");
    return renderSupervisor(main);
  }
  const bu = hash.match(/^#\/bu\/(\d+)$/);
  if (bu) {
    const { renderScanSheet } = await import("./scan-sheet.js");
    return renderScanSheet(main, Number(bu[1]));
  }
  return renderQueue(main);
}

window.addEventListener("hashchange", route);
route();
