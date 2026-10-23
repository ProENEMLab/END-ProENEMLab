import { API_BASE_URL } from "./config.js";
import { api } from "./api.js";
import { clearSession, getToken } from "./session.js";
import { showToast } from "./components/toast.js";
import { icon } from "./icons.js";

let dialog = null;

function filenameFromDisposition(header) {
  if (!header) return null;
  const star = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(header);
  if (star) {
    try {
      return decodeURIComponent(star[1].trim().replace(/^"|"$/g, ""));
    } catch {
      return star[1].trim();
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1] : null;
}

function messageFrom(data, status) {
  if ((status === 422 || status === 429) && data && typeof data.error === "string") {
    return data.error;
  }
  return "Não foi possível gerar o PDF. Tente de novo.";
}

export async function downloadStudyReport(params) {
  const token = getToken();
  const query = new URLSearchParams();
  if (params.sections) query.set("sections", params.sections);
  if (params.subjectId) query.set("subject_id", params.subjectId);
  if (params.from) query.set("from", params.from);
  if (params.to) query.set("to", params.to);
  query.set("include_resolved", params.includeResolved ? "true" : "false");
  const response = await fetch(`${API_BASE_URL}/exports/study-report.pdf?${query}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (response.status === 401) {
    clearSession();
    window.location.href = "/pages/authentication/login.html";
    throw new Error("Sessão expirada. Faça login novamente.");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(messageFrom(data, response.status));
  }
  const blob = await response.blob();
  const filename = filenameFromDisposition(response.headers.get("Content-Disposition"))
    || "proenem-relatorio.pdf";
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ensureDialog() {
  if (dialog) return dialog;
  dialog = document.createElement("div");
  dialog.className = "modal-backdrop";
  dialog.innerHTML = `
    <div class="modal export-report-modal" role="dialog" aria-modal="true" aria-labelledby="export-report-title">
      <button type="button" class="modal-close" data-export-close aria-label="Fechar">${icon("x", { size: 18 })}</button>
      <h2 id="export-report-title">Exportar PDF</h2>
      <p class="muted">Anotações por tópico e questões que você já errou, com o gabarito comentado.</p>
      <form id="export-report-form">
        <div class="export-checks">
          <label><input type="checkbox" name="notes" checked> Anotações por tópico</label>
          <label><input type="checkbox" name="wrong" checked> Questões erradas com gabarito</label>
          <label><input type="checkbox" name="include_resolved" checked> Incluir erradas que já acertei depois</label>
        </div>
        <div class="field">
          <label for="export-subject">Disciplina</label>
          <select id="export-subject" name="subject_id">
            <option value="">Todas</option>
          </select>
        </div>
        <div class="export-dates">
          <div class="field">
            <label for="export-from">De</label>
            <input id="export-from" name="from" type="date">
          </div>
          <div class="field">
            <label for="export-to">Até</label>
            <input id="export-to" name="to" type="date">
          </div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" data-export-close>Cancelar</button>
          <button type="submit" class="btn btn-primary" data-export-submit>Gerar PDF</button>
        </div>
      </form>
    </div>
  `;
  document.body.appendChild(dialog);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog || event.target.closest("[data-export-close]")) closeExportDialog();
  });
  dialog.querySelector("#export-report-form").addEventListener("submit", onSubmit);
  return dialog;
}

async function loadSubjects() {
  const select = dialog.querySelector("#export-subject");
  const current = select.value;
  select.innerHTML = `<option value="">Todas</option>`;
  try {
    const data = await api.get("/subjects");
    for (const subject of data.subjects || []) {
      const option = document.createElement("option");
      option.value = String(subject.id);
      option.textContent = subject.name;
      select.appendChild(option);
    }
    if (current) select.value = current;
  } catch (err) {
    showToast(err.message, "error");
  }
}

export function openExportDialog() {
  const node = ensureDialog();
  node.classList.add("is-open");
  loadSubjects();
}

export function closeExportDialog() {
  dialog?.classList.remove("is-open");
}

async function onSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const submit = form.querySelector("[data-export-submit]");
  const notes = form.notes.checked;
  const wrong = form.wrong.checked;
  if (!notes && !wrong) {
    showToast("Escolha anotações, questões erradas ou as duas.", "error");
    return;
  }
  const from = form.from.value;
  const to = form.to.value;
  if (from && to && from > to) {
    showToast("A data inicial é posterior à data final.", "error");
    return;
  }
  const sections = [notes ? "notes" : null, wrong ? "wrong" : null].filter(Boolean).join(",");
  submit.disabled = true;
  const previous = submit.textContent;
  submit.textContent = "Gerando...";
  try {
    await downloadStudyReport({
      sections,
      subjectId: form.subject_id.value,
      from,
      to,
      includeResolved: form.include_resolved.checked,
    });
    closeExportDialog();
    showToast("Relatório baixado.", "success");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    submit.disabled = false;
    submit.textContent = previous;
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-export-pdf]");
  if (!button) return;
  event.preventDefault();
  openExportDialog();
});
