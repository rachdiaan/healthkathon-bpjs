// PayRay frontend: shell konsol + router hash. Tanpa framework, tanpa build step.
import { api, ApiError, MODE } from "./api.js";
import { h, clear, icon } from "./dom.js";
import { bd, openInfo, closeInfo } from "./ui.js";
import { renderLogin } from "./login.js";
import { resetQueueMemory } from "./queue.js";
import { period, wib } from "./format.js";

const main = document.getElementById("main");
const topbar = document.getElementById("topbar");
const rail = document.getElementById("rail");
export const state = { me: null, batch: null };

// Tema: pilihan pengguna diingat per browser.
const THEME_KEY = "payray.theme";
try { const t = localStorage.getItem(THEME_KEY); if (t) document.documentElement.dataset.theme = t; } catch { /* abaikan */ }
const isDark = () => document.documentElement.dataset.theme === "dark"
  || (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => renderTopbar());
function setTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem(THEME_KEY, t); } catch { /* abaikan */ }
  renderTopbar();
}

// [hash, judul halaman, ikon, label rail, peran yang boleh]
const NAV = [
  ["#/ringkasan", "Ringkasan", "grid", "Ringkasan", null],
  ["#/antrean", "Antrean prioritas", "list", "Antrean", null],
  ["#/riwayat", "Riwayat saya", "clock", "Riwayat", "officer"],
  ["#/supervisor", "Dasbor supervisor", "chart", "Supervisor", "supervisor"],
  ["#/validasi", "Validasi model", "target", "Validasi", null],
  ["#/cara-kerja", "Cara kerja PayRay", "layers", "Cara kerja", null],
];

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

function greeting() {
  const hr = Number(new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Jakarta", hour: "numeric", hourCycle: "h23" }).format(new Date()));
  return hr < 11 ? "Selamat pagi" : hr < 15 ? "Selamat siang" : hr < 18 ? "Selamat sore" : "Selamat malam";
}

const current = () => {
  const hash = location.hash || "#/ringkasan";
  if (hash.startsWith("#/bu/")) return "#/antrean";
  return NAV.find((n) => hash.startsWith(n[0]))?.[0] || "#/ringkasan";
};

function titleFor(hash) {
  if (hash.startsWith("#/bu/")) return "Lembar hasil scan";
  return NAV.find((n) => hash.startsWith(n[0]))?.[1] || "Ringkasan";
}

function accountDrawer(btn) {
  const { me } = state;
  const role = me.role === "officer" ? "Petugas pemeriksa" : "Supervisor cabang";
  openInfo({
    t: me.username, sl: "Peran", s: role, hl: "Cabang", h: me.branch_name,
    wl: "Mode", w: MODE === "live" ? "Live: terhubung ke server PayRay." : "Statis: data snapshot, isian disimpan di browser ini.",
    ul: "Batch aktif", u: state.batch ? `${state.batch.periodLabel}, dipublikasikan ${state.batch.publishedLabel}` : "Belum dimuat",
    extra: MODE === "live" && h("div", { class: "form-actions" },
      h("button", { class: "btn dg", type: "button", onclick: logout }, icon("logout", 16), "Keluar")),
  }, btn);
}

export function renderTopbar() {
  const { me, batch } = state;
  clear(topbar);
  clear(rail);
  topbar.hidden = rail.hidden = !me;
  if (!me) return;
  const here = current();
  const hash = location.hash || "#/ringkasan";
  const dk = isDark();
  const initials = me.username.replace(/[^a-z0-9]/gi, " ").trim().split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase() || "P";
  topbar.append(
    h("a", { class: "lg", href: "#/ringkasan", "aria-label": "PayRay, ke ringkasan" }, icon("scan", 24)),
    h("div", {}, h("small", {}, here === "#/ringkasan" ? `${greeting()}, ${me.username}` : `PayRay · ${me.branch_name}`),
      h("h1", {}, titleFor(hash))),
    h("div", { class: "tr" },
      bd("d", "Data sintetis, bukan data peserta"),
      batch && h("span", { class: "b hide-sm" }, `Batch ${batch.periodLabel}`),
      h("span", { class: `b ${MODE === "live" ? "g" : "a"}` }, MODE === "live" ? "Live" : "Statis"),
      h("div", { class: "pill", role: "group", "aria-label": "Tema" },
        h("button", { type: "button", class: dk ? null : "on", "aria-label": "Tema terang", "aria-pressed": String(!dk), onclick: () => setTheme("light") }, icon("sun", 18)),
        h("button", { type: "button", class: dk ? "on" : null, "aria-label": "Tema gelap", "aria-pressed": String(dk), onclick: () => setTheme("dark") }, icon("moon", 18))),
      h("button", { class: "av", type: "button", "aria-label": `Akun ${me.username}`, "data-info": "", onclick: (e) => accountDrawer(e.currentTarget) }, initials)));
  for (const [href, title, ic, short, role] of NAV) {
    if (role && role !== me.role) continue;
    rail.append(h("a", { href, title, "aria-label": title, "aria-current": href === here ? "page" : null }, icon(ic), h("span", {}, short)));
  }
}

export function setBatch(b) {
  if (!b) return;
  const next = { id: b.id, periodLabel: period(b.period), publishedLabel: wib(b.published_at) };
  if (state.batch?.id === next.id) return;
  state.batch = next;
  renderTopbar();
}

async function logout() {
  try { await api("/auth/logout", { method: "POST" }); } catch { /* sesi sudah habis */ }
  closeInfo();
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
    clear(banner).append(h("div", { class: "banner", role: "note" },
      icon("info", 16), h("span", {}, store.bannerText(s)),
      s.live_url && h("a", { href: s.live_url, rel: "noopener" }, "Buka versi live")));
    return true;
  } catch (e) {
    clear(main).append(h("div", { class: "notice error", role: "alert" }, icon("alert"), h("span", {}, e.message)));
    return false;
  }
}

