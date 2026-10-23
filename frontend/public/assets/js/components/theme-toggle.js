import { THEME_KEY } from "../session.js";

function systemPrefersDark() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function getStoredTheme() {
  return localStorage.getItem(THEME_KEY) || "system";
}

export function isDarkTheme() {
  const stored = getStoredTheme();
  if (stored === "dark") return true;
  if (stored === "light") return false;
  return systemPrefersDark();
}

export function applyTheme(mode) {

  const theme = mode === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", theme);
  updateFavicon();
  document.dispatchEvent(new CustomEvent("proenem:themechange", { detail: { theme, dark: isDarkTheme() } }));
}

export function persistTheme(mode) {
  localStorage.setItem(THEME_KEY, mode);
  applyTheme(mode);
}

export function updateFavicon() {
  const link = document.getElementById("favicon") || document.querySelector("link[rel='icon']");
  if (!link) return;
  link.href = "/assets/images/icon-dark.png";
}

applyTheme("dark");

if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (getStoredTheme() === "system") applyTheme("system");
  });
}

const ICONS = {
  light: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>`,
  dark: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 14.5A8.5 8.5 0 1 1 9.5 3 7 7 0 0 0 21 14.5z"/></svg>`,
  system: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>`,
};

class ThemeToggle extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    const placement = this.getAttribute("placement") || "floating";
    this.setAttribute("placement", placement);
    this.innerHTML = `
      <button type="button" class="theme-btn" data-theme-mode="light" title="Tema claro" aria-label="Tema claro">${ICONS.light}</button>
      <button type="button" class="theme-btn" data-theme-mode="dark" title="Tema escuro" aria-label="Tema escuro">${ICONS.dark}</button>
      <button type="button" class="theme-btn" data-theme-mode="system" title="Seguir o sistema" aria-label="Seguir o sistema">${ICONS.system}</button>
    `;
    this.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-theme-mode]");
      if (!btn) return;
      persistTheme(btn.dataset.themeMode);
      this._sync();
    });
    this._sync();
  }

  _sync() {
    const current = getStoredTheme();
    this.querySelectorAll("[data-theme-mode]").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.themeMode === current);
    });
  }
}

customElements.define("theme-toggle", ThemeToggle);
