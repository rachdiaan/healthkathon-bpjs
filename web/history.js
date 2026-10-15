// Riwayat Saya (Alur B langkah 6–7). Status tanpa outcome (FR-18); koreksi ≤ 7 hari (BR-11).
import { api, MODE } from "./api.js";
import { h, clear, icon } from "./dom.js";
import { toast } from "./app.js";
import { openForm, loadCopy } from "./inspection-form.js";

const STATUS = {
  submitted: ["Tersimpan", "done"],
  superseded: ["Dikoreksi (versi lama)", "muted"],
  cancelled: ["Dibatalkan supervisor", "warn"],
};

const showCorrections = { value: false };

function fmtDate(iso) {
  return new Date(`${iso}T00:00:00+07:00`).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta" });
}

export async function loadItems() {
  return (await api("/inspections/mine")).items;
}

export async function renderHistory(main) {
  clear(main);
  document.title = "Riwayat Saya · PayRay";
  const toggle = h("input", { type: "checkbox", id: "show-corr", checked: showCorrections.value });
  const tbody = h("tbody", {});
  const extra = h("div", { class: "actions" });
  main.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Riwayat Saya"),
        h("p", { class: "muted" }, "Inspeksi yang Anda catat. Hasil (outcome) tidak ditampilkan di sini; supervisor yang membacanya.")),
      h("div", { class: "actions" },
        h("label", { class: "radio", for: "show-corr" }, toggle, h("span", {}, "Tampilkan koreksi")), extra)),
    h("div", { class: "table-wrap" },
      h("table", { class: "data history" },
        h("caption", { class: "visually-hidden" }, "Riwayat inspeksi saya"),
        h("thead", {}, h("tr", {}, ["Tanggal", "BU", "Rank saat dipilih", "Status", "Aksi"].map((t) => h("th", { scope: "col" }, t)))),
        tbody)));

  let items = [];
  const paint = () => {
    clear(tbody);
    const visible = items.filter((it) => showCorrections.value || it.status !== "superseded");
    if (!visible.length) {
      tbody.append(h("tr", {}, h("td", { colspan: 5, class: "empty" },
        h("strong", {}, "Belum ada inspeksi tercatat."),
        h("span", { class: "muted" }, "Buka BU dari antrean, lalu pilih “Catat hasil inspeksi”."))));
      return;
    }
    for (const it of visible) {
      const [label, cls] = STATUS[it.status] || [it.status, ""];
      const actions = [];
      if (it.can_correct) {
        const btn = h("button", { class: "btn btn-ghost", type: "button" }, "Koreksi");
        btn.addEventListener("click", () => openForm({
          employer: { id: it.employer_id, name: it.employer_name }, rank: it.rank_at_selection,
          supersedeId: it.id,
          initial: MODE === "static" ? { inspected_on: it.inspected_on, outcome: it.outcome, violation_types: it.violation_types, rp_found: it.rp_found, notes: it.notes } : loadCopy(it.id),
          onSaved: () => { toast("Koreksi tersimpan"); renderHistory(main); },
        }, btn));
        actions.push(btn);
      }
      tbody.append(h("tr", {},
        h("td", { "data-label": "Tanggal" }, fmtDate(it.inspected_on)),
        h("td", { "data-label": "BU" }, h("a", { href: `#/bu/${it.employer_id}`, class: "bu-name" }, it.employer_name)),
        h("td", { "data-label": "Rank saat dipilih", class: "num" }, `#${it.rank_at_selection}`),
        h("td", { "data-label": "Status" },
          h("span", { class: `status ${cls}` }, it.status === "submitted" ? icon("check") : null, label),
          it.status === "cancelled" && it.cancel_reason && h("span", { class: "muted small block" }, `Alasan: ${it.cancel_reason}`)),
        h("td", { "data-label": "Aksi" }, actions.length ? actions : h("span", { class: "muted small" }, it.status === "submitted" ? "Batas koreksi lewat" : "-"))));
    }
  };
  toggle.addEventListener("change", () => { showCorrections.value = toggle.checked; paint(); });

  if (MODE === "static") {
    const { staticHistoryActions } = await import("./static-store.js");
    extra.append(...staticHistoryActions(() => renderHistory(main)));
  }
  tbody.append(h("tr", { class: "skeleton", "aria-hidden": "true" }, Array.from({ length: 5 }, () => h("td", {}, h("span", { class: "sk" })))));
  try {
    items = await loadItems();
    paint();
  } catch (e) {
    clear(tbody).append(h("tr", {}, h("td", { colspan: 5, class: "empty" },
      h("strong", { role: "alert" }, `Riwayat gagal dimuat: ${e.message}`))));
  }
}
