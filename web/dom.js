// Pembuat elemen lewat createElement (GR-14). Data selalu masuk lewat textContent.
// style hanya lewat objek (CSSOM), karena CSP style-src 'self' memblokir atribut style.
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v === null || v === undefined) continue;
    if (k === "class") el.className = v;
    else if (k === "style") Object.assign(el.style, v);
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
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

// Ikon garis 24px, stroke 1.8. Tiap entri: daftar [tag, atribut].
const P = (d) => ["path", { d }];
const ICONS = {
  grid: [["rect", { x: 3, y: 3, width: 7, height: 7, rx: 1.5 }], ["rect", { x: 14, y: 3, width: 7, height: 7, rx: 1.5 }], ["rect", { x: 3, y: 14, width: 7, height: 7, rx: 1.5 }], ["rect", { x: 14, y: 14, width: 7, height: 7, rx: 1.5 }]],
  list: [P("M8 6h13M8 12h13M8 18h13"), ["circle", { cx: 3.5, cy: 6, r: 1 }], ["circle", { cx: 3.5, cy: 12, r: 1 }], ["circle", { cx: 3.5, cy: 18, r: 1 }]],
  chart: [P("M3 3v18h18"), P("M8 17V9M13 17V5M18 17v-6")],
  layers: [P("m12 3 9 5-9 5-9-5z"), P("m3 13 9 5 9-5")],
  target: [["circle", { cx: 12, cy: 12, r: 9 }], ["circle", { cx: 12, cy: 12, r: 5 }], ["circle", { cx: 12, cy: 12, r: 1 }]],
  clock: [["circle", { cx: 12, cy: 12, r: 9 }], P("M12 7v5l3 2")],
  route: [["circle", { cx: 6, cy: 19, r: 2.5 }], ["circle", { cx: 18, cy: 5, r: 2.5 }], P("M8.5 19H16a3.5 3.5 0 0 0 0-7H8a3.5 3.5 0 0 1 0-7h7.5")],
  coin: [["circle", { cx: 12, cy: 12, r: 9 }], P("M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.5 0-2.5.8-2.5 2s1 1.7 2.5 2 2.5.8 2.5 2-1 2-2.5 2c-1.1 0-2-.5-2.5-1.5M12 6.5V8M12 16v1.5")],
  users: [["circle", { cx: 9, cy: 8, r: 3.5 }], P("M2.5 20c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5c2 .7 3.5 2.6 3.5 5.5")],
  flag: [P("M5 21V4M5 4h11l-2 4 2 4H5")],
  scan: [P("M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"), P("M4 12h16"), P("M8 8.5h8M9 15.5h6")],
  shield: [P("M12 3 4.5 6v5.5c0 4.6 3.2 7.8 7.5 9.5 4.3-1.7 7.5-4.9 7.5-9.5V6z")],
  arrow: [P("M7 17 17 7M8 7h9v9")],
  sun: [["circle", { cx: 12, cy: 12, r: 4 }], P("M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4")],
  moon: [P("M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z")],
  alert: [P("M12 3 2 20h20z"), P("M12 10v4M12 17v.5")],
  info: [["circle", { cx: 12, cy: 12, r: 9 }], P("M12 11v5M12 8v.5")],
  back: [P("m15 18-6-6 6-6")],
  right: [P("m9 6 6 6-6 6")],
  check: [P("M4.5 12.5 9.5 17.5 19.5 6.5")],
  download: [P("M12 3v12"), P("m7 10 5 5 5-5"), P("M4 20h16")],
  logout: [P("M9 4H5v16h4"), P("m15 8 4 4-4 4"), P("M19 12H9")],
  clipboard: [["rect", { x: 8, y: 3, width: 8, height: 4, rx: 1 }], P("M8 5H5v16h14V5h-3"), P("M8 12h8M8 16h5")],
};

export function icon(name, size = 20, label) {
  const el = svg("svg", { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
    "stroke-width": 1.8, "stroke-linecap": "round", "stroke-linejoin": "round",
    ...(label ? { role: "img", "aria-label": label } : { "aria-hidden": "true" }) });
  for (const [tag, a] of ICONS[name] || []) el.append(svg(tag, a));
  return el;
}
