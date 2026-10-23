import { api } from "../api.js";
import { showToast } from "../components/toast.js";
import { icon } from "../icons.js";
import { escapeHtml, renderMarkdown } from "../markdown.js";

const params = new URLSearchParams(window.location.search);
const startId = Number(params.get("cycle"));
const loading = document.getElementById("question-loading");
const content = document.getElementById("question-content");
const errorBox = document.getElementById("session-error");

let queue = [];
let index = 0;
let current = null;
let answered = false;
let selected = null;

function formatDay(iso) {
  if (!iso) return "";
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}

function reviewMessage(result) {
  const review = result.review || {};
  if (!result.is_correct) return "Ciclo reiniciado — revisaremos amanhã";
  if (review.status === "completed") return "Ciclo concluído";
  return `Próxima revisão desta questão: ${formatDay(review.next_due_date)}`;
}

function optionClass(letter, result) {
  if (!result) return selected === letter ? "is-selected" : "";
  if (letter === result.correct_option) return "is-correct";
  if (letter === selected && !result.is_correct) return "is-wrong";
  return "";
}

function renderQuestion(payload, result = null) {
  const question = payload.question;
  document.getElementById("review-stage").textContent = `Revisão ${payload.stage} de ${payload.total_stages}`;
  document.getElementById("question-heading").textContent = question.enem_title || "Revisão";
  document.getElementById("question-meta").innerHTML = `
    <span class="badge">${question.year || ""}</span>
    <span class="badge badge-primary">${escapeHtml(question.subject || payload.subject || "")}</span>
    ${payload.topic ? `<span class="badge">${escapeHtml(payload.topic)}</span>` : ""}
  `;
  const contextEl = document.getElementById("question-context");
  if (question.context) {
    contextEl.innerHTML = renderMarkdown(question.context);
    document.getElementById("question-statement").textContent = "";
  } else {
    contextEl.innerHTML = "";
    document.getElementById("question-statement").textContent = question.statement || "";
  }
  const intro = document.getElementById("alternatives-intro");
  if (question.alternatives_introduction) {
    intro.hidden = false;
    intro.textContent = question.alternatives_introduction;
  } else {
    intro.hidden = true;
  }
  const imageWrap = document.getElementById("question-image-wrap");
  if (question.image_url) {
    imageWrap.hidden = false;
    imageWrap.innerHTML = `<img class="question-image" src="${escapeHtml(question.image_url)}" alt="Imagem da questão">`;
  } else {
    imageWrap.hidden = true;
    imageWrap.innerHTML = "";
  }
  const options = document.getElementById("options");
  options.innerHTML = (question.options || [])
    .map((opt) => `
      <label class="option-card ${optionClass(opt.letter, result)}">
        <input type="radio" name="option" value="${opt.letter}" ${selected === opt.letter ? "checked" : ""} ${result ? "disabled" : ""}>
        <span class="option-letter">${opt.letter})</span>
        <span>${escapeHtml(opt.text || "")}</span>
      </label>
    `)
    .join("");
  options.querySelectorAll(".option-card").forEach((card) => {
    card.addEventListener("click", () => {
      if (answered) return;
      selected = card.querySelector("input")?.value || null;
      options.querySelectorAll(".option-card").forEach((el) => el.classList.remove("is-selected"));
      card.classList.add("is-selected");
    });
  });
}

function showFeedback(result) {
  const banner = document.getElementById("answer-banner");
  banner.hidden = false;
  banner.className = `answer-banner ${result.is_correct ? "correct" : "incorrect"}`;
  const title = result.is_correct
    ? "Resposta correta."
    : `Resposta incorreta. Gabarito: ${result.correct_option}`;
  banner.innerHTML = `
    <span class="answer-banner-icon">${icon(result.is_correct ? "checkCircle" : "alertCircle", { size: 22 })}</span>
    <div class="answer-banner-copy"><p>${title}</p></div>
  `;
  const explanation = document.getElementById("explanation");
  explanation.hidden = false;
  explanation.innerHTML = `
    <h3>Gabarito</h3>
    <p>${escapeHtml(result.explanation_text || "")}</p>
  `;
  const status = document.getElementById("review-status");
  status.hidden = false;
  status.textContent = reviewMessage(result);
  document.getElementById("submit-answer").hidden = true;
  document.getElementById("next-review").hidden = false;
}

async function showCurrent() {
  answered = false;
  selected = null;
  document.getElementById("answer-banner").hidden = true;
  document.getElementById("explanation").hidden = true;
  document.getElementById("review-status").hidden = true;
  document.getElementById("submit-answer").hidden = false;
  document.getElementById("submit-answer").disabled = false;
  document.getElementById("next-review").hidden = true;
  const item = queue[index];
  current = await api.get(`/reviews/${item.cycle_id}`);
  if (current.question?.correct_option || current.question?.explanation_text) {
    throw new Error("A revisão chegou com o gabarito antes da resposta.");
  }
  renderQuestion(current);
  loading.hidden = true;
  content.hidden = false;
}

async function submitAnswer() {
  if (!selected) {
    showToast("Selecione uma alternativa.", "error");
    return;
  }
  const button = document.getElementById("submit-answer");
  button.disabled = true;
  try {
    const result = await api.post(`/reviews/${current.cycle_id}/answer`, { selected_option: selected });
    answered = true;
    renderQuestion(current, result);
    showFeedback(result);
    window.dispatchEvent(new CustomEvent("proenem:reviews-changed"));
  } catch (err) {
    button.disabled = false;
    showToast(err.message, "error");
  }
}

function goNext() {
  index += 1;
  if (index >= queue.length) {
    window.location.href = "/pages/reviews/index.html";
    return;
  }
  showCurrent().catch((err) => {
    errorBox.hidden = false;
    errorBox.textContent = err.message;
  });
}

async function init() {
  try {
    const today = await api.get("/reviews/today");
    queue = today.items || [];
    if (!queue.length) {
      window.location.replace("/pages/reviews/index.html");
      return;
    }
    const found = queue.findIndex((item) => item.cycle_id === startId);
    index = found >= 0 ? found : 0;
    await showCurrent();
  } catch (err) {
    loading.hidden = true;
    errorBox.hidden = false;
    errorBox.textContent = err.message;
  }
}

document.getElementById("submit-answer")?.addEventListener("click", submitAnswer);
document.getElementById("next-review")?.addEventListener("click", goNext);
init();
