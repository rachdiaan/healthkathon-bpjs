// Form hasil inspeksi (Alur B). Drawer kanan ≥ 1024 px, layar penuh < 1024 px.
// Idempotency-Key dibuat sekali per form; tombol Simpan terkunci sampai ada respons (BUG-3).
import { api, ApiError, MODE } from "./api.js";
import { h, icon } from "./dom.js";
import { go, toast } from "./app.js";
import { markInspected } from "./queue.js";

const OUTCOMES = [
  ["violation_found", "Ditemukan indikasi ketidakpatuhan"],
  ["no_violation", "Tidak ditemukan"],
  ["inconclusive", "Tidak dapat disimpulkan"],
];
const TYPES = [
  ["under_reported_wage", "Upah dilaporkan lebih rendah"],
  ["partial_registration", "Pekerja didaftarkan sebagian"],
  ["ppu_to_pbpu_shift", "Pekerja dipindah PPU ke PBPU"],
  ["other", "Lainnya"],
];
const DRAFT_KEY = "payray.inspection.copy";

export function todayWib() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
}

function shiftDate(iso, days) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

// Salinan isian di browser petugas sendiri, dipakai mengisi ulang form koreksi
// (role officer tidak bisa membaca outcome di server).
export function saveCopy(id, body) {
  try {
    const all = JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}");
    all[id] = body;
    localStorage.setItem(DRAFT_KEY, JSON.stringify(all));
  } catch { /* storage tidak tersedia */ }
}
export function loadCopy(id) {
  try { return JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}")[id] || null; } catch { return null; }
}

/**
 * opts: { employer: {id, name}, rank, supersedeId?, initial?, onSaved?(result) }
 * Di mode statis api() menyimpan ke localStorage (BR-25).
 */
