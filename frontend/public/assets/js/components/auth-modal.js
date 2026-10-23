import { bindPasswordToggles, icon } from "../icons.js";
import { loginWithForm, registerWithForm } from "../auth.js";
import { showToast } from "./toast.js";
import { brandLockup } from "../brand.js";
import "./auth-art.js";

const LOGIN_QUOTE = "O primeiro domingo de prova é 8 de novembro de 2026.";
const REGISTER_QUOTE = "Cadastro só com e-mail. Depois, o dashboard conta os dias até a prova.";

const LOGIN_HTML = `
  <form id="auth-login-form" novalidate>
    <div class="form-alert" data-form-alert hidden></div>
    <div class="field">
      <label for="auth-login-email">E-mail</label>
      <input id="auth-login-email" name="email" type="email" autocomplete="email" inputmode="email" required placeholder="voce@email.com">
      <span class="field-error"></span>
    </div>
    <div class="field">
      <label for="auth-login-password">Senha</label>
      <div class="field-control">
        <input id="auth-login-password" name="password" type="password" autocomplete="current-password" required>
        <button type="button" class="password-toggle" data-password-toggle="auth-login-password" aria-label="Mostrar senha"></button>
      </div>
      <span class="field-error"></span>
    </div>
    <p class="auth-row">
      <a href="/pages/authentication/forgot-password.html">Esqueci minha senha</a>
      <a class="auth-page-link" href="/pages/authentication/login.html">Abrir a página de login</a>
    </p>
    <button type="submit" class="btn btn-primary btn-block">Entrar na plataforma</button>
  </form>
`;

const REGISTER_HTML = `
  <form id="auth-register-form" novalidate>
    <div class="form-alert" data-form-alert hidden></div>
    <div class="field">
      <label for="auth-register-name">Nome</label>
      <input id="auth-register-name" name="name" type="text" autocomplete="name" required placeholder="Como você quer ser chamado">
      <span class="field-error"></span>
    </div>
    <div class="field">
      <label for="auth-register-email">E-mail</label>
      <input id="auth-register-email" name="email" type="email" autocomplete="email" inputmode="email" required placeholder="voce@email.com">
      <span class="field-error"></span>
    </div>
    <div class="field">
      <label for="auth-register-password">Senha</label>
      <div class="field-control">
        <input id="auth-register-password" name="password" type="password" autocomplete="new-password" required minlength="8">
        <button type="button" class="password-toggle" data-password-toggle="auth-register-password" aria-label="Mostrar senha"></button>
      </div>
      <span class="field-hint">Mínimo de 8 caracteres.</span>
      <span class="field-error"></span>
    </div>
    <div class="field">
      <label for="auth-register-confirm">Confirmar senha</label>
      <div class="field-control">
        <input id="auth-register-confirm" name="password-confirm" type="password" autocomplete="new-password" required minlength="8">
        <button type="button" class="password-toggle" data-password-toggle="auth-register-confirm" aria-label="Mostrar senha"></button>
      </div>
      <span class="field-error"></span>
    </div>
    <button type="submit" class="btn btn-primary btn-block">Criar conta para estudar</button>
  </form>
`;

const FOCUSABLE = "a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex='-1'])";