const PAGES = {
  "#/ringkasan": () => import("./summary.js").then((m) => m.renderSummary),
  "#/antrean": () => import("./queue.js").then((m) => m.renderQueue),
  "#/riwayat": () => import("./history.js").then((m) => m.renderHistory),
  "#/supervisor": () => import("./supervisor.js").then((m) => m.renderSupervisor),
  "#/validasi": () => import("./validation.js").then((m) => m.renderValidation),
  "#/cara-kerja": () => import("./method.js").then((m) => m.renderMethod),
};

async function route() {
  closeInfo();
  if (MODE === "static") {
    staticReady = staticReady || staticBoot();
    if (!(await staticReady)) return;
    if (location.hash === "#/login") return go("#/ringkasan");
  }
  let hash = location.hash || "#/";
  const me = hash === "#/login" ? null : await ensureMe().catch(() => null);
  if (!me && hash !== "#/login") return go("#/login");
  if (me && (hash === "#/" || hash === "#" || hash === "#/login")) {
    hash = "#/ringkasan";
    history.replaceState(null, "", hash);
  }
  renderTopbar();
  document.getElementById("banner").hidden = hash === "#/login";
  main.className = hash === "#/login" ? "" : "pg";
  main.focus({ preventScroll: true });
  if (hash === "#/login") return renderLogin(main);
  const bu = hash.match(/^#\/bu\/(\d+)$/);
  if (bu) {
    const { renderScanSheet } = await import("./scan-sheet.js");
    return renderScanSheet(main, Number(bu[1]));
  }
  let key = NAV.find((n) => hash.startsWith(n[0]))?.[0] || "#/ringkasan";
  const role = NAV.find((n) => n[0] === key)[4];
  if (role && role !== me.role) key = "#/ringkasan";
  const render = await PAGES[key]();
  return render(main);
}

window.addEventListener("hashchange", route);
route();
