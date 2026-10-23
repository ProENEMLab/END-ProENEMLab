import { api } from "../api.js";
import { cacheRoadmap } from "../session.js";
import { showToast } from "../components/toast.js";

const STATUS_LABEL = {
  not_started: "Não iniciado",
  in_progress: "Em progresso",
  completed: "Concluído",
};

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

const STATUS_BADGE = {
  not_started: "badge-muted",
  in_progress: "badge-primary",
  completed: "badge-success",
};

const loading = document.getElementById("roadmap-loading");
const content = document.getElementById("roadmap-content");

function formatDay(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("pt-BR").format(date);
}

function sourceLine(version) {
  if (!version) return "";
  const years = version.editions || [];
  const span = years.length ? `${years[0]}–${years[years.length - 1]}` : "";
  const when = formatDay(version.activated_at);
  return `Baseado nas provas do ENEM ${span} · ${version.edital} · atualizado em ${when}`;
}

function incidenceLevel(topic, topics) {
  const incidence = topic.incidence;
  if (!incidence) return null;
  const weights = topics
    .map((item) => item.incidence?.weight || 0)
    .filter((weight) => weight > 0)
    .sort((left, right) => left - right);
  if (incidence.low_incidence || !incidence.weight || !weights.length) return "Baixa";
  const rank = weights.filter((weight) => weight <= incidence.weight).length / weights.length;
  if (rank > 2 / 3) return "Alta";
  if (rank > 1 / 3) return "Média";
  return "Baixa";
}

function incidenceBadge(topic, topics) {
  const level = incidenceLevel(topic, topics);
  if (!level) {
    return `<span class="badge badge-muted">${topic.inep_incidence ?? "—"}% INEP</span>`;
  }
  const percent = (topic.incidence.weight * 100).toFixed(1).replace(".", ",");
  const tone = level === "Alta" ? "badge-warning" : level === "Média" ? "badge-primary" : "badge-muted";
  return `<span class="badge ${tone}" title="${percent}% das questões">${level}</span>`;
}

function render(topics) {
  const completed = topics.filter((t) => t.status === "completed").length;
  const percent = topics.length ? Math.round((completed / topics.length) * 100) : 0;

  document.getElementById("progress-label").textContent = `${completed} de ${topics.length} tópicos concluídos`;
  document.getElementById("progress-percent").textContent = `${percent}%`;
  document.getElementById("progress-fill").style.width = `${percent}%`;

  const list = document.getElementById("topic-list");
  if (!topics.length) {
    list.innerHTML = `<div class="card empty-state"><h3>Nenhum tópico</h3><p>O roadmap ainda não foi carregado.</p></div>`;
    return;
  }

  list.innerHTML = topics
    .map(
      (topic, index) => `
      <div class="topic-block">
        <a class="card topic-item" href="/pages/roadmap/topic.html?id=${topic.id}">
          <div class="row">
            <span class="topic-index">${index + 1}</span>
            <div>
              <h3>${escapeHtml(topic.name)}</h3>
              <span class="badge">${escapeHtml(topic.subject)}</span>
              ${incidenceBadge(topic, topics)}
            </div>
          </div>
          <span class="badge ${STATUS_BADGE[topic.status] || "badge-muted"}">${STATUS_LABEL[topic.status] || topic.status}</span>
        </a>
        ${
          topic.incidence?.reason
            ? `<details class="topic-reason"><summary>Por que esta posição</summary><p>${escapeHtml(topic.incidence.reason)}</p></details>`
            : ""
        }
      </div>
    `
    )
    .join("");
}

function showVersion(version) {
  const source = document.getElementById("roadmap-source");
  const line = sourceLine(version);
  source.hidden = !line;
  source.textContent = line;
  document.getElementById("btn-refresh-incidence").hidden = Boolean(version);
}

async function showNotice() {
  const banner = document.getElementById("roadmap-notice");
  try {
    const data = await api.get("/roadmap/notices");
    const notice = (data.notices || [])[0];
    if (!notice) {
      banner.hidden = true;
      return;
    }
    document.getElementById("roadmap-notice-text").textContent = notice.payload?.message || "";
    banner.hidden = false;
    document.getElementById("roadmap-notice-dismiss").onclick = async () => {
      await api.post(`/roadmap/notices/${notice.id}/seen`, {});
      banner.hidden = true;
    };
  } catch {
    banner.hidden = true;
  }
}

async function load() {
  try {
    const data = await api.get("/roadmap");
    const topics = data.topics || [];
    cacheRoadmap(topics);
    showVersion(data.roadmap_version);
    render(topics);
    showNotice();
    loading.hidden = true;
    content.hidden = false;
  } catch (err) {
    loading.hidden = true;
    content.hidden = false;
    showToast(err.message, "error");
  }
}

document.getElementById("btn-refresh-incidence").addEventListener("click", async () => {
  try {
    await api.post("/incidence/refresh", {});
    await load();
    showToast("Incidência atualizada com as provas disponíveis.", "success");
  } catch (err) {
    showToast(err.message, "error");
  }
});

load();
