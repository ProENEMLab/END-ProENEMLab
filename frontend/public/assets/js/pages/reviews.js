import { api } from "../api.js";

const list = document.getElementById("reviews-list");
const empty = document.getElementById("reviews-empty");
const upcoming = document.getElementById("reviews-upcoming");
const errorBox = document.getElementById("reviews-error");
const summary = document.getElementById("reviews-summary");
const start = document.getElementById("reviews-start");

const WEEKDAY = ["no domingo", "na segunda", "na terça", "na quarta", "na quinta", "na sexta", "no sábado"];

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function parseDay(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function dayLabel(iso) {
  const today = new Date();
  const startToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const tomorrow = new Date(startToday);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const day = parseDay(iso);
  if (day.getTime() === tomorrow.getTime()) return "amanhã";
  return WEEKDAY[day.getDay()];
}

function sentence(count, overdue) {
  const noun = count === 1 ? "revisão" : "revisões";
  let text = `Você tem ${count} ${noun} hoje`;
  if (overdue > 0) {
    text += ` (${overdue} ${overdue === 1 ? "atrasada" : "atrasadas"})`;
  }
  return text;
}

function emptySentence(days) {
  const bits = (days || [])
    .filter((row) => row.count > 0)
    .map((row) => `${row.count} ${dayLabel(row.date)}`);
  if (!bits.length) return "Nenhuma revisão para hoje.";
  return `Nenhuma revisão para hoje. Próximas: ${bits.join(", ")}.`;
}

async function load() {
  try {
    const today = await api.get("/reviews/today");
    const items = today.items || [];
    if (!items.length) {
      const next = await api.get("/reviews/upcoming?days=7");
      upcoming.textContent = emptySentence(next.days);
      empty.hidden = false;
      summary.hidden = true;
      start.hidden = true;
      list.innerHTML = "";
      return;
    }
    empty.hidden = true;
    summary.hidden = false;
    summary.textContent = sentence(today.count, today.overdue_count);
    start.hidden = false;
    start.href = `/pages/reviews/session.html?cycle=${items[0].cycle_id}`;
    list.innerHTML = items
      .map((item) => {
        const late = item.overdue_days > 0
          ? ` · ${item.overdue_days} ${item.overdue_days === 1 ? "dia de atraso" : "dias de atraso"}`
          : "";
        const topic = item.topic ? `<p>${escapeHtml(item.topic)}</p>` : "";
        return `
          <article class="card">
            <p class="muted">Revisão ${item.stage} de ${item.total_stages}${late}</p>
            <h2>${escapeHtml(item.subject || "Questão")}</h2>
            ${topic}
            <a class="btn btn-primary" href="/pages/reviews/session.html?cycle=${item.cycle_id}">Começar</a>
          </article>`;
      })
      .join("");
  } catch (err) {
    errorBox.hidden = false;
    errorBox.textContent = err.message;
  }
}

load();
