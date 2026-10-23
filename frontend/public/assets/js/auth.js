import { api } from "./api.js";
import { setSession } from "./session.js";

export function setFieldError(input, message) {
  const field = input?.closest(".field");
  if (!field) return;
  field.classList.toggle("has-error", Boolean(message));
  const el = field.querySelector(".field-error");
  if (el) el.textContent = message || "";
}

export function clearFieldErrors(form) {
  form.querySelectorAll(".field").forEach((field) => {
    field.classList.remove("has-error");
    const el = field.querySelector(".field-error");
    if (el) el.textContent = "";
  });
}

export function setFormAlert(form, message) {
  const alert = form.querySelector("[data-form-alert]");
  if (!alert) return;
  alert.hidden = !message;
  alert.textContent = message || "";
}

export function setSubmitting(form, loading) {
  const submit = form.querySelector("[type=submit]");
  if (!submit) return;
  submit.disabled = loading;
  submit.classList.toggle("is-loading", loading);
}

export function validateEmail(value) {
  if (!value) return "Informe seu e-mail.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return "E-mail inválido.";
  return "";
}

export function validateLogin(form) {
  clearFieldErrors(form);
  setFormAlert(form, "");
  const email = form.querySelector("[name=email]");
  const password = form.querySelector("[name=password]");
  let valid = true;
  const emailError = validateEmail(email.value.trim());
  if (emailError) {
    setFieldError(email, emailError);
    valid = false;
  }
  if (!password.value) {
    setFieldError(password, "Informe sua senha.");
    valid = false;
  }
  return valid;
}

export function validateRegister(form) {
  clearFieldErrors(form);
  setFormAlert(form, "");
  const name = form.querySelector("[name=name]");
  const email = form.querySelector("[name=email]");
  const password = form.querySelector("[name=password]");
  const confirm = form.querySelector("[name=password-confirm]");
  let valid = true;
  if (!name.value.trim()) {
    setFieldError(name, "Informe seu nome.");
    valid = false;
  }
  const emailError = validateEmail(email.value.trim());
  if (emailError) {
    setFieldError(email, emailError);
    valid = false;
  }
  if (!password.value || password.value.length < 8) {
    setFieldError(password, "A senha deve ter no mínimo 8 caracteres.");
    valid = false;
  }
  if (password.value !== confirm.value) {
    setFieldError(confirm, "As senhas não coincidem.");
    valid = false;
  }
  return valid;
}

export async function loginWithForm(form) {
  if (!validateLogin(form)) return null;
  setSubmitting(form, true);
  try {
    const data = await api.post("/auth/login", {
      email: form.querySelector("[name=email]").value.trim(),
      password: form.querySelector("[name=password]").value,
    });
    setSession(data.access_token, data.user);
    return data;
  } catch (err) {
    setFormAlert(form, err.message);
    const password = form.querySelector("[name=password]");
    setFieldError(password, err.message);
    throw err;
  } finally {
    setSubmitting(form, false);
  }
}

export async function registerWithForm(form) {
  if (!validateRegister(form)) return null;
  setSubmitting(form, true);
  try {
    const data = await api.post("/auth/register", {
      name: form.querySelector("[name=name]").value.trim(),
      email: form.querySelector("[name=email]").value.trim(),
      password: form.querySelector("[name=password]").value,
    });
    return data;
  } catch (err) {
    setFormAlert(form, err.message);
    const email = form.querySelector("[name=email]");
    setFieldError(email, err.message);
    throw err;
  } finally {
    setSubmitting(form, false);
  }
}
