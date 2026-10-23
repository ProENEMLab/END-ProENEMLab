import { bindPasswordToggles } from "../icons.js";
import { registerWithForm } from "../auth.js";
import { setFlash } from "../session.js";
import "../components/auth-art.js";

bindPasswordToggles();

const form = document.getElementById("register-form");

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await registerWithForm(form);
    if (!data) return;
    setFlash("Conta criada. Entre com o e-mail cadastrado para abrir o dashboard.");
    const next = new URLSearchParams(window.location.search).get("next");
    const login = next
      ? `/pages/authentication/login.html?next=${encodeURIComponent(next)}`
      : "/pages/authentication/login.html";
    window.location.href = login;
  } catch {

  }
});
