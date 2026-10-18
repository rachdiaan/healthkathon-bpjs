// Cara kerja PayRay: modul scan, alur petugas, kalkulator estimasi, etika & perlindungan.
import { h, clear, icon } from "./dom.js";
import { card, bd, openInfo, table } from "./ui.js";
import { REASONS, MODULES } from "./catalog.js";

const MODS = [
  ["upah", "Membaca pola upah yang dilaporkan dibanding UMK, sektor, dan BU sejenis.", null],
  ["headcount", "Membandingkan jumlah pekerja terdaftar dengan skala usaha (NIB/OSS) dan pola sektor (KBLI).", "Fase lanjut: dicocokkan dengan kepesertaan BPJS Ketenagakerjaan."],
  ["status", "Mencari klaster pekerja yang pindah dari PPU ke PBPU dari satu pemberi kerja dalam waktu berdekatan.", "Fase lanjut: cek \"pekerja masih aktif bekerja\" butuh data BPJS Ketenagakerjaan."],
];

function moduleCard([mod, what, later]) {
  const codes = Object.entries(REASONS).filter(([, r]) => r[1] === mod);
  return card(MODULES[mod][0], [
    h("p", { class: "fn", style: { marginBottom: "10px" } }, what),
    h("div", {}, codes.map(([code, [label, , desc, miss]]) => h("button", { class: "hb", type: "button", "data-info": "",
      style: { gridTemplateColumns: "1fr auto" },
      onclick: (e) => openInfo({ t: label, c: "d", sl: "Apa artinya", s: desc, hl: "Kode", h: code, w: miss,
        u: "Dasar memilih BU untuk diperiksa, bukan bukti ketidakpatuhan." }, e.currentTarget) },
    h("span", {}, label), icon("right", 16)))),
    later && h("p", { class: "disc" }, icon("clock", 16), later)]);
}

export function renderMethod(main) {
  clear(main);
  document.title = "Cara kerja · PayRay";
  const arrow = () => icon("right");
  main.append(
    card("Dari data badan usaha menjadi antrean pemeriksaan", h("div", { class: "fun" },
      h("div", {}, h("strong", {}, "Semua BU"), "dinilai tiap batch, bukan sampel ", bd("m")),
      arrow(),
      h("div", {}, h("strong", {}, "3 modul + model"), "aturan transparan, Isolation Forest, model dari hasil pemeriksaan ", bd("d")),
      arrow(),
      h("div", {}, h("strong", {}, "Antrean"), "skor, keyakinan, 2–3 alasan, estimasi Rp ", bd("a")))),
    h("div", { class: "row4 r3" }, MODS.map(moduleCard)),
    h("div", { class: "g2" },
      card("Kenapa AI, bukan aturan saja", h("div", {},
        h("div", { class: "li" }, h("span", {}, "Aturan transparan"), h("b", {}, "menangkap pola yang sudah dikenal")),
        h("div", { class: "li" }, h("span", {}, "Isolation Forest"), h("b", {}, "menandai kombinasi ciri yang belum dirumuskan")),
        h("div", { class: "li" }, h("span", {}, "Model dari hasil pemeriksaan"), h("b", {}, "belajar mana pola yang benar-benar terbukti")),
        h("div", { class: "li" }, h("span", {}, "Skor gabungan"), h("b", {}, "presisi 10% teratas naik dari 68,4% ke 82,2%")),
        h("p", { class: "fn", style: { marginTop: "10px" } }, "Model dibatasi monoton: ciri yang makin mencurigakan tidak pernah menurunkan skor, sehingga alasannya tetap bisa dibaca."))),
      card("Kalkulator estimasi iuran tak tertagih", [
        h("div", { class: "formula" }, "(min(upah wajar, plafon) − min(upah dilaporkan, plafon))", h("br"),
          "× 5% × jumlah pekerja × 12", h("br"), "+ iuran pekerja yang dipindah ke PBPU"),
        h("p", { class: "fn", style: { marginTop: "10px" } }, "Iuran PPU 5% dari upah (4% pemberi kerja, 1% pekerja) dengan plafon upah iuran. Ditampilkan sebagai rentang dan selalu berlabel indikatif, bukan tagihan. ", bd("a"))])),
    card("Alur kerja petugas: dulu dan nanti", [
      h("b", {}, "Dulu"),
      h("div", { class: "flow" }, ["Susun daftar target manual", "Pilih dari laporan atau sampel", "Periksa satu per satu", "Hasil tersimpan di berkas", "Daftar berikutnya disusun ulang"].map((t) => h("span", {}, t))),
      h("b", {}, "Dengan PayRay"),
      h("div", { class: "flow af" }, ["Semua BU dinilai otomatis", "Petugas membuka antrean + alasan", "Periksa dengan checklist", "Catat hasil di PayRay", "Hasil jadi label, model belajar"].map((t) => h("span", {}, t))),
      h("p", { class: "fn" }, "Waktu menyusun daftar target: dari hitungan hari menjadi menit. Supervisor menjalankan rescore dan memublikasikan batch baru tiap periode.")]),
    card("Etika dan perlindungan", table(["Prinsip", "Penerapan di PayRay"], h("tbody", {},
      [["Tidak menuduh", "Output berupa urutan prioritas dengan alasan. Keputusan pemeriksaan dan sanksi tetap di petugas (human-in-the-loop)."],
        ["Perlindungan UMKM", "Usaha mikro dan kecil dikecualikan dari upah minimum (PP 36/2021). Aturan upah dibedakan per skala; UMKM padat karya diberi badge pembinaan."],
        ["Keyakinan skor", "Wilayah atau sektor dengan data sedikit mendapat keyakinan rendah dan tidak didahulukan."],
        ["UU PDP", "Analisis agregat per badan usaha. NIK dipseudonimisasi dengan HMAC; layar hanya menampilkan 8 karakter token."],
        ["Akses dan jejak", "Akses berbasis peran (petugas, supervisor), audit log setiap aksi, petugas tidak melihat outcome inspeksi orang lain."],
        ["Data prototype", "100% data sintetis dan data publik. Data peserta riil tidak dipakai."]]
        .map(([a, b]) => h("tr", {}, h("td", {}, h("b", {}, a)), h("td", {}, b)))), "Etika dan perlindungan")));
}
