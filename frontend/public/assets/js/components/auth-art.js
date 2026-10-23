import { brandLockup } from "../brand.js";
import { getEnemCountdown, renderCountdownMarkup } from "../enem-dates.js";

const DEFAULT_QUOTE = "O primeiro domingo de prova é 8 de novembro de 2026.";

class AuthArt extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    this.classList.add("auth-art");
    this.setAttribute("aria-hidden", "true");
    const showCountdown = this.getAttribute("countdown") !== "0";
    this.innerHTML = `
      <header class="auth-art-top">
        ${brandLockup({ linked: false, extraClass: "is-lg" })}
        <p class="auth-art-edition">ENEM 2026</p>
      </header>
      <div class="auth-art-dates">
        <div class="auth-exam-date">
          <span class="auth-exam-day">08</span>
          <span class="auth-exam-month">novembro</span>
          <span class="auth-exam-label">1º dia · linguagens, humanas, redação</span>
        </div>
        <div class="auth-exam-date">
          <span class="auth-exam-day">15</span>
          <span class="auth-exam-month">novembro</span>
          <span class="auth-exam-label">2º dia · natureza e matemática</span>
        </div>
      </div>
      <div class="auth-art-inner">
        <p class="auth-art-quote"></p>
        ${showCountdown ? '<div data-auth-countdown></div>' : ""}
      </div>
      <ul class="auth-art-facts">
        <li>Banco de questões oficiais do INEP</li>
        <li>Roadmap linear com o que falta até novembro</li>
        <li>Cadastro com e-mail, sem cartão nesta fase</li>
      </ul>
    `;
    this.setQuote(this.getAttribute("quote") || DEFAULT_QUOTE);
    const mount = this.querySelector("[data-auth-countdown]");
    if (mount) {
      mount.innerHTML = renderCountdownMarkup(getEnemCountdown(), { compact: true });
    }
  }

  setQuote(text) {
    const el = this.querySelector(".auth-art-quote");
    if (el) el.textContent = text;
  }
}

customElements.define("auth-art", AuthArt);
