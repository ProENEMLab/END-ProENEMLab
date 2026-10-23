import { api } from "../api.js";

const MONTHS = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];
const DAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

const errorBox = document.getElementById("report-error");
const statusBox = document.getElementById("report-status");
const body = document.getElementById("report-body");
const toolbar = document.getElementById("report-toolbar");
const prevButton = document.getElementById("week-prev");
const nextButton = document.getElementById("week-next");

let liveWeek = null;
let selectedWeek = null;
let historyWeeks = [];

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function parseISO(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function toISO(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function addDays(iso, days) {
  const date = parseISO(iso);
  date.setDate(date.getDate() + days);
  return toISO(date);
}

function formatRange(startIso, endIso) {
  const start = parseISO(startIso);
  const end = parseISO(endIso);
  if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
    return `${start.getDate()}–${end.getDate()} de ${MONTHS[start.getMonth()]} de ${start.getFullYear()}`;
  }
  return `${start.getDate()} de ${MONTHS[start.getMonth()]} a ${end.getDate()} de ${MONTHS[end.getMonth()]} de ${end.getFullYear()}`;
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours && minutes) return `${hours} h ${minutes} min`;
  if (hours) return `${hours} h`;
  return `${minutes} min`;
}

function percent(value) {
  return `${Math.round(Number(value) * 100)}%`;
}

function signed(delta) {
  const number = Number(delta);
  if (number > 0) return `+${number}`;
  return String(number);
}

function showError(message) {
  errorBox.hidden = false;
  errorBox.textContent = message;
}

function compareText(current, previous) {
  const delta = current - previous;
  if (delta === 0) return "igual à semana passada";
  const direction = delta > 0 ? "a mais" : "a menos";
  const arrow = delta > 0 ? "↑" : "↓";
  return `${arrow} ${formatDuration(Math.abs(delta))} ${direction} vs semana passada`;
}

function plannedText(total, planned) {
  if (!planned) return "nada planejado no calendário";
  return `${Math.round((total / planned) * 100)}% do planejado`;
}

function bars(rows, labelOf) {
  if (!rows.length) {
    return `<p class="muted">Nenhum foco fechado nesta semana.</p>`;
  }
  const max = Math.max(1, ...rows.map((row) => row.seconds));
  return rows
    .map((row) => {
      const height = Math.max(2, Math.round((row.seconds / max) * 100));
      const label = labelOf(row);
      return `<div class="report-bar">
        <span class="report-bar-value">${formatDuration(row.seconds)}</span>
        <div class="report-bar-track" aria-hidden="true"><div class="report-bar-fill" style="height:${height}%"></div></div>
        <span class="report-bar-label">${escapeHtml(label)}</span>
      </div>`;
    })
    .join("");
}

function baselineText(item) {
  if (item.baseline === "cumulative") return "comparado ao histórico anterior";
  return "comparado à semana anterior";
}

function actionLink(action) {
  if (action.type === "practice_topic") {
    return `<a class="btn btn-ghost btn-sm" href="/pages/roadmap/topic.html?id=${action.topic_id}">Praticar este tópico</a>`;
  }
  if (action.type === "review_due") {
    const noun = action.count === 1 ? "revisão pendente" : "revisões pendentes";
    return `<a class="btn btn-ghost btn-sm" href="/pages/reviews/index.html">${action.count} ${noun}</a>`;
  }
  return "";
}

function comparedCard(item, tone) {
  const word = tone === "up" ? "Evoluiu" : "Regrediu";
  const arrow = tone === "up" ? "↑" : "↓";
  const actions = (item.actions || []).map(actionLink).join("");
  return `<article class="report-topic report-topic-${tone}">
    <p class="report-topic-status"><span aria-hidden="true">${arrow}</span> ${word}</p>
    <h3>${escapeHtml(item.name)}</h3>
    <p class="muted">${escapeHtml(item.subject || "")}</p>
    <p>${percent(item.previous_accuracy)} → ${percent(item.accuracy)} <span class="muted">(${signed(item.delta_pp)} pp, ${item.answers} respostas, ${baselineText(item)})</span></p>
    ${actions ? `<div class="report-actions">${actions}</div>` : ""}
  </article>`;
}

function fillCompared(id, rows, tone, emptyText) {
  const target = document.getElementById(id);
  if (!rows.length) {
    target.innerHTML = `<p class="muted">${emptyText}</p>`;
    return;
  }
  target.innerHTML = rows.map((row) => comparedCard(row, tone)).join("");
}

function renderTrend(weeks) {
  const target = document.getElementById("chart-trend");
  const max = Math.max(1, ...weeks.map((week) => week.net_seconds));
  target.innerHTML = weeks
    .map((week) => {
      const height = Math.max(2, Math.round((week.net_seconds / max) * 100));
      const [year, month, day] = week.week_start.split("-");
      const label = `${day}/${month}`;
      const description = `Semana de ${day}/${month}/${year}: ${formatDuration(week.net_seconds)}, ${week.evolved_count} evoluíram, ${week.regressed_count} regrediram`;
      const current = week.week_start === selectedWeek ? ' aria-current="true"' : "";
      return `<button type="button" class="report-trend-bar" data-week="${week.week_start}" aria-label="${escapeHtml(description)}"${current}>
        <span class="report-bar-value">${week.evolved_count}↑ ${week.regressed_count}↓</span>
        <span class="report-bar-track" aria-hidden="true"><span class="report-bar-fill" style="height:${height}%"></span></span>
        <span class="report-bar-label">${label}</span>
      </button>`;
    })
    .join("");
  target.querySelectorAll("[data-week]").forEach((button) => {
    button.addEventListener("click", () => loadWeek(button.dataset.week));
  });
}

