import { api } from "../api.js";
import { consumePendingFilterSave, getToken, setPendingFilterSave, setQuestionQueue } from "../session.js";
import { escapeHtml } from "../markdown.js";
import { showToast } from "../components/toast.js";
import { FilterCombobox } from "../components/filter-combobox.js";
import { difficultyBadge } from "../difficulty.js";

const COUNT_DEBOUNCE_MS = 200;
const yearBox = new FilterCombobox(document.getElementById("filter-year"), {
  id: "filter-year",
  label: "Ano",
  placeholder: "Buscar ano",
  onChange: onFiltersChanged,
});
const subjectBox = new FilterCombobox(document.getElementById("filter-subject"), {
  id: "filter-subject",
  label: "Matéria",
  placeholder: "Buscar matéria",
  onChange: onFiltersChanged,
});
const topicWrap = document.getElementById("filter-topic-wrap");
const topicBox = new FilterCombobox(document.getElementById("filter-topic"), {
  id: "filter-topic",
  label: "Tópico",
  placeholder: "Buscar tópico",
  onChange: onFiltersChanged,
});
const languageWrap = document.getElementById("filter-language-wrap");
const languageBox = new FilterCombobox(document.getElementById("filter-language"), {
  id: "filter-language",
  label: "Idioma",
  placeholder: "Buscar idioma",
  onChange: onFiltersChanged,
});
const excludeInput = document.getElementById("filter-exclude-answered");
const difficultyInput = document.getElementById("filter-difficulty");
const loading = document.getElementById("questions-loading");
const list = document.getElementById("question-list");
const empty = document.getElementById("questions-empty");
const emptyHint = document.getElementById("questions-empty-hint");
const pagination = document.getElementById("pagination");
const countEl = document.getElementById("result-count");
const savedSelect = document.getElementById("saved-filters");
const savePanel = document.getElementById("filter-save-panel");
const saveName = document.getElementById("filter-set-name");

let countTimer = 0;
let applyingSaved = false;
let currentTotal = null;

function debounceCount(fn) {
  window.clearTimeout(countTimer);
  countTimer = window.setTimeout(fn, COUNT_DEBOUNCE_MS);
}

function currentFilters(page) {
  const params = new URLSearchParams(window.location.search);
  return {
    years: yearBox.getValues(),
    subjects: subjectBox.getValues(),
    topic_ids: topicWrap.hidden ? [] : topicBox.getValues(),
    languages: languageWrap.hidden ? [] : languageBox.getValues(),
    exclude_answered: Boolean(excludeInput?.checked),
    difficulty: difficultyInput?.value || "",
    page: page ?? Number(params.get("page") || 1),
  };
}

function queryString(filters) {
  const q = new URLSearchParams();
  (filters.years || []).forEach((year) => q.append("year", String(year)));
  (filters.subjects || []).forEach((subject) => q.append("subject", subject));
  (filters.topic_ids || []).forEach((id) => q.append("topic_id", String(id)));
  (filters.languages || []).forEach((lang) => q.append("language", lang));
  if (filters.exclude_answered) q.set("exclude_answered", "1");
  if (filters.difficulty) q.set("difficulty", filters.difficulty);
  if (filters.page && filters.page > 1) q.set("page", String(filters.page));
  const s = q.toString();
  return s ? `?${s}` : "";
}

function payloadFromFilters(filters) {
  return {
    years: (filters.years || []).map(Number),
    subjects: filters.subjects || [],
    topic_ids: (filters.topic_ids || []).map(Number),
    languages: filters.languages || [],
    exclude_answered: Boolean(filters.exclude_answered),
  };
}

function applyPayload(payload) {
  applyingSaved = true;
  yearBox.setValues(payload.years || []);
  subjectBox.setValues(payload.subjects || []);
  topicBox.setValues((payload.topic_ids || []).map(String));
  languageBox.setValues(payload.languages || []);
  if (excludeInput) excludeInput.checked = Boolean(payload.exclude_answered);
  applyingSaved = false;
}

function formatCount(total) {
  return Number(total || 0).toLocaleString("pt-BR");
}

function activeFilterHints(filters) {
  const hints = [];
  (filters.years || []).forEach((year) => hints.push({ key: "year", value: year, label: `Ano ${year}` }));
  (filters.subjects || []).forEach((subject) => hints.push({ key: "subject", value: subject, label: subject }));
  (filters.topic_ids || []).forEach((id) => {
    const opt = topicBox.options.find((item) => item.value === String(id));
    hints.push({ key: "topic_id", value: id, label: opt?.label || `Tópico ${id}` });
  });
  (filters.languages || []).forEach((lang) => hints.push({ key: "language", value: lang, label: lang }));
  if (filters.exclude_answered) hints.push({ key: "exclude_answered", value: "1", label: "Já respondidas" });
  if (filters.difficulty) {
    const names = { easy: "Fácil", medium: "Médio", hard: "Difícil" };
    hints.push({ key: "difficulty", value: filters.difficulty, label: names[filters.difficulty] || filters.difficulty });
  }
  return hints;
}

