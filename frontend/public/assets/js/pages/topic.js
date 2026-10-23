import { api } from "../api.js";
import { cacheRoadmap, getCachedRoadmap } from "../session.js";
import { showToast } from "../components/toast.js";

const STATUS_LABEL = {
  not_started: "Não iniciado",
  in_progress: "Em progresso",
  completed: "Concluído",
};

const params = new URLSearchParams(window.location.search);
const topicId = Number(params.get("id"));
const loading = document.getElementById("topic-loading");
const content = document.getElementById("topic-content");

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

async function fetchTopic() {
  let topics = getCachedRoadmap();
  if (!topics || topics.some((topic) => !("incidence" in topic))) {
    const data = await api.get("/roadmap");
    topics = data.topics || [];
    cacheRoadmap(topics);
  }
  return (topics || []).find((t) => t.id === topicId);
}

function renderTopic(topic) {
  document.getElementById("topic-name").textContent = topic.name;
  const subjectEl = document.getElementById("topic-subject");
  subjectEl.dataset.subject = topic.subject;
  subjectEl.textContent = topic.subject;
  document.getElementById("topic-description").textContent =
    topic.description || "Sem descrição cadastrada.";
  const incidence = document.getElementById("topic-incidence");
  if (topic.incidence?.reason) {
    incidence.hidden = false;
    incidence.textContent = topic.incidence.reason;
  } else {
    incidence.hidden = true;
    incidence.textContent = "";
  }
  document.getElementById("topic-status").textContent = STATUS_LABEL[topic.status] || topic.status;
  document.getElementById("practice-link").href = `/pages/questions/index.html?topic_id=${topic.id}`;
  loadProgression();

  const inProgress = document.getElementById("btn-in-progress");
  const completed = document.getElementById("btn-completed");
  inProgress.disabled = topic.status === "in_progress";
  completed.disabled = topic.status === "completed";
}

const LEVELS = [
  { id: "easy", label: "Fácil" },
  { id: "medium", label: "Médio" },
  { id: "hard", label: "Difícil" },
];

let activeLevel = "easy";

function percentText(accuracy) {
  return `${Math.round((accuracy || 0) * 100)}%`;
}

function progressText(block) {
  if (!block || block.status !== "unlocked" || !block.to_unlock_next) return "";
  const needed = block.to_unlock_next.needed_attempts;
  const done = block.attempts_in_window || 0;
  const target = Math.round((block.to_unlock_next.needed_accuracy || 0.8) * 100);
  return `${done}/${needed} respostas · ${percentText(block.accuracy)} (precisa de ${target}%)`;
}

async function loadLevelQuestions(level) {
  const list = document.getElementById("level-question-list");
  if (!list) return;
  list.innerHTML = `<p class="muted">Carregando questões...</p>`;
  try {
    const data = await api.get(`/progression/topics/${topicId}/questions?level=${level}`);
    const items = data.questions || [];
    if (!items.length) {
      list.innerHTML = `<p class="muted">Não há questões neste nível. O banco livre continua aberto.</p>`;
      return;
    }
    list.innerHTML = items
      .map(
        (question) => `
        <a class="card question-item" href="/pages/questions/question.html?id=${question.id}">
          <p class="question-year">${question.year}${question.enem_index ? ` · nº ${question.enem_index}` : ""}</p>
          <p>${escapeHtml((question.statement || "").slice(0, 180))}</p>
        </a>`
      )
      .join("");
  } catch (err) {
    list.innerHTML = "";
    showToast(err.message, "error");
  }
}

function renderTracks(data) {
  const root = document.getElementById("level-tracks");
  if (!root) return;
  activeLevel = data.unlocked_level || "easy";
  const current = data.levels?.[activeLevel];
  root.innerHTML = `
    <div class="level-tabs" role="tablist">
      ${LEVELS.map((level) => {
        const block = data.levels?.[level.id] || { status: "locked" };
        const locked = block.status !== "unlocked";
        const pressed = level.id === activeLevel;
        return `<button type="button" class="btn ${pressed ? "btn-primary" : "btn-ghost"} level-tab" role="tab" data-level="${level.id}" aria-pressed="${pressed}" ${locked ? "disabled" : ""}>${locked ? "Travado · " : ""}${level.label}</button>`;
      }).join("")}
    </div>
    <div class="level-progress">
      <p>${escapeHtml(data.suggestion?.message || "")}</p>
      ${
        current?.to_unlock_next
          ? `<p class="muted">${escapeHtml(progressText(current))}</p>
             <div class="progress-bar" aria-hidden="true"><span style="width:${Math.min(100, Math.round(((current.attempts_in_window || 0) / (current.to_unlock_next.needed_attempts || 1)) * 100))}%"></span></div>`
          : ""
      }
    </div>
    <div id="level-question-list" class="level-list"></div>
  `;
  root.querySelectorAll("[data-level]").forEach((button) => {
    button.addEventListener("click", async () => {
      activeLevel = button.dataset.level;
      root.querySelectorAll("[data-level]").forEach((item) => {
        const pressed = item.dataset.level === activeLevel;
        item.setAttribute("aria-pressed", String(pressed));
        item.classList.toggle("btn-primary", pressed);
        item.classList.toggle("btn-ghost", !pressed);
      });
      await loadLevelQuestions(activeLevel);
    });
  });
  loadLevelQuestions(activeLevel);
}