class AuthModal extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    this.innerHTML = `
      <div class="modal-backdrop auth-modal" id="auth-modal">
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title" aria-describedby="auth-modal-lead">
          <button type="button" class="modal-close" data-close-auth aria-label="Fechar">${icon("x", { size: 18 })}</button>
          <div class="auth-modal-grid">
            <div class="auth-modal-form">
              ${brandLockup({ href: "/" })}
              <p class="auth-kicker" data-auth-kicker>Acesso à plataforma</p>
              <h2 id="auth-modal-title">Entrar</h2>
              <p class="muted" id="auth-modal-lead" data-auth-lead>Use a conta do ProENEM Lab para retomar o roadmap e o banco de questões.</p>
              <div class="auth-modal-tabs" role="tablist" aria-label="Entrar ou criar conta">
                <button type="button" data-auth-tab="login" role="tab" aria-selected="true" class="is-active">Entrar</button>
                <button type="button" data-auth-tab="register" role="tab" aria-selected="false">Criar conta</button>
              </div>
              <div data-auth-panel></div>
              <p class="auth-legal">Cadastro com e-mail. Nesta fase não pedimos cartão. O progresso fica na conta: banco, roadmap e estatísticas.</p>
            </div>
            <auth-art quote="${LOGIN_QUOTE}"></auth-art>
          </div>
        </div>
      </div>
    `;

    this._backdrop = this.querySelector("#auth-modal");
    this._dialog = this.querySelector(".modal");
    this._panel = this.querySelector("[data-auth-panel]");
    this._title = this.querySelector("#auth-modal-title");
    this._lead = this.querySelector("[data-auth-lead]");
    this._kicker = this.querySelector("[data-auth-kicker]");
    this._art = this.querySelector("auth-art");
    this._onKeydown = (event) => this._handleKeydown(event);

    this.querySelector("[data-close-auth]").addEventListener("click", () => this.close());
    this._backdrop.addEventListener("click", (event) => {
      if (event.target === this._backdrop) this.close();
    });
    this.querySelectorAll("[data-auth-tab]").forEach((btn) => {
      btn.addEventListener("click", () => this.show(btn.dataset.authTab));
    });

    document.addEventListener("click", (event) => {
      const trigger = event.target.closest("[data-open-auth]");
      if (!trigger) return;
      event.preventDefault();
      this.show(trigger.dataset.openAuth || "login");
    });
  }

  show(mode = "login") {
    this._mode = mode === "register" ? "register" : "login";
    this.querySelectorAll("[data-auth-tab]").forEach((btn) => {
      const active = btn.dataset.authTab === this._mode;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-selected", active ? "true" : "false");
    });
    if (this._mode === "register") {
      this._title.textContent = "Criar conta";
      this._kicker.textContent = "Cadastro";
      this._lead.textContent = "E-mail e senha. O próximo passo é o roadmap e o banco de questões oficiais.";
      this._art?.setQuote(REGISTER_QUOTE);
      this._panel.innerHTML = REGISTER_HTML;
      this._bindRegister();
    } else {
      this._title.textContent = "Entrar";
      this._kicker.textContent = "Acesso à plataforma";
      this._lead.textContent = "Use a conta do ProENEM Lab para retomar o roadmap e o banco de questões.";
      this._art?.setQuote(LOGIN_QUOTE);
      this._panel.innerHTML = LOGIN_HTML;
      this._bindLogin();
    }
    bindPasswordToggles(this._panel);

    const wasOpen = this._backdrop.classList.contains("is-open");
    if (!wasOpen) {
      this._lastFocus = document.activeElement;
      document.addEventListener("keydown", this._onKeydown);
      document.body.classList.add("auth-modal-open");
    }
    this._backdrop.classList.add("is-open");
    this._panel.querySelector("input")?.focus();
  }

  close() {
    this._backdrop.classList.remove("is-open");
    document.body.classList.remove("auth-modal-open");
    document.removeEventListener("keydown", this._onKeydown);
    if (this._lastFocus && typeof this._lastFocus.focus === "function") {
      this._lastFocus.focus();
    }
  }

  _handleKeydown(event) {
    if (!this._backdrop.classList.contains("is-open")) return;
    if (event.key === "Escape") {
      event.preventDefault();
      this.close();
      return;
    }
    if (event.key !== "Tab") return;
    const nodes = [...this._dialog.querySelectorAll(FOCUSABLE)].filter(
      (el) => !el.hasAttribute("disabled") && el.offsetParent !== null,
    );
    if (!nodes.length) return;
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  _bindLogin() {
    const form = this.querySelector("#auth-login-form");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const data = await loginWithForm(form);
        if (!data) return;
        this.close();
        document.dispatchEvent(new CustomEvent("proenem:session"));
        showToast("Sessão iniciada.", "success");
      } catch {

      }
    });
  }

  _bindRegister() {
    const form = this.querySelector("#auth-register-form");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const data = await registerWithForm(form);
        if (!data) return;
        showToast("Conta criada. Entre com o e-mail cadastrado.", "success");
        this.show("login");
      } catch {

      }
    });
  }
}

customElements.define("auth-modal", AuthModal);
