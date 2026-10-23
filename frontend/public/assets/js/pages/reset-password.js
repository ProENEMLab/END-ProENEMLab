import { api } from "../api.js";
import { setFlash } from "../session.js";
import { bindPasswordToggles } from "../icons.js";
import { setFieldError, setFormAlert, setSubmitting } from "../auth.js";
import { showToast } from "../components/toast.js";
import "../components/auth-art.js";

bindPasswordToggles();

const params = new URLSearchParams(window.location.search);
const resetToken = params.get("reset_token") || params.get("token") || "";

const form = document.getElementById("reset-form");
const missing = document.getElementById("missing-token");

if (!resetToken) {
  form.hidden = true;
  missing.hidden = false;
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = form.querySelector("[name=password]");
  const confirm = form.querySelector("[name=password-confirm]");
  setFieldError(password, "");
  setFieldError(confirm, "");
  setFormAlert(form, "");

  if (password.value.length < 8) {
    setFieldError(password, "A senha deve ter no mínimo 8 caracteres.");
    return;
  }
  if (password.value !== confirm.value) {
    setFieldError(confirm, "As senhas não coincidem.");
    return;
  }

  setSubmitting(form, true);
  try {
    await api.post("/auth/reset-password", {
      reset_token: resetToken,
      new_password: password.value,
    });
    setFlash("Senha redefinida. Entre com a nova senha.");
    window.location.href = "/pages/authentication/login.html";
  } catch (err) {
    setFormAlert(form, err.message);
    showToast(err.message, "error");
    setSubmitting(form, false);
  }
});