export function openForm(opts, returnFocus) {
  const key = crypto.randomUUID();
  const init = opts.initial || {};
  const today = todayWib();
  const live = h("div", { class: "visually-hidden", "aria-live": "polite", id: "form-live" });
  const errs = {};
  const errEl = (name) => (errs[name] = h("p", { class: "form-error", id: `err-${name}` }));

  const date = h("input", { type: "date", id: "f-date", name: "inspected_on", value: init.inspected_on || today,
    max: today, min: shiftDate(today, -30), required: true, "aria-describedby": "err-inspected_on" });
  const outcomeGroup = h("fieldset", { class: "field", "aria-describedby": "err-outcome" },
    h("legend", {}, "Hasil pemeriksaan"),
    OUTCOMES.map(([v, label]) => h("label", { class: "radio" },
      h("input", { type: "radio", name: "outcome", value: v, checked: init.outcome === v }), h("span", {}, label))),
    errEl("outcome"));
  const typeBoxes = TYPES.map(([v, label]) => h("label", { class: "radio" },
    h("input", { type: "checkbox", name: "violation_types", value: v, checked: (init.violation_types || []).includes(v) }),
    h("span", {}, label)));
  const typeGroup = h("fieldset", { class: "field", "aria-describedby": "err-violation_types" },
    h("legend", {}, "Jenis temuan"), h("p", { class: "hint" }, "Wajib bila ditemukan indikasi ketidakpatuhan."),
    typeBoxes, errEl("violation_types"));
  const rp = h("input", { type: "number", id: "f-rp", name: "rp_found", min: 0, max: 1000000000000, step: 1000,
    inputmode: "numeric", value: init.rp_found ?? "", "aria-describedby": "hint-rp err-rp_found" });
  const notes = h("textarea", { id: "f-notes", name: "notes", rows: 4, maxlength: 1000, "aria-describedby": "count-notes err-notes" });
  notes.value = init.notes || "";
  const count = h("p", { class: "hint", id: "count-notes" });
  const updateCount = () => { count.textContent = `${notes.value.length}/1.000 karakter`; };
  notes.addEventListener("input", updateCount);
  updateCount();

  const syncTypes = () => {
    const vf = outcomeGroup.querySelector("input:checked")?.value === "violation_found";
    for (const box of typeGroup.querySelectorAll("input")) {
      box.disabled = !vf;
      if (!vf) box.checked = false;
    }
    rp.disabled = !vf;
    if (!vf) rp.value = "";
    typeGroup.classList.toggle("is-disabled", !vf);
  };
  outcomeGroup.addEventListener("change", syncTypes);

  const save = h("button", { class: "btn btn-primary", type: "submit" }, "Simpan");
  const cancel = h("button", { class: "btn btn-ghost", type: "button" }, "Batal");
  const formError = h("p", { class: "form-error", role: "alert" });
  const form = h("form", { class: "inspection-form", novalidate: true },
    h("div", { class: "field" }, h("label", { for: "f-date" }, "Tanggal pemeriksaan"), date,
      h("p", { class: "hint" }, "Hari ini atau maksimal 30 hari ke belakang (WIB)."), errEl("inspected_on")),
    outcomeGroup, typeGroup,
    h("div", { class: "field" }, h("label", { for: "f-rp" }, "Rp temuan (opsional)"), rp,
      h("p", { class: "hint", id: "hint-rp" }, "Isi bila ada angka temuan. Bukan tagihan."), errEl("rp_found")),
    h("div", { class: "field" }, h("label", { for: "f-notes" }, "Catatan (opsional)"), notes, count, errEl("notes")),
    formError,
    h("div", { class: "form-actions" }, save, cancel));

  const title = opts.supersedeId ? "Koreksi hasil inspeksi" : "Catat hasil inspeksi";
  const panel = h("div", { class: "drawer", role: "dialog", "aria-modal": "true", "aria-labelledby": "drawer-title" },
    h("div", { class: "drawer-head" },
      h("div", {}, h("h2", { id: "drawer-title" }, title),
        h("p", { class: "muted small" }, `#${opts.rank} · ${opts.employer.name}`)),
      h("button", { class: "btn btn-ghost", type: "button", "aria-label": "Tutup form", onclick: () => close() }, "Tutup")),
    opts.supersedeId && !opts.initial && h("p", { class: "notice" }, icon("info"),
      h("span", {}, "Isian lama tidak tersimpan di browser ini. Isi ulang semua field; versi lama tetap tercatat.")),
    form, live);
  const backdrop = h("div", { class: "drawer-backdrop", onclick: () => close() });
  const root = h("div", { class: "drawer-root" }, backdrop, panel);
  document.body.append(root);
  document.body.classList.add("drawer-open");
  syncTypes();

  function close() {
    document.removeEventListener("keydown", onKey, true);
    root.remove();
    document.body.classList.remove("drawer-open");
    returnFocus?.focus();
  }
  function onKey(e) {
    if (e.key === "Escape") { e.stopPropagation(); close(); return; }
    if (e.key === "Tab") { // fokus tetap di dalam dialog
      const f = [...panel.querySelectorAll("button, input:not([disabled]), textarea, select, [href]")];
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
      else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
    }
  }
  document.addEventListener("keydown", onKey, true);
  cancel.addEventListener("click", close);
  date.focus();

  function showErrors(fields, message) {
    for (const [k, el] of Object.entries(errs)) { el.textContent = ""; form.querySelector(`[name="${k}"]`)?.removeAttribute("aria-invalid"); }
    const lines = [];
    for (const [k, msg] of Object.entries(fields || {})) {
      const target = errs[k] || formError;
      target.textContent = msg;
      form.querySelector(`[name="${k}"]`)?.setAttribute("aria-invalid", "true");
      lines.push(msg);
    }
    if (!lines.length && message) { formError.textContent = message; lines.push(message); }
    live.textContent = `Periksa isian: ${lines.join(". ")}`;
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (save.disabled) return;
    const outcome = outcomeGroup.querySelector("input:checked")?.value;
    const types = [...typeGroup.querySelectorAll("input:checked")].map((b) => b.value);
    const local = {};
    if (!outcome) local.outcome = "Pilih hasil pemeriksaan.";
    if (outcome === "violation_found" && !types.length) local.violation_types = "Pilih minimal satu jenis temuan.";
    if (!date.value) local.inspected_on = "Isi tanggal pemeriksaan.";
    else if (date.value > today) local.inspected_on = "Tanggal tidak boleh setelah hari ini.";
    if (Object.keys(local).length) { showErrors(local); return; }
    const body = {
      employer_id: opts.employer.id, inspected_on: date.value, outcome,
      violation_types: outcome === "violation_found" ? types : [],
      rp_found: outcome === "violation_found" && rp.value !== "" ? Number(rp.value) : null,
      notes: notes.value.trim() || null,
    };
    save.disabled = true;
    save.textContent = "Menyimpan...";
    try {
      const path = opts.supersedeId ? `/inspections/${opts.supersedeId}/supersede` : "/inspections";
      const result = await api(path, { method: "POST", body, headers: { "Idempotency-Key": key } });
      if (MODE === "live") saveCopy(result.id, body);
      close();
      toast("Tersimpan");
      markInspected(opts.employer.id);
      opts.onSaved?.(result);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        close();
        toast(e.code === "already_inspected_this_period" ? "BU ini sudah diperiksa periode ini." : e.message);
        markInspected(opts.employer.id);
        return;
      }
      if (e instanceof ApiError && e.status === 422) {
        const fields = {};
        for (const [k, v] of Object.entries(e.fields || {})) fields[k === "_" ? "form" : k] = v;
        showErrors(fields, e.message);
      } else {
        showErrors({}, e instanceof ApiError ? e.message : "Gagal menyimpan. Periksa koneksi lalu coba lagi.");
      }
      save.disabled = false;
      save.textContent = "Simpan";
    }
  });
  return { close };
}

// Dipanggil dari Scan Sheet.
export function openInspectionForm(d, returnFocus) {
  openForm({
    employer: d.employer, rank: d.rank,
    onSaved: () => go("#/antrean"),
  }, returnFocus);
}

