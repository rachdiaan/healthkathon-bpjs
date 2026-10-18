import { api, ApiError } from "./api.js";
import { h, clear, icon } from "./dom.js";
import { go, state } from "./app.js";

export function renderLogin(main) {
  clear(main);
  document.title = "Masuk · PayRay";
  const err = h("p", { class: "form-error", id: "login-error", "aria-live": "polite" });
  const user = h("input", { id: "username", name: "username", autocomplete: "username", required: true, maxlength: 64 });
  const pass = h("input", { id: "password", name: "password", type: "password", autocomplete: "current-password", required: true, maxlength: 256 });
  const submit = h("button", { class: "btn blk", type: "submit" }, "Masuk");
  const form = h("form", { novalidate: true, "aria-describedby": "login-error" },
    h("div", { class: "field" }, h("label", { for: "username" }, "Username"), user),
    h("div", { class: "field" }, h("label", { for: "password" }, "Password"), pass),
    err, submit);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    err.textContent = "";
    if (!user.value.trim() || !pass.value) {
      err.textContent = "Isi username dan password.";
      return;
    }
    submit.disabled = true;
    submit.textContent = "Memeriksa...";
    try {
      await api("/auth/login", { method: "POST", body: { username: user.value.trim(), password: pass.value } });
      state.me = null;
      go("#/ringkasan");
    } catch (e) {
      err.textContent = e instanceof ApiError && e.status !== 500 ? e.message : "Server tidak merespons. Coba lagi.";
      pass.value = "";
      pass.focus();
    } finally {
      submit.disabled = false;
      submit.textContent = "Masuk";
    }
  });
  main.append(h("section", { class: "login" },
    h("div", {},
      h("div", { class: "login-card" },
        h("div", { class: "login-head" },
          h("span", { class: "lg", "aria-hidden": "true" }, icon("scan", 24)),
          h("div", {}, h("h1", {}, "PayRay"), h("p", {}, "Rontgen kepatuhan pemberi kerja untuk JKN"))),
        form),
      h("p", { class: "fn" }, "Data sintetis · Healthkathon 2026 · Prioritas pemeriksaan, bukan tuduhan"))));
  user.focus();
}
