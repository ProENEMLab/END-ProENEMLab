import { api } from "../api.js";
import { icon } from "../icons.js";
import { getToken } from "../session.js";

const BADGE_INTERVAL_MS = 5 * 60 * 1000;

const LINKS = [
  {
    href: "/pages/dashboard/index.html",
    label: "Dashboard",
    match: "/pages/dashboard/",
    icon: "layoutDashboard",
  },
  {
    href: "/pages/roadmap/index.html",
    label: "Roadmap",
    match: "/pages/roadmap/",
    icon: "route",
  },
  {
    href: "/pages/questions/index.html",
    label: "Banco de questões",
    match: "/pages/questions/",
    icon: "bookOpen",
  },
  {
    href: "/pages/stats/index.html",
    label: "Estatísticas",
    match: "/pages/stats/",
    icon: "barChart",
  },
  {
    href: "/pages/calendar/index.html",
    label: "Calendário",
    match: "/pages/calendar/",
    icon: "calendar",
  },
  {
    href: "/pages/reviews/index.html",
    label: "Revisões",
    match: "/pages/reviews/",
    icon: "clock",
  },
  {
    href: "/pages/report/index.html",
    label: "Relatório",
    match: "/pages/report/",
    icon: "listChecks",
  },
  {
    href: "/pages/notifications/index.html",
    label: "Avisos",
    match: "/pages/notifications/",
    icon: "mail",
  },
];

class AppSidebar extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    const path = window.location.pathname;
    this.innerHTML = `
      <div class="sidebar-backdrop" data-sidebar-close></div>
      <aside class="sidebar">
        <nav>
          ${LINKS.map((link) => `
            <a class="nav-link${path.includes(link.match) ? " is-active" : ""}" href="${link.href}">
              ${icon(link.icon, { size: 18 })}
              <span>${link.label}</span>
              ${link.match === "/pages/reviews/" ? `<span class="nav-count" data-review-badge hidden></span>` : ""}
            </a>
          `).join("")}
        </nav>
      </aside>
    `;

    const sidebar = this.querySelector(".sidebar");
    const backdrop = this.querySelector(".sidebar-backdrop");
    const close = () => {
      sidebar.classList.remove("is-open");
      backdrop.classList.remove("is-open");
    };

    document.addEventListener("proenem:togglesidebar", () => {
      const open = !sidebar.classList.contains("is-open");
      sidebar.classList.toggle("is-open", open);
      backdrop.classList.toggle("is-open", open);
    });
    backdrop.addEventListener("click", close);
    this._refreshBadge = () => refreshReviewBadge(this);
    this._refreshBadge();
    this._badgeTimer = window.setInterval(this._refreshBadge, BADGE_INTERVAL_MS);
    window.addEventListener("proenem:reviews-changed", this._refreshBadge);
  }

  disconnectedCallback() {
    window.clearInterval(this._badgeTimer);
    if (this._refreshBadge) {
      window.removeEventListener("proenem:reviews-changed", this._refreshBadge);
    }
  }
}

async function refreshReviewBadge(root) {
  const badge = root.querySelector("[data-review-badge]");
  if (!badge || !getToken()) return;
  try {
    const data = await api.get("/reviews/badge");
    const count = Number(data.due_today) || 0;
    if (count <= 0) {
      badge.hidden = true;
      badge.textContent = "";
      badge.removeAttribute("aria-label");
      return;
    }
    badge.hidden = false;
    badge.textContent = count > 99 ? "99+" : String(count);
    const noun = count === 1 ? "revisão" : "revisões";
    badge.setAttribute("aria-label", `${count} ${noun} para hoje`);
  } catch {
    badge.hidden = true;
  }
}

customElements.define("app-sidebar", AppSidebar);
