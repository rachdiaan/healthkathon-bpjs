// Klien API. MODE dibaca dari satu konstanta supaya build statis (t26) bisa memakai modul yang sama.
export const MODE = document.documentElement.dataset.mode === "static" ? "static" : "live";

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.error?.message || `HTTP ${status}`);
    this.status = status;
    this.code = body?.error?.code;
    this.fields = body?.error?.fields || {};
  }
}

export async function api(path, { method = "GET", body, headers = {} } = {}) {
  if (MODE === "static") {
    // Mode statis: tidak ada request ke /api (FR-32).
    const store = await import("./static-store.js");
    return store.handle(path, { method, body });
  }
  const opts = { method, headers: { Accept: "application/json", ...headers }, credentials: "same-origin" };
  if (method !== "GET") opts.headers["X-PayRay-CSRF"] = "1";
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, opts);
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}
