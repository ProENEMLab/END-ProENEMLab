import { api } from "../api.js";
import { setFormAlert, setSubmitting } from "../auth.js";
import { showToast } from "../components/toast.js";
import "../components/auth-art.js";

const form = document.getElementById("forgot-form");
const success = document.getElementById("forgot-success");

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("email").value.trim();
  if (!email) {
    setFormAlert(form, "Informe seu e-mail.");
    return;
  }
  setSubmitting(form, true);
  try {
    await api.post("/auth/forgot-password", { email });
    form.hidden = true;
    success.hidden = false;
  } catch (err) {
    setFormAlert(form, err.message);
    showToast(err.message, "error");
    setSubmitting(form, false);
  }
});
