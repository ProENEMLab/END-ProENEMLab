import { consumeFlash } from "../session.js";

const queued = [];

function ensureContainer() {
  let el = document.querySelector("toast-container");
  if (!el) {
    el = document.createElement("toast-container");
    document.body.appendChild(el);
  }
  return el;
}

function renderToast(message, type) {
  const container = ensureContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", "status");
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

export function showToast(message, type = "success", options = {}) {
  if (window.proenem?.focusActive && !options.urgent) {
    queued.push({ message, type });
    return;
  }
  renderToast(message, type);
}

export function flushQueuedToasts() {
  const pending = queued.splice(0, queued.length);
  for (const item of pending) renderToast(item.message, item.type);
}

window.showToast = showToast;

class ToastContainer extends HTMLElement {
  connectedCallback() {
    const flash = consumeFlash();
    if (flash?.message) {
      showToast(flash.message, flash.type || "success");
    }
  }
}

customElements.define("toast-container", ToastContainer);
