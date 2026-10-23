import { api } from "../api.js";
import { getUser, logout } from "../session.js";
import { icon } from "../icons.js";
import { brandLockup } from "../brand.js";
import { bootPomodoro } from "../pomodoro.js";
import "../export-report.js";

function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "?";
}

class AppNavbar extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    const user = getUser() || {};
    this.innerHTML = `
      <header class="topbar">
        <div class="row">
          <button type="button" class="menu-toggle" data-menu-toggle aria-label="Abrir menu">
            ${icon("menu", { size: 20 })}
          </button>
          ${brandLockup({ href: "/pages/dashboard/index.html" })}
        </div>
        <div class="topbar-actions">
          <span class="badge badge-primary" id="points-badge">${icon("star", { size: 13 })} <span data-points>...</span> pts</span>
          <span class="badge badge-warning" id="streak-badge">${icon("flame", { size: 13 })} <span data-streak>...</span></span>
          <div class="user-menu">
            <button type="button" class="user-menu-btn" aria-haspopup="true">
              <span class="user-avatar">${initials(user.name)}</span>
              <span>${user.name || "Conta"}</span>
            </button>
            <div class="user-menu-dropdown">
              <div class="muted" style="padding: 8px 12px; font-size: 12px;">${user.email || ""}</div>
              <button type="button" data-export-pdf>${icon("fileText", { size: 16 })} Exportar PDF</button>
              <button type="button" data-logout>${icon("logOut", { size: 16 })} Sair</button>
            </div>
          </div>
        </div>
      </header>
    `;

    const menu = this.querySelector(".user-menu");
    this.querySelector(".user-menu-btn").addEventListener("click", () => {
      menu.classList.toggle("open");
    });
    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target)) menu.classList.remove("open");
    });
    this.querySelector("[data-logout]").addEventListener("click", () => {
      logout();
    });
    this.querySelector("[data-menu-toggle]")?.addEventListener("click", () => {
      document.dispatchEvent(new CustomEvent("proenem:togglesidebar"));
    });
    this._loadBadges();
    bootPomodoro();
  }

  async _loadBadges() {
    try {
      const [points, streak] = await Promise.all([
        api.get("/points"),
        api.get("/streak"),
      ]);
      this.querySelector("[data-points]").textContent = points.total_points ?? 0;
      this.querySelector("[data-streak]").textContent = streak.current_streak ?? 0;
    } catch (err) {
      this.querySelector("[data-points]").textContent = "—";
      this.querySelector("[data-streak]").textContent = "—";
      showToast(err.message, "error");
    }
  }
}

customElements.define("app-navbar", AppNavbar);
