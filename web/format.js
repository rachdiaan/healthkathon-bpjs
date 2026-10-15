// Format tampilan. Rp dibulatkan half-up ke Rp 100.000 (BR-5); waktu dalam WIB (BR-9).
const STEP = 100000;
export function rp(v) {
  if (v === null || v === undefined) return "-";
  const r = Math.floor(v / STEP + 0.5) * STEP;
  return "Rp " + r.toLocaleString("id-ID");
}
export function rpShort(v) {
  const r = Math.floor(v / STEP + 0.5) * STEP;
  if (r >= 1e9) return `Rp ${(r / 1e9).toLocaleString("id-ID", { maximumFractionDigits: 1 })} M`;
  if (r >= 1e6) return `Rp ${(r / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 1 })} jt`;
  return rp(v);
}
const WIB = new Intl.DateTimeFormat("id-ID", { timeZone: "Asia/Jakarta", day: "numeric", month: "short",
  year: "numeric", hour: "2-digit", minute: "2-digit" });
export function wib(iso) {
  return iso ? `${WIB.format(new Date(iso))} WIB` : "-";
}
const MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
  "Oktober", "November", "Desember"];
export function period(p) {
  if (!p) return "-";
  const [y, m] = p.split("-");
  return `${MONTHS[Number(m) - 1]} ${y}`;
}
export const CONF_LABEL = { tinggi: "Keyakinan tinggi", sedang: "Keyakinan sedang", rendah: "Keyakinan rendah" };