function snippet(text) {
  const clean = (text || "").replace(/\s+/g, " ").trim();
  const cut = clean.length > 220 ? `${clean.slice(0, 220)}...` : clean;
  return escapeHtml(cut);
}

function renderItems(items) {
  list.innerHTML = items
    .map((q) => {
      const title = q.enem_title || `Questão ${q.enem_index || q.id}`;
      return `
      <article class="card question-item">
        <div>
          <p class="question-year">${q.year}${q.enem_index ? ` · nº ${q.enem_index}` : ""}</p>
          <p class="question-statement">${snippet(q.statement || title)}</p>
          <div class="row">
            <span class="badge badge-primary">${escapeHtml(q.subject)}</span>
            ${difficultyBadge(q.difficulty)}
            ${q.language ? `<span class="badge">${escapeHtml(q.language)}</span>` : ""}
            ${q.enem_title ? `<span class="badge badge-muted">${escapeHtml(q.enem_title)}</span>` : ""}
          </div>
        </div>
        <a class="btn btn-ghost" href="/pages/questions/question.html?id=${q.id}">Abrir questão</a>
      </article>
    `;
    })
    .join("");
}

function renderPagination(page, pages) {
  if (pages <= 1) {
    pagination.innerHTML = "";
    return;
  }
  const filters = currentFilters(page);
  const prev = { ...filters, page: page - 1 };
  const next = { ...filters, page: page + 1 };
  pagination.innerHTML = `
    <a class="btn btn-ghost btn-sm ${page <= 1 ? "is-disabled" : ""}" href="${page <= 1 ? "#" : `/pages/questions/index.html${queryString(prev)}`}" ${page <= 1 ? "aria-disabled=true" : ""}>Anterior</a>
    <span class="muted">Página ${page} de ${pages}</span>
    <a class="btn btn-ghost btn-sm ${page >= pages ? "is-disabled" : ""}" href="${page >= pages ? "#" : `/pages/questions/index.html${queryString(next)}`}" ${page >= pages ? "aria-disabled=true" : ""}>Próxima</a>
  `;
}

function renderCount(total, pending = false) {
  currentTotal = total;
  if (pending) {
    countEl.innerHTML = `<span class="count-spinner" aria-hidden="true"></span> calculando...`;
    countEl.dataset.state = "loading";
    return;
  }
  countEl.dataset.state = "ready";
  countEl.textContent = `${formatCount(total)} ${total === 1 ? "questão" : "questões"}`;
}

function renderEmpty(filters) {
  const hints = activeFilterHints(filters);
  if (!hints.length) {
    emptyHint.textContent = "Não há questões com esses critérios.";
    return;
  }
  emptyHint.innerHTML = `
    Nenhuma questão com esses filtros.
    ${hints.map((hint) => `<button type="button" class="btn btn-ghost btn-sm" data-drop-filter="${hint.key}" data-drop-value="${escapeHtml(String(hint.value))}">Remover ${escapeHtml(hint.label)}</button>`).join(" ")}
  `;
}

async function refreshCount() {
  const filters = { ...currentFilters(1), page: 1 };
  renderCount(currentTotal, true);
  try {
    const data = await api.get(`/questoes/count${queryString(filters)}`);
    renderCount(data.total);
  } catch (err) {
    countEl.textContent = "—";
    showToast(err.message, "error");
  }
}

function onFiltersChanged() {
  if (applyingSaved) return;
  debounceCount(refreshCount);
}

async function loadSavedFilters(selectId) {
  try {
    const data = await api.get("/filter-sets");
    const items = data.items || [];
    savedSelect.innerHTML = `<option value="">Meus filtros salvos</option>` + items
      .map((item) => `<option value="${item.id}" ${String(item.id) === String(selectId) ? "selected" : ""}>${escapeHtml(item.name)}</option>`)
      .join("");
    savedSelect.disabled = items.length === 0;
  } catch {
    savedSelect.innerHTML = `<option value="">Meus filtros salvos</option>`;
    savedSelect.disabled = true;
  }
}

async function loadFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const meta = await api.get("/questoes/meta").catch(() => api.get("/questions/meta"));
  const years = (meta.years || []).map((year) => ({ value: String(year), label: String(year) }));
  const subjects = (meta.subjects || []).map((subject) => ({ value: subject, label: subject }));
  const topics = (meta.topics || []).map((topic) => ({ value: String(topic.id), label: topic.name }));
  const languages = (meta.languages || []).map((lang) => ({ value: lang, label: lang }));

  yearBox.setOptions(years);
  subjectBox.setOptions(subjects);
  topicBox.setOptions(topics);
  languageBox.setOptions(languages);

  topicWrap.hidden = topics.length === 0;
  languageWrap.hidden = languages.length === 0;

  yearBox.setValues(params.getAll("year"));
  subjectBox.setValues(params.getAll("subject"));
  topicBox.setValues(params.getAll("topic_id"));
  languageBox.setValues(params.getAll("language"));
  if (excludeInput) excludeInput.checked = ["1", "true", "yes"].includes((params.get("exclude_answered") || "").toLowerCase());
  if (difficultyInput) difficultyInput.value = params.get("difficulty") || "";
}

