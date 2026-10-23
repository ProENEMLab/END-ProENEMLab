import { api } from "../api.js";
import { icon } from "../icons.js";
import { getEnemCountdown, renderCountdownMarkup } from "../enem-dates.js";
import { showToast } from "../components/toast.js";

function todayISO() {
  const d = new Date();
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

const loading = document.getElementById("dashboard-loading");
const content = document.getElementById("dashboard-content");
const modal = document.getElementById("goal-modal");
const countdownRoot = document.getElementById("enem-countdown-root");

if (countdownRoot) {
  countdownRoot.innerHTML = renderCountdownMarkup(getEnemCountdown());
}

function renderNextStep(next) {
  const el = document.getElementById("next-step");
  if (!next) {
    el.innerHTML = `
      <p class="card-title">Próximo passo</p>
      <h2>Roadmap concluído</h2>
      <p class="muted">Você finalizou os tópicos. O próximo movimento é treinar no banco de questões oficiais.</p>
      <a class="btn btn-primary" href="/pages/questions/index.html">Abrir o banco de questões</a>
    `;
    return;
  }
  el.innerHTML = `
    <p class="card-title">Próximo passo</p>
    <span class="badge badge-primary">${escapeHtml(next.subject)}</span>
    <h2 style="margin-top:16px">${escapeHtml(next.topic_name)}</h2>
    <p class="muted">Continue no tópico em que o roadmap parou — sem pular a ordem.</p>
    <a class="btn btn-primary" href="/pages/roadmap/topic.html?id=${next.topic_id}">Continuar este tópico</a>
  `;
}

function renderGoal(goal) {
  const el = document.getElementById("daily-goal");
  if (!goal) {
    el.innerHTML = `
      <p class="card-title">Meta de hoje</p>
      <h3>Nenhuma meta ainda</h3>
      <p class="muted">Um objetivo curto, para hoje — por exemplo, 15 questões de Natureza.</p>
      <button type="button" class="btn btn-ghost" data-open-goal>Definir a meta de hoje</button>
    `;
    el.querySelector("[data-open-goal]")?.addEventListener("click", () => modal.classList.add("is-open"));
    return;
  }

  el.innerHTML = `
    <p class="card-title">Meta de hoje</p>
    <label class="check-row" style="font-size:16px;color:var(--color-text-primary)">
      <input type="checkbox" id="goal-complete" ${goal.is_completed ? "checked disabled" : ""}>
      <span>${escapeHtml(goal.description)}</span>
    </label>
    <p class="muted" style="margin-top:12px">${goal.is_completed ? "Meta concluída. +15 pontos registrados." : "Marque ao concluir para ganhar pontos."}</p>
  `;

  const checkbox = el.querySelector("#goal-complete");
  checkbox?.addEventListener("change", async () => {
    if (!checkbox.checked) return;
    checkbox.disabled = true;
    try {
      await api.patch(`/goals/${goal.id}/complete`);
      showToast("Meta concluída! +15 pontos", "success");
      await loadDashboard();
    } catch (err) {
      checkbox.checked = false;
      checkbox.disabled = false;
      showToast(err.message, "error");
    }
  });
}

function renderStreak(streak) {
  const el = document.getElementById("streak-card");
  const current = streak?.current_streak ?? 0;
  const longest = streak?.longest_streak ?? 0;
  el.innerHTML = `
    <p class="card-title">Sequência</p>
    <div class="streak-value">
      ${icon("flame", { size: 28 })}
      <strong>${current}</strong>
      <span class="muted">${current === 1 ? "dia seguido" : "dias seguidos"}</span>
    </div>
    <p class="muted">Maior sequência: ${longest} ${longest === 1 ? "dia" : "dias"}</p>
  `;
}

function renderProgression(summary) {
  const el = document.getElementById("progression-card");
  if (!el) return;
  const unlocks = summary?.recent_unlocks || [];
  const suggestions = (summary?.suggestions || []).filter((item) => item.type !== "advance");
  if (!unlocks.length && !suggestions.length) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.innerHTML = `
    <p class="card-title">Progressão</p>
    <h3>Próximo nível de dificuldade</h3>
    <div class="stack">
      ${unlocks
        .map(
          (item) => `
          <p><a href="/pages/roadmap/topic.html?id=${item.topic_id}">${escapeHtml(item.topic_name)}</a> liberou um nível novo.</p>`
        )
        .join("")}
      ${suggestions
        .map(
          (item) => `
          <p><a href="/pages/roadmap/topic.html?id=${item.topic_id}">${escapeHtml(item.topic_name)}</a>: ${escapeHtml(item.message)}</p>`
        )
        .join("")}
    </div>
  `;
}

function reviewSentence(count, overdue) {
  const noun = count === 1 ? "revisão" : "revisões";
  let text = `Você tem ${count} ${noun} hoje`;
  if (overdue > 0) {
    const late = overdue === 1 ? "atrasada" : "atrasadas";
    text += ` (${overdue} ${late})`;
  }
  return text;
}

async function loadReviewCard() {
  const el = document.getElementById("review-today-card");
  if (!el) return;
  try {
    const today = await api.get("/reviews/today");
    if (!today.count) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    el.innerHTML = `
      <p class="card-title">Revisões</p>
      <h3>${reviewSentence(today.count, today.overdue_count)}</h3>
      <a class="btn btn-primary" href="/pages/reviews/index.html">Revisar agora</a>
    `;
  } catch {
    el.hidden = true;
  }
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours && minutes) return `${hours} h ${minutes} min`;
  if (hours) return `${hours} h`;
  return `${minutes} min`;
}

async function loadWeeklyCard() {
  const el = document.getElementById("weekly-report-card");
  if (!el) return;
  try {
    const report = await api.get("/reports/weekly");
    const seconds = report.net_study?.total_seconds ?? 0;
    el.hidden = false;
    el.innerHTML = `
      <p class="card-title">Relatório da semana</p>
      <p class="weekly-dash-hours">${formatDuration(seconds)}</p>
      <p class="muted">Horas líquidas de foco</p>
      <a class="btn btn-ghost" href="/pages/report/index.html">Abrir relatório</a>
    `;
  } catch {
    el.hidden = true;
  }
}

async function loadDashboard() {
  try {
    const data = await api.get("/dashboard");
    renderNextStep(data.next_step);
    renderGoal(data.daily_goal);
    renderStreak(data.streak);
    loading.hidden = true;
    content.hidden = false;
    try {
      renderProgression(await api.get("/progression/summary"));
    } catch (err) {
      showToast(err.message, "error");
    }
  } catch (err) {
    loading.hidden = true;
    content.hidden = false;
    showToast(err.message, "error");
  }
  await loadReviewCard();
  await loadWeeklyCard();
}

document.getElementById("goal-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const description = document.getElementById("goal-description").value.trim();
  if (!description) return;
  const submit = event.target.querySelector("[type=submit]");
  submit.disabled = true;
  try {
    await api.post("/goals", { description, target_date: todayISO() });
    modal.classList.remove("is-open");
    event.target.reset();
    showToast("Meta criada para hoje.", "success");
    await loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    submit.disabled = false;
  }
});

modal?.querySelectorAll("[data-close-modal]").forEach((btn) => {
  btn.addEventListener("click", () => modal.classList.remove("is-open"));
});

loadDashboard();