function render(report) {
  selectedWeek = report.week_start;
  document.getElementById("report-week").textContent = formatRange(report.week_start, report.week_end);
  document.getElementById("report-partial").hidden = !report.is_partial;
  nextButton.disabled = report.week_start === liveWeek;
  const net = report.net_study;
  document.getElementById("report-hours").textContent = formatDuration(net.total_seconds);
  document.getElementById("report-compare").textContent = compareText(
    net.total_seconds,
    net.previous_week_seconds
  );
  document.getElementById("report-planned").textContent = plannedText(
    net.total_seconds,
    net.planned_seconds
  );
  const accuracy = percent(report.totals.accuracy);
  const answers = report.totals.answers;
  const answerNoun = answers === 1 ? "resposta" : "respostas";
  document.getElementById("report-totals").textContent = `${answers} ${answerNoun} · ${accuracy} de acerto`;
  const interruptions = Number(report.focus_interruptions || 0);
  const interruptionNoun = interruptions === 1 ? "interrupção" : "interrupções";
  document.getElementById("report-interruptions").textContent =
    `${interruptions} ${interruptionNoun} do Foco Total`;

  const empty = answers === 0 && net.total_seconds === 0;
  document.getElementById("report-empty").hidden = !empty;
  document.getElementById("report-detail").hidden = empty;
  if (historyWeeks.length) renderTrend(historyWeeks);
  if (empty) return;

  const dayChart = document.getElementById("chart-days");
  dayChart.innerHTML = bars(net.by_day, (row) => DAY_LABELS[parseISO(row.date).getDay() === 0 ? 6 : parseISO(row.date).getDay() - 1]);
  dayChart.setAttribute(
    "aria-label",
    net.by_day
      .map((row, index) => `${DAY_LABELS[index]} ${formatDuration(row.seconds)}`)
      .join(", ")
  );
  const subjectChart = document.getElementById("chart-subjects");
  subjectChart.innerHTML = bars(net.by_subject, (row) => row.name);
  if (net.by_subject.length) {
    subjectChart.setAttribute(
      "aria-label",
      net.by_subject.map((row) => `${row.name} ${formatDuration(row.seconds)}`).join(", ")
    );
  }

  fillCompared("evolved-list", report.topics.evolved, "up", "Nenhum tópico evoluiu o suficiente nesta semana.");
  fillCompared(
    "regressed-list",
    report.topics.regressed,
    "down",
    "Nenhum tópico regrediu o suficiente nesta semana."
  );
  renderPlain("stable-list", report.topics.stable, (item) => {
    return `${escapeHtml(item.name)} · ${percent(item.previous_accuracy)} → ${percent(item.accuracy)} (${signed(item.delta_pp)} pp)`;
  });
  renderPlain("new-list", report.topics.new, (item) => {
    return `${escapeHtml(item.name)} · ${escapeHtml(item.subject)} · ${percent(item.accuracy)} em ${item.answers} respostas`;
  });
  renderPlain("insufficient-list", report.topics.insufficient_data, (item) => {
    const noun = item.answers === 1 ? "resposta" : "respostas";
    return `${escapeHtml(item.name)} · ${item.answers} ${noun}`;
  });
  document.getElementById("stable-count").textContent = `(${report.topics.stable.length})`;
  document.getElementById("new-count").textContent = `(${report.topics.new.length})`;
  document.getElementById("insufficient-count").textContent = `(${report.topics.insufficient_data.length})`;
}

function renderPlain(id, rows, line) {
  const target = document.getElementById(id);
  if (!rows.length) {
    target.innerHTML = `<p class="muted">Nenhum tópico neste grupo.</p>`;
    return;
  }
  target.innerHTML = rows.map((row) => `<p>${line(row)}</p>`).join("");
}

async function loadWeek(weekStart) {
  errorBox.hidden = true;
  statusBox.hidden = false;
  statusBox.textContent = "Carregando relatório...";
  try {
    const report =
      weekStart && weekStart !== liveWeek
        ? await api.get(`/reports/weekly/${weekStart}`)
        : await api.get("/reports/weekly");
    if (!liveWeek) liveWeek = report.is_partial ? report.week_start : liveWeek;
    body.hidden = false;
    statusBox.hidden = true;
    render(report);
    const url = new URL(window.location.href);
    if (report.week_start === liveWeek) url.searchParams.delete("week");
    else url.searchParams.set("week", report.week_start);
    window.history.replaceState({}, "", url);
  } catch (err) {
    statusBox.hidden = true;
    showError(err.message);
  }
}

function shift(days) {
  if (!selectedWeek) return;
  if (days > 0 && nextButton.disabled) return;
  loadWeek(addDays(selectedWeek, days));
}

prevButton.addEventListener("click", () => shift(-7));
nextButton.addEventListener("click", () => shift(7));
toolbar.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    shift(-7);
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    shift(7);
  }
});

async function start() {
  const requested = new URLSearchParams(window.location.search).get("week");
  try {
    const [live, history] = await Promise.all([
      api.get("/reports/weekly"),
      api.get("/reports/weekly/history?limit=8"),
    ]);
    liveWeek = live.week_start;
    historyWeeks = history.weeks || [];
    body.hidden = false;
    statusBox.hidden = true;
    if (requested && requested !== liveWeek) {
      await loadWeek(requested);
    } else {
      render(live);
    }
  } catch (err) {
    statusBox.hidden = true;
    showError(err.message);
  }
}

start();
