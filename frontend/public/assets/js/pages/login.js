import { bindPasswordToggles } from "../icons.js";
import { loginWithForm } from "../auth.js";
import { safeNextPath } from "../session.js";
import "../components/auth-art.js";

bindPasswordToggles();

const form = document.getElementById("login-form");
const privacyModal = document.getElementById("privacy-modal");

document.getElementById("privacy-link")?.addEventListener("click", (event) => {
  event.preventDefault();
  privacyModal?.classList.add("is-open");
});

privacyModal?.querySelectorAll("[data-close-modal]").forEach((btn) => {
  btn.addEventListener("click", () => privacyModal.classList.remove("is-open"));
});
privacyModal?.addEventListener("click", (event) => {
  if (event.target === privacyModal) privacyModal.classList.remove("is-open");
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") privacyModal?.classList.remove("is-open");
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await loginWithForm(form);
    if (!data) return;
    window.location.href = safeNextPath("/pages/dashboard/index.html");
  } catch {

  }
});
