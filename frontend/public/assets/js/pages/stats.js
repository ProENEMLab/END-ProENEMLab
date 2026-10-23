import { api } from "../api.js";
import { showToast } from "../components/toast.js";

const loading = document.getElementById("stats-loading");
const content = document.getElementById("stats-content");
let charts = [];

function pct(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function chartColors() {
  const styles = getComputedStyle(document.documentElement);
  return {
    primary: styles.getPropertyValue("--color-primary").trim(),
    navy: styles.getPropertyValue("--color-navy").trim(),
    danger: styles.getPropertyValue("--color-danger").trim(),
    warning: styles.getPropertyValue("--color-warning").trim(),
    text: styles.getPropertyValue("--color-text-secondary").trim(),
    border: styles.getPropertyValue("--color-border").trim(),
  };
}

function destroyCharts() {
  charts.forEach((c) => c.destroy());
  charts = [];
}

function render(data) {
  document.getElementById("overall-accuracy").textContent = pct(data.overall_accuracy);

  const subjectParam = new URLSearchParams(window.location.search).get("subject");
  const focus = document.getElementById("subject-focus");
  if (focus) {
    const row = (data.by_subject || []).find((item) => item.subject === subjectParam);
    if (subjectParam && row) {
      focus.hidden = false;
      document.getElementById("subject-focus-title").textContent = subjectParam;
      document.getElementById("subject-focus-value").textContent = pct(row.accuracy);
      document.getElementById("subject-focus-meta").textContent =
        `${row.total_attempts} ${row.total_attempts === 1 ? "tentativa" : "tentativas"} nesta matéria.`;
    } else if (subjectParam) {
      focus.hidden = false;
      document.getElementById("subject-focus-title").textContent = subjectParam;
      document.getElementById("subject-focus-value").textContent = "—";
      document.getElementById("subject-focus-meta").textContent =
        "Ainda não há tentativas suficientes nesta matéria.";
    } else {
      focus.hidden = true;
    }
  }

  const worst = document.getElementById("worst-topics");
  if (!data.worst_topics?.length) {
    worst.innerHTML = `<li class="muted">Ainda não há tentativas suficientes para ranquear tópicos.</li>`;
  } else {
    worst.innerHTML = data.worst_topics
      .map(
        (t, i) => `
        <li>
          <span><strong>${i + 1}. ${escapeHtml(t.topic_name)}</strong></span>
          <span class="badge badge-warning">${pct(t.accuracy)}</span>
        </li>
      `
      )
      .join("");
  }

  const emptyCharts = document.getElementById("stats-empty");
  const hasAttempts = (data.by_topic || []).some((t) => t.total_attempts > 0) ||
    Object.values(data.error_breakdown || {}).some((n) => n > 0);
  if (!hasAttempts && !data.overall_accuracy) {
    emptyCharts.hidden = false;
  } else {
    emptyCharts.hidden = true;
  }

  const ChartLib = window.Chart;
  if (!ChartLib) {
    showToast("Não foi possível carregar os gráficos.", "error");
    return;
  }

  const colors = chartColors();
  destroyCharts();

  const barCtx = document.getElementById("by-topic-chart");
  const topics = data.by_topic || [];
  charts.push(
    new ChartLib(barCtx, {
      type: "bar",
      data: {
        labels: topics.map((t) => t.topic_name),
        datasets: [
          {
            label: "% de acerto",
            data: topics.map((t) => Math.round(t.accuracy * 100)),
            backgroundColor: colors.primary,
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: { color: colors.text, callback: (v) => `${v}%` },
            grid: { color: colors.border },
          },
          x: {
            ticks: { color: colors.text, maxRotation: 45, minRotation: 0 },
            grid: { display: false },
          },
        },
      },
    })
  );

  const pieCtx = document.getElementById("error-chart");
  const breakdown = data.error_breakdown || { conceito: 0, atencao: 0, nao_classificado: 0 };
  charts.push(
    new ChartLib(pieCtx, {
      type: "doughnut",
      data: {
        labels: ["Falta de conceito", "Erro de atenção", "Não classificado"],
        datasets: [
          {
            data: [breakdown.conceito, breakdown.atencao, breakdown.nao_classificado],
            backgroundColor: [colors.danger, colors.warning, colors.navy],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { color: colors.text } },
        },
      },
    })
  );
}

async function load() {
  try {
    const data = await api.get("/stats/performance");
    render(data);
    loading.hidden = true;
    content.hidden = false;
  } catch (err) {
    loading.hidden = true;
    content.hidden = false;
    showToast(err.message, "error");
  }
}

document.addEventListener("proenem:themechange", () => {
  if (!content.hidden) load();
});

load();
