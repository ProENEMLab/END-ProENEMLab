import { api } from "../api.js";
import { getQuestionQueue } from "../session.js";
import { escapeHtml, renderMarkdown } from "../markdown.js";
import { showToast } from "../components/toast.js";
import { icon } from "../icons.js";
import { difficultyBadge } from "../difficulty.js";

const params = new URLSearchParams(window.location.search);
const questionId = Number(params.get("id"));
const loading = document.getElementById("question-loading");
const content = document.getElementById("question-content");

let currentQuestion = null;
let answered = false;

function optionClass(letter, result, selected) {
  if (!result) return selected === letter ? "is-selected" : "";
  if (letter === result.correct_option) return "is-correct";
  if (letter === selected && !result.is_correct) return "is-wrong";
  return "";
}

function renderFiles(urls) {
  const wrap = document.getElementById("question-files");
  const extra = (urls || []).slice(1);
  if (!extra.length) {
    wrap.hidden = true;
    wrap.innerHTML = "";
    return;
  }
  wrap.hidden = false;
  wrap.innerHTML = extra
    .map((url) => `<img class="question-image" src="${escapeHtml(url)}" alt="Anexo da questão">`)
    .join("");
}

function renderQuestion(question, result = null, selected = null) {
  const heading = question.enem_title || (question.enem_index ? `Questão ${question.enem_index}` : "Questão");
  document.getElementById("question-heading").textContent = heading;
  document.getElementById("question-meta").innerHTML = `
    <span class="badge">${question.year}</span>
    <span class="badge badge-primary">${escapeHtml(question.subject)}</span>
    ${difficultyBadge(question.difficulty)}
    ${question.language ? `<span class="badge">${escapeHtml(question.language)}</span>` : ""}
  `;
  document.getElementById("question-meta").classList.add("question-meta-row");

  const contextEl = document.getElementById("question-context");
  if (question.context) {
    contextEl.innerHTML = renderMarkdown(question.context);
  } else {
    contextEl.innerHTML = "";
    document.getElementById("question-statement").textContent = question.statement || "";
  }
  if (question.context) {
    document.getElementById("question-statement").textContent = "";
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
    imageWrap.innerHTML = `<img class="question-image" src="${question.image_url}" alt="Imagem da questão">`;
  } else {
    imageWrap.hidden = true;
    imageWrap.innerHTML = "";
  }
  renderFiles(question.files);

  const source = document.getElementById("question-source");
  if (source) {
    source.innerHTML = question.source === "enem-api"
      ? `Questão do ENEM (INEP), via <a href="https://enem.dev" target="_blank" rel="noopener">enem-api</a> · GPL-2.0.`
      : "Questão de treino do ProENEM Lab.";
  }

  const options = document.getElementById("options");
  options.innerHTML = (question.options || [])
    .map((opt) => {
      const file = opt.file_url
        ? `<img class="question-image" src="${escapeHtml(opt.file_url)}" alt="Alternativa ${opt.letter}">`
        : "";
      return `
      <label class="option-card ${optionClass(opt.letter, result, selected)}">
        <input type="radio" name="option" value="${opt.letter}" ${selected === opt.letter ? "checked" : ""} ${result ? "disabled" : ""}>
        <span class="option-letter">${opt.letter})</span>
        <span>${escapeHtml(opt.text || "")}${file}</span>
      </label>
    `;
    })
    .join("");

  options.querySelectorAll(".option-card").forEach((card) => {
    card.addEventListener("click", () => {
      if (answered) return;
      options.querySelectorAll(".option-card").forEach((el) => el.classList.remove("is-selected"));
      card.classList.add("is-selected");
    });
  });
}

function renderResult(result, selected) {
  const banner = document.getElementById("answer-banner");
  banner.hidden = false;
  banner.className = `answer-banner ${result.is_correct ? "correct" : "incorrect"}`;
  const action = result.suggested_action || {};
  const title = result.is_correct
    ? "Resposta correta."
    : `Resposta incorreta. Gabarito: ${result.correct_option}`;
  const actionMarkup = suggestedActionMarkup(action);
  banner.innerHTML = `
    <span class="answer-banner-icon">${icon(result.is_correct ? "checkCircle" : "alertCircle", { size: 22, label: result.is_correct ? "Acerto" : "Erro" })}</span>
    <div class="answer-banner-copy">
      <p>${title}</p>
    </div>
    <div class="answer-banner-actions">${actionMarkup}</div>
  `;

  const explanation = document.getElementById("explanation");
  explanation.innerHTML = `
    <h3>Gabarito</h3>
    <p>${escapeHtml(result.explanation_text || "")}</p>
    ${result.explanation_image_url ? `<img class="question-image" src="${result.explanation_image_url}" alt="Imagem do gabarito">` : ""}
    ${result.explanation_video_url ? `<p><a href="${result.explanation_video_url}" target="_blank" rel="noopener">Assistir vídeo de correção</a></p>` : ""}
  `;
  explanation.hidden = action.id === "explanation";

  const prompt = document.getElementById("error-prompt");
  if (!result.is_correct && result.attempt_id) {
    prompt.hidden = false;
    prompt.dataset.attemptId = result.attempt_id;
  } else {
    prompt.hidden = true;
  }

  document.getElementById("submit-answer").hidden = true;
  document.getElementById("next-question").hidden = false;
  bindSuggestedActions(action);
}