async function loadQuestions() {
  loading.hidden = false;
  empty.hidden = true;
  list.innerHTML = "";
  const filters = currentFilters();
  const qs = queryString(filters);
  try {
    const data = await api.get(`/questoes${qs}`).catch(() => api.get(`/questions${qs}`));
    const items = data.items || [];
    setQuestionQueue(
      items.map((q) => q.id),
      { ...filters, page: data.page, pages: data.pages }
    );
    loading.hidden = true;
    renderCount(data.total);
    if (!items.length) {
      empty.hidden = false;
      renderEmpty(filters);
      pagination.innerHTML = "";
      return;
    }
    renderItems(items);
    renderPagination(data.page, data.pages);
  } catch (err) {
    loading.hidden = true;
    showToast(err.message, "error");
  }
}

function pushFilters(filters) {
  const next = `/pages/questions/index.html${queryString({ ...filters, page: 1 })}`;
  window.history.pushState({ filters }, "", next);
}

document.getElementById("filters-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const filters = { ...currentFilters(), page: 1 };
  pushFilters(filters);
  loadQuestions();
});

document.getElementById("clear-filters")?.addEventListener("click", () => {
  applyingSaved = true;
  yearBox.clear();
  subjectBox.clear();
  topicBox.clear();
  languageBox.clear();
  if (excludeInput) excludeInput.checked = false;
  if (difficultyInput) difficultyInput.value = "";
  savedSelect.value = "";
  applyingSaved = false;
  const filters = { ...currentFilters(), page: 1 };
  pushFilters(filters);
  refreshCount();
  loadQuestions();
});

document.getElementById("save-filters")?.addEventListener("click", () => {
  if (!getToken()) {
    setPendingFilterSave({ filters: payloadFromFilters(currentFilters()), name: "" });
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/pages/authentication/login.html?next=${next}`;
    return;
  }
  savePanel.hidden = false;
  saveName.focus();
});

document.getElementById("confirm-save-filters")?.addEventListener("click", async () => {
  const name = saveName.value.trim();
  if (!name) {
    showToast("Dê um nome a este conjunto de filtros.", "error");
    return;
  }
  try {
    const item = await api.post("/filter-sets", {
      name,
      payload: payloadFromFilters(currentFilters()),
    });
    savePanel.hidden = true;
    saveName.value = "";
    showToast("Filtros salvos.", "success");
    await loadSavedFilters(item.item.id);
  } catch (err) {
    showToast(err.message, "error");
  }
});

savedSelect?.addEventListener("change", async () => {
  const id = savedSelect.value;
  if (!id) return;
  try {
    const data = await api.get("/filter-sets");
    const item = (data.items || []).find((row) => String(row.id) === String(id));
    if (!item) return;
    applyPayload(item.payload || {});
    const filters = { ...currentFilters(), page: 1 };
    pushFilters(filters);
    await refreshCount();
    await loadQuestions();
  } catch (err) {
    showToast(err.message, "error");
  }
});

excludeInput?.addEventListener("change", onFiltersChanged);
difficultyInput?.addEventListener("change", onFiltersChanged);

empty?.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-drop-filter]");
  if (!btn) return;
  const key = btn.dataset.dropFilter;
  const value = btn.dataset.dropValue;
  if (key === "year") yearBox.setValues(yearBox.getValues().filter((item) => item !== value));
  if (key === "subject") subjectBox.setValues(subjectBox.getValues().filter((item) => item !== value));
  if (key === "topic_id") topicBox.setValues(topicBox.getValues().filter((item) => item !== value));
  if (key === "language") languageBox.setValues(languageBox.getValues().filter((item) => item !== value));
  if (key === "exclude_answered" && excludeInput) excludeInput.checked = false;
  if (key === "difficulty" && difficultyInput) difficultyInput.value = "";
  const filters = { ...currentFilters(), page: 1 };
  pushFilters(filters);
  refreshCount();
  loadQuestions();
});

window.addEventListener("popstate", () => {
  loadFiltersFromUrl().then(() => {
    refreshCount();
    loadQuestions();
  });
});

async function init() {
  try {
    await loadFiltersFromUrl();
    const pending = consumePendingFilterSave();
    if (pending?.filters) {
      applyPayload(pending.filters);
      savePanel.hidden = false;
      if (pending.name) saveName.value = pending.name;
    }
    await loadSavedFilters();
    await loadQuestions();
  } catch (err) {
    loading.hidden = true;
    showToast(err.message, "error");
  }
}

init();