async function loadProgression() {
  try {
    const data = await api.get(`/progression/topics/${topicId}`);
    renderTracks(data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

document.getElementById("btn-practice-level").addEventListener("click", async () => {
  try {
    const data = await api.get(`/progression/topics/${topicId}/practice`);
    if (!data.question) {
      showToast("Não há questão nova neste nível. O banco livre continua aberto.", "error");
      return;
    }
    window.location.href = `/pages/questions/question.html?id=${data.question.id}`;
  } catch (err) {
    showToast(err.message, "error");
  }
});

async function updateStatus(status) {
  try {
    const data = await api.patch(`/roadmap/topics/${topicId}/status`, { status });
    const topic = data.topic;
    const cached = getCachedRoadmap() || [];
    cacheRoadmap(cached.map((t) => (t.id === topic.id ? { ...t, ...topic } : t)));
    renderTopic({ ...topic });
    showToast("Status atualizado.", "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderNotes(notes) {
  const list = document.getElementById("notes-list");
  if (!notes.length) {
    list.innerHTML = `<div class="empty-state"><h3>Nenhuma anotação</h3><p>Registre o que acabou de estudar para revisar depois.</p></div>`;
    return;
  }

  list.innerHTML = notes
    .map(
      (note) => `
      <article class="card note-card" data-note-id="${note.id}">
        <p class="note-content">${escapeHtml(note.content)}</p>
        <p class="note-meta">Atualizada em ${formatDate(note.updated_at)}</p>
        <div class="note-actions">
          <button type="button" class="btn btn-ghost btn-sm" data-edit="${note.id}">Editar</button>
          <button type="button" class="btn btn-danger btn-sm" data-delete="${note.id}">Excluir</button>
        </div>
      </article>
    `
    )
    .join("");
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function loadNotes() {
  const data = await api.get(`/topics/${topicId}/notes`);
  renderNotes(data.notes || []);
}

document.getElementById("btn-in-progress")?.addEventListener("click", () => updateStatus("in_progress"));
document.getElementById("btn-completed")?.addEventListener("click", () => updateStatus("completed"));

document.getElementById("note-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const textarea = document.getElementById("note-content");
  const contentValue = textarea.value.trim();
  if (!contentValue) return;
  try {
    await api.post(`/topics/${topicId}/notes`, { content: contentValue });
    textarea.value = "";
    showToast("Anotação salva.", "success");
    await loadNotes();
  } catch (err) {
    showToast(err.message, "error");
  }
});

document.getElementById("notes-list")?.addEventListener("click", async (event) => {
  const editId = event.target.dataset.edit;
  const deleteId = event.target.dataset.delete;
  const card = event.target.closest("[data-note-id]");
  if (!card) return;
  const noteId = card.dataset.noteId;

  if (deleteId) {
    if (!confirm("Excluir esta anotação?")) return;
    try {
      await api.del(`/notes/${noteId}`);
      showToast("Anotação excluída.", "success");
      await loadNotes();
    } catch (err) {
      showToast(err.message, "error");
    }
    return;
  }

  if (editId) {
    const current = card.querySelector(".note-content").textContent;
    const next = prompt("Editar anotação:", current);
    if (next == null) return;
    const contentValue = next.trim();
    if (!contentValue) return;
    try {
      await api.put(`/notes/${noteId}`, { content: contentValue });
      showToast("Anotação atualizada.", "success");
      await loadNotes();
    } catch (err) {
      showToast(err.message, "error");
    }
  }
});

async function init() {
  if (!topicId) {
    window.location.replace("/pages/roadmap/index.html");
    return;
  }
  try {
    const topic = await fetchTopic();
    if (!topic) {
      showToast("Tópico não encontrado.", "error");
      window.location.replace("/pages/roadmap/index.html");
      return;
    }
    renderTopic(topic);
    await loadNotes();
    loading.hidden = true;
    content.hidden = false;
  } catch (err) {
    loading.hidden = true;
    content.hidden = false;
    showToast(err.message, "error");
  }
}

init();
