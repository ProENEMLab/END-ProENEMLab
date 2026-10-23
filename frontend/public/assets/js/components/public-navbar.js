import { getToken, getUser, logout } from "../session.js";
import { brandLockup } from "../brand.js";

function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "?";
}

class PublicNavbar extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    this._render();
    document.addEventListener("proenem:session", () => this._render());
  }

  _render() {
    const logged = Boolean(getToken());
    const user = getUser() || {};
    const path = window.location.pathname;
    const onPlans = path.includes("/pages/plans/");
    this.innerHTML = `
      <header class="public-nav">
        ${brandLockup({ href: "/" })}
        <nav class="public-nav-links" aria-label="Seções">
          <a href="/#fonte">Fonte</a>
          <a href="/#app">O app</a>
          <a href="/pages/plans/index.html"${onPlans ? ' aria-current="page"' : ""}>Planos</a>
        </nav>
        <div class="public-nav-actions">
          ${logged ? `
            <span class="muted" style="font-size:14px">${user.name || initials(user.name)}</span>
            <a class="btn btn-ghost btn-sm" href="/pages/dashboard/index.html">Abrir o dashboard</a>
            <button type="button" class="btn btn-text" data-logout>Sair</button>
          ` : `
            <button type="button" class="btn btn-ghost btn-sm" data-open-auth="login">Entrar</button>
            <button type="button" class="btn btn-primary btn-sm" data-open-auth="register">Criar conta</button>
          `}
        </div>
      </header>
    `;
    this.querySelector("[data-logout]")?.addEventListener("click", logout);
  }
}

customElements.define("public-navbar", PublicNavbar);