function suggestedActionMarkup(action) {
  if (action.id === "explanation") {
    return `<button type="button" class="btn btn-ghost btn-sm" data-suggested="explanation">Ver gabarito e comentário</button>`;
  }
  if (action.id === "subject_stats" && action.subject) {
    const href = `/pages/stats/index.html?subject=${encodeURIComponent(action.subject)}`;
    return `<a class="btn btn-ghost btn-sm" href="${href}">${escapeHtml(action.label || "Ver desempenho")}</a>`;
  }
  return `<button type="button" class="btn btn-ghost btn-sm" data-suggested="next">${escapeHtml(action.label || "Próxima questão")}</button>`;
}

function bindSuggestedActions(action) {
  const banner = document.getElementById("answer-banner");
  banner.querySelector("[data-suggested=explanation]")?.addEventListener("click", () => {
    const explanation = document.getElementById("explanation");
    explanation.hidden = false;
    explanation.scrollIntoView({ behavior: "smooth", block: "start" });
    explanation.focus?.();
  });
  banner.querySelector("[data-suggested=next]")?.addEventListener("click", goNext);
}

async function submitAnswer() {
  const selected = document.querySelector("input[name=option]:checked")?.value;
  if (!selected) {
    showToast("Selecione uma alternativa.", "error");
    return;
  }
  const btn = document.getElementById("submit-answer");
  btn.disabled = true;
  try {
    const result = await api.post(`/questions/${questionId}/answer`, { selected_option: selected });
    answered = true;
    renderQuestion(currentQuestion, result, selected);
    renderResult(result, selected);
    await showUnlock(result);
    await showReviewReminder(result);
    if (result.is_correct) {
      showToast("Você ganhou +5 pontos.", "success");
    }
  } catch (err) {
    btn.disabled = false;
    showToast(err.message, "error");
  }
}

async function showUnlock(result) {
  if (!currentQuestion?.topic_id) return;
  try {
    const status = await api.get(`/progression/topics/${currentQuestion.topic_id}`);
    if (status.suggestion?.type !== "advance") return;
    const banner = document.getElementById("answer-banner");
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = status.suggestion.message;
    banner.querySelector(".answer-banner-copy")?.append(note);
    showToast(status.suggestion.message, "success");
  } catch (err) {
    if (result) showToast(err.message, "error");
  }
}

async function showReviewReminder(result) {
  if (result.is_correct) return;
  try {
    const history = await api.get(`/reviews/history?question_id=${questionId}`);
    const active = (history.cycles || []).find((cycle) => cycle.status === "active");
    if (!active) return;
    const banner = document.getElementById("answer-banner");
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "Vamos te lembrar de revisar esta questão amanhã.";
    banner.querySelector(".answer-banner-copy")?.append(note);
    window.dispatchEvent(new CustomEvent("proenem:reviews-changed"));
  } catch {

  }
}

function goNext() {
  const queue = getQuestionQueue();
  const ids = queue?.ids || [];
  const index = ids.indexOf(questionId);
  if (index >= 0 && index < ids.length - 1) {
    window.location.href = `/pages/questions/question.html?id=${ids[index + 1]}`;
    return;
  }
  window.location.href = "/pages/questions/index.html";
}

document.getElementById("submit-answer")?.addEventListener("click", submitAnswer);
document.getElementById("next-question")?.addEventListener("click", goNext);

document.getElementById("error-prompt")?.addEventListener("click", async (event) => {
  const type = event.target.dataset.errorType;
  if (!type) return;
  const attemptId = document.getElementById("error-prompt").dataset.attemptId;
  try {
    await api.patch(`/attempts/${attemptId}/error-type`, { error_type: type });
    showToast("Erro classificado. Isso ajuda nas estatísticas.", "success");
    document.getElementById("error-prompt").hidden = true;
  } catch (err) {
    showToast(err.message, "error");
  }
});

async function init() {
  if (!questionId) {
    window.location.replace("/pages/questions/index.html");
    return;
  }
  try {
    const data = await api.get(`/questions/${questionId}`);
    currentQuestion = data.question;
    renderQuestion(currentQuestion);
    loading.hidden = true;
    content.hidden = false;
  } catch (err) {
    loading.hidden = true;
    content.hidden = false;
    showToast(err.message, "error");
  }
}

init();
