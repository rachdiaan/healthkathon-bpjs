// Riwayat Saya (Alur B langkah 6–7). Status tanpa outcome (FR-18); koreksi ≤ 7 hari (BR-11).
import { api, MODE } from "./api.js";
import { h, clear, icon } from "./dom.js";
import { toast } from "./app.js";
import { openForm, loadCopy } from "./inspection-form.js";
import { card, labelRows, kpi } from "./ui.js";

const STATUS = {
  submitted: ["Tersimpan", "g"],
  superseded: ["Dikoreksi (versi lama)", ""],
  cancelled: ["Dibatalkan supervisor", "a"],
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
  const tbl = h("table", { class: "rsp" },
    h("caption", { class: "visually-hidden" }, "Riwayat inspeksi saya"),
    h("thead", {}, h("tr", {}, ["Tanggal", "Badan usaha", "Rank saat dipilih", "Status", "Aksi"].map((t) => h("th", { scope: "col" }, t)))),
    tbody);
  const stats = h("div", { class: "row4" });
  const extra = [h("label", { class: "radio", for: "show-corr" }, toggle, h("span", {}, "Tampilkan koreksi"))];
  if (MODE === "static") {
    const { staticHistoryActions } = await import("./static-store.js");
    extra.push(...staticHistoryActions(() => renderHistory(main)));
  }
  main.append(stats,
    card("Inspeksi yang Anda catat", [h("div", { class: "tw" }, tbl),
      h("p", { class: "fn", style: { marginTop: "12px" } }, "Hasil (outcome) tidak ditampilkan di sini; supervisor yang membacanya. Koreksi bisa dilakukan sampai 7 hari setelah dicatat.")], extra));

  let items = [];
  const paint = () => {
    clear(stats).append(
      kpi("Inspeksi tersimpan", items.filter((i) => i.status === "submitted").length.toLocaleString("id-ID"), "m", "versi terbaru tiap BU"),
      kpi("Masih bisa dikoreksi", items.filter((i) => i.can_correct).length.toLocaleString("id-ID"), "m", "batas 7 hari"),
      kpi("Sudah dikoreksi", items.filter((i) => i.status === "superseded").length.toLocaleString("id-ID"), "m", "versi lama tetap tercatat"),
      kpi("Dibatalkan supervisor", items.filter((i) => i.status === "cancelled").length.toLocaleString("id-ID"), "m", "dengan alasan tertulis"));
    clear(tbody);
    const visible = items.filter((it) => showCorrections.value || it.status !== "superseded");
    if (!visible.length) {
      tbody.append(h("tr", {}, h("td", { colspan: 5, class: "empty" },
        h("strong", {}, "Belum ada inspeksi tercatat."),
        "Buka BU dari antrean, lalu pilih “Catat hasil inspeksi”.")));
      return;
    }
    for (const it of visible) {
      const [label, cls] = STATUS[it.status] || [it.status, ""];
      const actions = [];
      if (it.can_correct) {
        const btn = h("button", { class: "btn l", type: "button" }, "Koreksi");
        btn.addEventListener("click", () => openForm({
          employer: { id: it.employer_id, name: it.employer_name }, rank: it.rank_at_selection,
          supersedeId: it.id,
          initial: MODE === "static" ? { inspected_on: it.inspected_on, outcome: it.outcome, violation_types: it.violation_types, rp_found: it.rp_found, notes: it.notes } : loadCopy(it.id),
          onSaved: () => { toast("Koreksi tersimpan"); renderHistory(main); },
        }, btn));
        actions.push(btn);
      }
      tbody.append(h("tr", {},
        h("td", {}, fmtDate(it.inspected_on)),
        h("td", {}, h("a", { href: `#/bu/${it.employer_id}`, class: "nm" }, it.employer_name)),
        h("td", {}, `#${it.rank_at_selection}`),
        h("td", {}, h("span", { class: `b ${cls}` }, it.status === "submitted" ? icon("check") : null, label),
          it.status === "cancelled" && it.cancel_reason && h("small", {}, `Alasan: ${it.cancel_reason}`)),
        h("td", {}, actions.length ? actions : h("span", { class: "fn" }, it.status === "submitted" ? "Batas koreksi lewat" : "-"))));
    }
    labelRows(tbl);
  };
  toggle.addEventListener("change", () => { showCorrections.value = toggle.checked; paint(); });

  tbody.append(h("tr", { "aria-hidden": "true" }, Array.from({ length: 5 }, () => h("td", {}, h("span", { class: "sk" })))));
  try {
    items = await loadItems();
    paint();
  } catch (e) {
    clear(tbody).append(h("tr", {}, h("td", { colspan: 5, class: "empty" },
      h("strong", { role: "alert" }, `Riwayat gagal dimuat: ${e.message}`))));
  }
}
