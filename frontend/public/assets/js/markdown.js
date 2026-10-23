function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function renderMarkdown(source) {
  if (!source) return "";
  let text = escapeHtml(source);
  text = text.replace(/!\[([^\]]*)\]\((https?:[^)\s]+)\)/g, (_m, alt, url) => {
    return `<img class="question-image" src="${url}" alt="${alt || "Imagem da questão"}">`;
  });
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/\n{2,}/g, "</p><p>");
  text = text.replace(/\n/g, "<br>");
  return `<p>${text}</p>`;
}

export { escapeHtml };
