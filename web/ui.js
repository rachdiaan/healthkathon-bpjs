// Komponen konsol bersama: badge kepastian angka, kartu, KPI, catatan, drawer "asal angka".
import { h, clear, append, icon } from "./dom.js";

export const BL = { m: "● Data batch", d: "◐ Hasil hitungan", a: "○ Perkiraan" };
export const bd = (c, text) => h("span", { class: `b ${c}` }, text || BL[c]);

export const card = (title, body, actions) => h("section", { class: "cd" },
  h("div", { class: "ch" }, h("h3", {}, title), actions && h("div", { class: "acts" }, actions)), body);

// f = { t: judul, c: m|d|a, s: berdasarkan apa, h: cara menghitung, w: kapan meleset, u: yang boleh diputuskan }
export function kpi(label, value, c, caption, f, opts = {}) {
  return h("div", { class: `kp${opts.muted ? " muted" : ""}` },
    h("span", {}, label),
    f ? h("button", { class: "ar", type: "button", "aria-label": `Asal angka: ${label}`, onclick: (e) => openInfo(f, e.currentTarget) }, icon("arrow", 16)) : h("span"),
    h("strong", { class: opts.small ? "sm" : null }, value),
    h("div", {}, c && bd(c), caption));
}

export const insight = (tone, ic, title, text, link) => h("div", { class: "it" },
  h("div", { class: `ti ${tone}` }, icon(ic)),
  h("div", {}, h("b", {}, title), h("span", {}, text), link && h("a", { class: "lk", href: link[1] }, link[0])));

export const legend = () => h("p", { class: "fn legend" }, "Seberapa pasti angkanya:", bd("m"), bd("d"), bd("a"),
  "Klik panah atau baris untuk melihat asal angkanya.");

export const disclaimer = () => h("p", { class: "disc" }, icon("shield", 16),
  "Prioritas pemeriksaan, bukan tuduhan. Keputusan pemeriksaan dan sanksi tetap di tangan petugas.");

const dr = () => document.getElementById("dr");
let lastTrigger = null;

export function openInfo(f, trigger) {
  lastTrigger = trigger || null;
  const sec = (label, v) => v && [h("h4", {}, label), Array.isArray(v) ? h("ul", {}, v.map((x) => h("li", {}, x))) : h("p", {}, v)];
  const close = h("button", { class: "x", type: "button", "data-x": "" }, "Tutup");
  append(clear(dr()), [close, f.c && bd(f.c), h("h2", { id: "dr-title" }, f.t),
    sec(f.sl || "Berdasarkan apa", f.s), sec(f.hl || "Cara menghitung", f.h),
    sec(f.wl || "Kapan bisa meleset", f.w), sec(f.ul || "Yang boleh diputuskan dari angka ini", f.u), f.extra]);
  dr().setAttribute("aria-labelledby", "dr-title");
  dr().classList.add("on");
  close.focus({ preventScroll: true });
}

export function closeInfo() {
  if (!dr()?.classList.contains("on")) return false;
  dr().classList.remove("on");
  lastTrigger?.focus?.({ preventScroll: true });
  lastTrigger = null;
  return true;
}

document.addEventListener("click", (e) => {
  if (e.target.closest("[data-x]")) { closeInfo(); return; }
  if (!e.target.closest("#dr, .ar, [data-info]")) closeInfo();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && closeInfo()) e.stopImmediatePropagation();
}, true);

// Baris tabel yang bisa diklik dan difokus dengan keyboard.
export function clickRow(tr, fn) {
  tr.classList.add("click");
  tr.tabIndex = 0;
  tr.dataset.info = "";
  tr.addEventListener("click", (e) => { if (!e.target.closest("a,button,input")) fn(tr); });
  tr.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target === tr) fn(tr); });
  return tr;
}

// Tabel responsif: label kolom disalin ke data-l untuk tampilan kartu di layar sempit.
export function table(cols, body, caption) {
  const t = h("table", { class: "rsp" }, caption && h("caption", { class: "visually-hidden" }, caption),
    h("thead", {}, h("tr", {}, cols.map((c) => h("th", { scope: "col", class: c.startsWith("#") ? "num" : null }, c.replace(/^#/, ""))))), body);
  labelRows(t);
  return h("div", { class: "tw" }, t);
}
export function labelRows(t) {
  const table = t.tagName === "TABLE" ? t : t.closest("table");
  const heads = [...table.querySelectorAll("thead th")].map((c) => c.textContent);
  for (const r of table.querySelectorAll("tbody tr")) [...r.cells].forEach((c, i) => { if (heads[i]) c.dataset.l = heads[i]; });
}

export const pct = (v, d = 1) => v === null || v === undefined ? "-" : `${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: d })}%`;
export const num = (v, d = 0) => Number(v).toLocaleString("id-ID", { maximumFractionDigits: d });

// Batang horizontal (.hb). fill = kelas warna (f1/f2/f3/fa/fg).
export function hbar(label, value, max, valueText, fill, onclick) {
  const bar = h("i", { class: fill, style: { width: `${max > 0 ? Math.max(1, (value / max) * 100) : 1}%` } });
  return onclick
    ? h("button", { class: "hb", type: "button", "data-info": "", onclick }, h("span", {}, label), bar, h("b", {}, valueText))
    : h("div", { class: "hb" }, h("span", {}, label), bar, h("b", {}, valueText));
}
