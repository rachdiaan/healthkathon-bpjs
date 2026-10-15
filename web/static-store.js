// Mode statis GitHub Pages (FR-31, FR-32, BR-25): baca data/snapshot.json, inspeksi hanya di localStorage.
// Tidak ada request ke /api. Semua jalur api() dialihkan ke handle() di sini.
import { ApiError } from "./api.js";
import { h } from "./dom.js";
import { toast } from "./app.js";

const KEY = "payray.static.inspections";
let snapPromise = null;

export function loadSnapshot() {
  if (!snapPromise) {
    snapPromise = fetch("data/snapshot.json", { cache: "no-cache" }).then(async (r) => {
      if (!r.ok) throw new Error(`snapshot.json tidak bisa dimuat (HTTP ${r.status})`);
      const s = await r.json();
      // BUG-7: tanpa generated_at atau batch.period, data bisa dikira terbaru. Tolak render.
      if (!s.generated_at || !s.batch?.period) throw new Error("Snapshot tidak lengkap: generated_at atau batch.period hilang. Data tidak ditampilkan.");
      return s;
    });
  }
  return snapPromise;
}

function readAll() {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
function writeAll(list) {
  try { localStorage.setItem(KEY, JSON.stringify(list)); } catch { toast("Penyimpanan browser tidak tersedia."); }
}

export function localInspections() {
  return readAll().map((it) => ({ ...it, can_correct: it.status === "submitted" && Date.now() - Date.parse(it.created_at) <= 7 * 864e5 }));
}

function inspectedIds(period) {
  return new Set(readAll().filter((i) => i.status === "submitted" && i.period === period).map((i) => i.employer_id));
}

function wibMonth() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit" }).format(new Date());
}

function saveInspection(body, supersedeId) {
  const s = window.__payraySnap;
  const list = readAll();
  const period = body.inspected_on.slice(0, 7);
  const clash = list.find((i) => i.employer_id === body.employer_id && i.period === period && i.status === "submitted" && i.id !== supersedeId);
  if (clash) throw new ApiError(409, { error: { code: "already_inspected_this_period", message: "BU ini sudah diperiksa periode ini." } });
  const item = s.items.find((x) => x.employer_id === body.employer_id);
  if (supersedeId) {
    const old = list.find((i) => i.id === supersedeId);
    if (old) old.status = "superseded";
  }
  const rec = {
    id: Date.now(), employer_id: body.employer_id, employer_name: item?.name || `BU ${body.employer_id}`,
    rank_at_selection: item?.rank ?? 0, inspected_on: body.inspected_on, period, status: "submitted",
    supersedes_id: supersedeId || null, cancel_reason: null, created_at: new Date().toISOString(),
    outcome: body.outcome, violation_types: body.violation_types, rp_found: body.rp_found, notes: body.notes,
  };
  list.unshift(rec);
  writeAll(list);
  return { id: rec.id, status: "submitted", period };
}

export async function handle(path, { method = "GET", body } = {}) {
  const s = await loadSnapshot();
  window.__payraySnap = s;
  const url = new URL(path, "https://static.invalid");
  const p = url.pathname;
  if (p === "/me") return { id: 0, username: "pengunjung", role: "officer", branch_id: s.branch.id, branch_name: s.branch.name };
  if (p === "/queue") {
    const limit = Number(url.searchParams.get("limit") || 10);
    const after = url.searchParams.get("cursor") ? Number(atob(url.searchParams.get("cursor"))) : 0;
    const done = inspectedIds(wibMonth());
    const items = s.items.filter((i) => i.rank > after).slice(0, limit)
      .map((i) => ({ ...i, inspection_status: done.has(i.employer_id) ? "submitted" : "none" }));
    const last = items[items.length - 1];
    const more = last && s.items.some((i) => i.rank > last.rank);
    return { batch: { id: s.batch.id, period: s.batch.period, published_at: s.batch.published_at },
      items, next_cursor: more ? btoa(String(last.rank)) : null };
  }
  const sheet = p.match(/^\/employers\/(\d+)\/scan-sheet$/);
  if (sheet) {
    const d = s.details[sheet[1]];
    if (!d) throw new ApiError(404, { error: { message: `Mode statis hanya memuat detail ${s.detail_top} BU teratas. Buka versi live untuk BU ini.` } });
    return { ...d, inspection_status: inspectedIds(wibMonth()).has(d.employer.id) ? "submitted" : "none" };
  }
  if (p === "/inspections" && method === "POST") return saveInspection(body);
  const sup = p.match(/^\/inspections\/(\d+)\/supersede$/);
  if (sup && method === "POST") return saveInspection(body, Number(sup[1]));
  if (p === "/inspections/mine") return { items: localInspections() };
  if (p === "/auth/logout") return { ok: true };
  throw new ApiError(404, { error: { message: "Fitur ini hanya ada di versi live." } });
}

// CSV inspeksi lokal (fungsi lama dashboard dipertahankan), dengan sanitasi formula yang sama dengan server.
function csvCell(v) {
  let s = v === null || v === undefined ? "" : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function exportCsv() {
  const cols = ["id", "employer_id", "employer_name", "rank_at_selection", "inspected_on", "period", "status",
    "supersedes_id", "outcome", "violation_types", "rp_found", "notes", "created_at"];
  const rows = readAll().map((r) => cols.map((c) => csvCell(Array.isArray(r[c]) ? r[c].join("|") : r[c])).join(","));
  const blob = new Blob([[cols.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = h("a", { href: URL.createObjectURL(blob), download: `inspeksi-lokal-${new Date().toISOString().slice(0, 10)}.csv` });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

export function staticHistoryActions(rerender) {
  return [
    h("button", { class: "btn btn-ghost", type: "button", onclick: exportCsv }, "Ekspor CSV"),
    h("button", { class: "btn btn-danger", type: "button", onclick: () => {
      if (!window.confirm("Hapus semua data inspeksi yang tersimpan di browser ini?")) return;
      try { localStorage.removeItem(KEY); localStorage.removeItem("payray.inspection.copy"); } catch { /* abaikan */ }
      toast("Data lokal dihapus");
      rerender();
    } }, "Hapus data lokal"),
  ];
}

const WIB_FMT = new Intl.DateTimeFormat("id-ID", { timeZone: "Asia/Jakarta", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
const MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];

export function bannerText(s) {
  const [y, m] = s.batch.period.split("-");
  return `Mode statis: data batch ${MONTHS[Number(m) - 1]} ${y}, dibuat ${WIB_FMT.format(new Date(s.generated_at))} WIB. Form inspeksi tersimpan lokal, bukan ke server.`;
}
