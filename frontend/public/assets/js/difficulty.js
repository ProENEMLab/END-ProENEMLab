const TIPS = {
  inep_tri: "Classificação baseada nas estatísticas oficiais do ENEM (INEP)",
  platform: "Classificação baseada no desempenho dos estudantes da plataforma",
};

const FALLBACK = {
  easy: "Fácil",
  medium: "Médio",
  hard: "Difícil",
};

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function difficultyBadge(difficulty) {
  const payload =
    difficulty && typeof difficulty === "object"
      ? difficulty
      : { level: difficulty || null, source: null, label: null };
  const label = payload.label || FALLBACK[payload.level] || "Não classificada";
  const kind = payload.level || "none";
  const tip =
    TIPS[payload.source] ||
    "Ainda não há estatística oficial do ENEM nem amostra suficiente na plataforma.";
  return `<span class="badge badge-difficulty badge-difficulty-${kind}" title="${escapeHtml(tip)}">${escapeHtml(label)}</span>`;
}
