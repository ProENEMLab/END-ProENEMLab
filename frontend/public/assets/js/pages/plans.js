import { api } from "../api.js";
import { icon } from "../icons.js";
import { showToast } from "../components/toast.js";

const loading = document.getElementById("plans-loading");
const empty = document.getElementById("plans-empty");
const grid = document.getElementById("plans-grid");
const compareSection = document.getElementById("plans-compare");
const compareTable = document.getElementById("plans-compare-table");
const faqSection = document.getElementById("plans-faq");
const faqList = document.getElementById("plans-faq-list");

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function featureList(items) {
  return `<ul class="plan-features">${(items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function isAvailable(plan) {
  return String(plan.price_label || "").trim().toLowerCase() !== "em breve";
}

function compareTone(value) {
  const v = String(value || "").trim().toLowerCase();
  if (v === "inclui") return "is-yes";
  if (v === "quando abrir") return "is-wait";
  if (v === "—" || v === "-" || v === "") return "is-empty";
  return "";
}

function renderPlans(catalog) {
  const plans = catalog.plans || [];
  if (!plans.length) {
    empty.hidden = false;
    grid.hidden = true;
    return;
  }
  empty.hidden = true;
  grid.hidden = false;
  grid.innerHTML = plans.map((plan) => {
    const available = isAvailable(plan);
    const extraId = `plan-extra-${plan.id}`;
    const classes = [
      "plan-card",
      available ? "is-now" : "is-soon",
      plan.highlight ? "is-recommended" : "",
    ].filter(Boolean).join(" ");
    const badge = plan.badge
      ? `<span class="plan-badge plan-badge-${escapeHtml(plan.badge_style || "value")}">${escapeHtml(plan.badge)}</span>`
      : available
        ? `<span class="plan-badge plan-badge-now">Disponível</span>`
        : "";
    const status = available
      ? "Disponível agora · sem cartão"
      : (plan.includes_previous || "Sem checkout nesta fase");
    return `
      <article class="${classes}">
        <header class="plan-card-head">
          <h2 class="plan-kicker">${escapeHtml(plan.name)}${badge}</h2>
          <p class="plan-price">${escapeHtml(plan.price_label || "")}${plan.period ? ` <span>${escapeHtml(plan.period)}</span>` : ""}</p>
          <p class="plan-status">${escapeHtml(status)}</p>
        </header>
        ${featureList(plan.summary_features)}
        <div class="plan-extra">
          <button type="button" class="btn btn-text" data-expand="${extraId}" aria-expanded="false" aria-controls="${extraId}">
            Ver tudo que este plano oferece
            ${icon("chevronDown", { size: 16 })}
          </button>
          <div id="${extraId}" class="plan-extra-panel" hidden>
            ${plan.includes_previous ? `<p class="plan-includes">${escapeHtml(plan.includes_previous)}</p>` : ""}
            ${featureList(plan.all_features)}
          </div>
        </div>
        <button type="button" class="btn ${available ? "btn-primary" : "btn-ghost"}" data-open-auth="${plan.cta_mode || "register"}">
          ${escapeHtml(plan.cta_label || "Criar conta")}
        </button>
      </article>
    `;
  }).join("");

  grid.dataset.count = String(plans.length);

  grid.querySelectorAll("[data-expand]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const panel = document.getElementById(btn.dataset.expand);
      const open = panel.hidden;
      panel.hidden = !open;
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.classList.toggle("is-open", open);
    });
  });
}

function renderCompare(catalog) {
  const plans = catalog.plans || [];
  const rows = catalog.compare || [];
  if (!compareSection || !compareTable || !rows.length || !plans.length) {
    if (compareSection) compareSection.hidden = true;
    return;
  }
  compareSection.hidden = false;
  const head = `<tr><th>Recurso</th>${plans.map((plan) => {
    const classes = [
      isAvailable(plan) ? "is-now" : "",
      plan.highlight ? "is-recommended" : "",
    ].filter(Boolean).join(" ");
    const note = plan.badge ? `<span>${escapeHtml(plan.badge)}</span>` : (isAvailable(plan) ? "<span>agora</span>" : "");
    return `<th class="${classes}">${escapeHtml(plan.name)}${note}</th>`;
  }).join("")}</tr>`;
  const body = rows.map((row) => {
    const cells = plans.map((plan) => {
      const value = (row.values && row.values[plan.id]) || "—";
      const tone = [
        compareTone(value),
        isAvailable(plan) ? "is-now" : "",
      ].filter(Boolean).join(" ");
      return `<td class="${tone}">${escapeHtml(value)}</td>`;
    }).join("");
    return `<tr><td>${escapeHtml(row.label)}</td>${cells}</tr>`;
  }).join("");
  compareTable.innerHTML = `<thead>${head}</thead><tbody>${body}</tbody>`;
}

function renderFaq(items) {
  if (!items?.length) {
    faqSection.hidden = true;
    return;
  }
  faqSection.hidden = false;
  faqList.innerHTML = items.map((item, index) => `
    <div class="accordion-item">
      <h3>
        <button type="button" id="faq-btn-${item.id}" aria-expanded="${index === 0 ? "true" : "false"}" aria-controls="faq-panel-${item.id}">
          ${escapeHtml(item.question)}
          ${icon("chevronDown", { size: 16 })}
        </button>
      </h3>
      <div id="faq-panel-${item.id}" class="accordion-panel" role="region" aria-labelledby="faq-btn-${item.id}" ${index === 0 ? "" : "hidden"}>
        <p>${escapeHtml(item.answer)}</p>
      </div>
    </div>
  `).join("");

  faqList.querySelectorAll("button[aria-controls]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const panel = document.getElementById(btn.getAttribute("aria-controls"));
      const willOpen = panel.hidden;
      faqList.querySelectorAll(".accordion-panel").forEach((el) => {
        el.hidden = true;
      });
      faqList.querySelectorAll("button[aria-controls]").forEach((other) => {
        other.setAttribute("aria-expanded", "false");
      });
      panel.hidden = !willOpen;
      btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
    });
  });
}

async function init() {
  try {
    const catalog = await api.get("/plans");
    loading.hidden = true;
    renderPlans(catalog);
    renderCompare(catalog);
    renderFaq(catalog.faq);
  } catch (err) {
    loading.hidden = true;
    empty.hidden = false;
    showToast(err.message, "error");
  }
}

init();
