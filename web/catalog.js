// Katalog alasan untuk tampilan. Kode dan checklist mengikuti engine/reasons.py.
export const MODULES = {
  upah: ["Scan Upah", "f1"],
  headcount: ["Scan Headcount", "f2"],
  status: ["Scan Status", "fa"],
  anomali: ["Anomali kombinasi", "f3"],
  data: ["Kualitas data", "f3"],
};

// kode: [label pendek, modul, apa artinya, kapan bisa meleset]
export const REASONS = {
  UPAH_BUNCHING_UMK: ["Upah menumpuk tepat di UMK", "upah",
    "Porsi pekerja yang dilaporkan tepat di UMK jauh di atas pola wajar BU sejenis di sektor dan wilayahnya.",
    "Sektor padat karya yang sah memang membayar di UMK, misalnya garmen atau alas kaki."],
  UPAH_NAIK_SAMA_UMK: ["Kenaikan upah = kenaikan UMK", "upah",
    "Kenaikan upah yang dilaporkan selalu persis sama dengan kenaikan UMK tahunan, tidak pernah lebih.",
    "Perusahaan yang memang menetapkan kenaikan hanya mengikuti UMK."],
  UPAH_BEKU: ["Upah tidak naik", "upah",
    "Upah sebagian besar pekerja tidak berubah antar-tahun, lalu tertinggal dari UMK.",
    "Data upah tahun terakhir belum diperbarui pemberi kerja."],
  UPAH_BAWAH_UMK: ["Upah di bawah UMK (usaha wajib)", "upah",
    "Usaha menengah atau besar melaporkan upah di bawah UMK. Usaha mikro dan kecil dikecualikan (PP 36/2021).",
    "Skala usaha di data keliru, atau pekerja paruh waktu tercatat sebagai penuh waktu."],
  UPAH_ATAS_RENDAH: ["Upah jabatan atas rendah", "upah",
    "Upah 10% pekerja teratas hampir sama dengan UMK. Pola wajar: staf dan supervisor dibayar lebih tinggi.",
    "Struktur organisasi sangat datar, misalnya koperasi kecil."],
  HEADCOUNT_OSS: ["Pekerja terdaftar < rencana OSS", "headcount",
    "Jumlah pekerja terdaftar jauh di bawah rencana tenaga kerja di NIB/OSS dan pola sektornya.",
    "Rencana di OSS belum terealisasi atau usaha sedang mengecil."],
  STATUS_KLASTER_PBPU: ["Klaster pindah PPU ke PBPU", "status",
    "Beberapa pekerja dari satu pemberi kerja pindah ke segmen mandiri (PBPU) dalam waktu berdekatan.",
    "Pemutusan hubungan kerja sungguhan. Cek \"masih aktif bekerja\" butuh data BPJS Ketenagakerjaan (fase lanjut)."],
  ANOMALI_KOMBINASI: ["Kombinasi ciri tidak biasa", "anomali",
    "Isolation Forest menandai kombinasi fitur yang menyimpang dibanding usaha seskala, walau tiap aturan belum terpicu.",
    "Usaha dengan model bisnis unik yang memang berbeda dari sektornya."],
  DATA_SEKTOR_KOSONG: ["Data sektor kosong", "data",
    "Data sektor atau skala usaha kosong, jadi pembanding sektor tidak bisa dipakai.",
    "Bukan indikasi ketidakpatuhan. Lengkapi data sebelum memeriksa."],
};

export const reasonLabel = (code) => REASONS[code]?.[0] || code;
export const reasonModule = (code) => MODULES[REASONS[code]?.[1]] || ["Lainnya", "f3"];

export const CONF = {
  tinggi: ["Keyakinan tinggi", "m"],
  sedang: ["Keyakinan sedang", "d"],
  rendah: ["Keyakinan rendah", "a"],
};
