// Pembuat elemen lewat createElement (GR-14). Data selalu masuk lewat textContent.
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v === null || v === undefined) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(el.dataset, v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

const SVG = "http://www.w3.org/2000/svg";
export function svg(tag, attrs = {}, ...children) {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  for (const c of children.flat()) if (c) el.append(c);
  return el;
}

// Ikon garis 16px, stroke 1.5, inline SVG (tanpa emoji, tanpa icon font).
const ICONS = {
  arrowLeft: ["M10 3 5 8l5 5", "M5 8h8"],
  arrowRight: ["M6 3l5 5-5 5"],
  check: ["M3 8.5 6.5 12 13 4.5"],
  shield: ["M8 1.8 2.8 3.8v4c0 3.2 2.2 5.4 5.2 6.4 3-1 5.2-3.2 5.2-6.4v-4z"],
  info: ["M8 14.2A6.2 6.2 0 1 0 8 1.8a6.2 6.2 0 0 0 0 12.4z", "M8 7.2v4", "M8 4.8v.1"],
  download: ["M8 2v8", "M4.5 6.8 8 10.3l3.5-3.5", "M2.5 13.5h11"],
  logout: ["M6 2.5H3v11h3", "M10.5 5 13.5 8l-3 3", "M13.5 8H6"],
  clipboard: ["M5.5 2.5h5v2h-5z", "M4 3.5H3v10h10v-10h-1", "M5.5 8h5", "M5.5 10.5h3"],
  alert: ["M8 2 1.8 13h12.4z", "M8 6.5v3", "M8 11.2v.1"],
};
export function icon(name, label) {
  const el = svg("svg", { width: 16, height: 16, viewBox: "0 0 16 16", fill: "none", stroke: "currentColor",
    "stroke-width": 1.5, "stroke-linecap": "round", "stroke-linejoin": "round", class: "icon",
    ...(label ? { role: "img", "aria-label": label } : { "aria-hidden": "true" }) });
  for (const d of ICONS[name] || []) el.append(svg("path", { d }));
  return el;
}
