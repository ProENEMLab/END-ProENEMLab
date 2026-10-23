import { icon } from "../icons.js";

const MAX_SUGGESTIONS = 8;
const SEARCH_DEBOUNCE_MS = 300;

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function debounce(fn, wait) {
  let timer = 0;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), wait);
  };
}

function normalize(text) {
  return String(text || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export class FilterCombobox {
  constructor(root, { id, label, placeholder, multiple = true, onChange } = {}) {
    this.root = root;
    this.id = id;
    this.labelText = label;
    this.placeholder = placeholder || "Buscar";
    this.multiple = multiple;
    this.onChange = onChange || (() => {});
    this.options = [];
    this.selected = [];
    this.activeIndex = -1;
    this.query = "";
    this._renderShell();
  }

  _renderShell() {
    const listId = `${this.id}-listbox`;
    this.root.classList.add("filter-combobox");
    this.root.innerHTML = `
      <div class="filter-combobox-label-row">
        <label id="${this.id}-label" for="${this.id}-input">${this.labelText}</label>
      </div>
      <div class="filter-combobox-control" data-control>
        <div class="filter-chips" data-chips></div>
        <input
          id="${this.id}-input"
          class="filter-combobox-input"
          type="text"
          autocomplete="off"
          spellcheck="false"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded="false"
          aria-controls="${listId}"
          aria-labelledby="${this.id}-label"
          placeholder="${this.placeholder}"
        >
        ${icon("chevronDown", { size: 16, className: "icon filter-combobox-caret" })}
      </div>
      <ul id="${listId}" class="filter-combobox-list" role="listbox" hidden></ul>
    `;
    this.input = this.root.querySelector("input");
    this.list = this.root.querySelector("[role=listbox]");
    this.chips = this.root.querySelector("[data-chips]");
    this.control = this.root.querySelector("[data-control]");
    this.labelEl = this.root.querySelector("label");

    this.input.addEventListener("input", debounce(() => {
      this.query = this.input.value;
      this.open();
      this._renderList();
    }, SEARCH_DEBOUNCE_MS));
    this.input.addEventListener("focus", () => {
      this.query = this.input.value;
      this.open();
      this._renderList();
    });
    this.input.addEventListener("keydown", (event) => this._onKey(event));
    this.control.addEventListener("click", (event) => {
      if (event.target.closest("[data-remove]")) return;
      this.input.focus();
      this.open();
      this._renderList();
    });
    this.list.addEventListener("mousedown", (event) => {
      const option = event.target.closest("[role=option]");
      if (!option) return;
      event.preventDefault();
      this._selectValue(option.dataset.value);
    });
    document.addEventListener("mousedown", (event) => {
      if (!this.root.contains(event.target)) this.close();
    });
  }

  setOptions(options) {
    this.options = (options || []).map((item) => (
      typeof item === "object"
        ? { value: String(item.value), label: String(item.label) }
        : { value: String(item), label: String(item) }
    ));
    this._syncSelected();
    this._renderChips();
    this._renderList();
  }

  setValues(values) {
    const wanted = new Set((values || []).map((v) => String(v)).filter(Boolean));
    this.selected = this.options.filter((opt) => wanted.has(opt.value));
    this._renderChips();
    this._updateLabel();
  }

  getValues() {
    return this.selected.map((opt) => opt.value);
  }

  clear() {
    this.selected = [];
    this.input.value = "";
    this.query = "";
    this._renderChips();
    this._updateLabel();
    this._renderList();
  }

  _syncSelected() {
    const byValue = new Map(this.options.map((opt) => [opt.value, opt]));
    this.selected = this.selected
      .map((opt) => byValue.get(opt.value) || opt)
      .filter((opt) => byValue.has(opt.value));
  }

  _matches() {
    const q = normalize(this.query);
    const selected = new Set(this.selected.map((opt) => opt.value));
    return this.options.filter((opt) => {
      if (this.multiple && selected.has(opt.value)) return false;
      if (!q) return true;
      return normalize(opt.label).includes(q);
    });
  }

  _renderList() {
    const matches = this._matches();
    const visible = matches.slice(0, MAX_SUGGESTIONS);
    const extra = matches.length - visible.length;

    if (!matches.length) {
      const term = this.query.trim();
      this.list.innerHTML = `<li class="filter-combobox-empty" role="presentation">Nenhum resultado${term ? ` para '${term}'` : ""}.</li>`;
      this.activeIndex = -1;
      return;
    }

    this.list.innerHTML = visible.map((opt, index) => `
      <li
        role="option"
        id="${this.id}-opt-${index}"
        data-value="${escapeHtml(opt.value)}"
        aria-selected="${index === this.activeIndex ? "true" : "false"}"
        class="${index === this.activeIndex ? "is-active" : ""}"
      >${escapeHtml(opt.label)}</li>
    `).join("") + (extra > 0
      ? `<li class="filter-combobox-more" role="presentation">+${extra} outras</li>`
      : "");
  }

  _renderChips() {
    this.chips.innerHTML = this.selected.map((opt) => `
      <button type="button" class="filter-chip" data-remove="${escapeHtml(opt.value)}" aria-label="Remover ${escapeHtml(opt.label)}">
        <span>${escapeHtml(opt.label)}</span>
        ${icon("x", { size: 12 })}
      </button>
    `).join("");
    this.chips.querySelectorAll("[data-remove]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        this._removeValue(btn.dataset.remove);
      });
    });
    this._updateLabel();
  }

  _updateLabel() {
    const count = this.selected.length;
    this.labelEl.textContent = count ? `${this.labelText} (${count})` : this.labelText;
  }

  _selectValue(value) {
    const option = this.options.find((opt) => opt.value === String(value));
    if (!option) return;
    if (this.multiple) {
      if (!this.selected.some((opt) => opt.value === option.value)) {
        this.selected = [...this.selected, option];
      }
      this.input.value = "";
      this.query = "";
      this._renderChips();
      this._renderList();
      this.input.focus();
      this.onChange(this.getValues());
      return;
    }
    this.selected = [option];
    this.input.value = "";
    this.query = "";
    this._renderChips();
    this.close();
    this.onChange(this.getValues());
  }

  _removeValue(value) {
    this.selected = this.selected.filter((opt) => opt.value !== String(value));
    this._renderChips();
    this._renderList();
    this.onChange(this.getValues());
  }

  _onKey(event) {
    const matches = this._matches().slice(0, MAX_SUGGESTIONS);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      this.open();
      this.activeIndex = Math.min(this.activeIndex + 1, matches.length - 1);
      if (this.activeIndex < 0 && matches.length) this.activeIndex = 0;
      this._renderList();
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      this.activeIndex = Math.max(this.activeIndex - 1, 0);
      this._renderList();
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      const current = matches[this.activeIndex] || matches[0];
      if (current) this._selectValue(current.value);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      this.close();
      return;
    }
    if (event.key === "Backspace" && !this.input.value && this.selected.length) {
      this._removeValue(this.selected[this.selected.length - 1].value);
    }
  }

  open() {
    this.list.hidden = false;
    this.input.setAttribute("aria-expanded", "true");
    this.root.classList.add("is-open");
  }

  close() {
    this.list.hidden = true;
    this.input.setAttribute("aria-expanded", "false");
    this.root.classList.remove("is-open");
    this.activeIndex = -1;
  }
}
