export const ENEM_DATES = {
  edition: 2026,
  day1: "2026-11-08",
  day2: "2026-11-15",
};

function parseISODate(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function diffDays(from, to) {
  return Math.round((startOfDay(to) - startOfDay(from)) / 86400000);
}

function daysPhrase(n) {
  if (n === 1) return "1 dia";
  return `${n} dias`;
}

export function getEnemCountdown(now = new Date()) {
  const day1 = parseISODate(ENEM_DATES.day1);
  const day2 = parseISODate(ENEM_DATES.day2);
  const today = startOfDay(now);
  const datesLabel = "8 e 15 de novembro de 2026";

  if (today < day1) {
    const days = diffDays(today, day1);
    return {
      phase: "before-day1",
      days,
      kicker: "ENEM 2026",
      number: String(days),
      title: `Faltam ${daysPhrase(days)} para o 1º dia do ENEM`,
      subtitle: datesLabel,
    };
  }

  if (today < day2) {
    const days = diffDays(today, day2);
    if (days === 0) {
      return {
        phase: "day2",
        days: 0,
        kicker: "ENEM 2026",
        number: "2º",
        title: "Hoje é o 2º dia do ENEM",
        subtitle: datesLabel,
      };
    }
    return {
      phase: "between",
      days,
      kicker: "ENEM 2026",
      number: String(days),
      title: `Faltam ${daysPhrase(days)} para o 2º dia do ENEM`,
      subtitle: datesLabel,
    };
  }

  if (today.getTime() === day2.getTime()) {
    return {
      phase: "day2",
      days: 0,
      kicker: "ENEM 2026",
      number: "2º",
      title: "Hoje é o 2º dia do ENEM",
      subtitle: datesLabel,
    };
  }

  return {
    phase: "after",
    days: 0,
    kicker: "ENEM 2026",
    number: "—",
    title: "ENEM 2026 concluído",
    subtitle: "A próxima edição entra nesta tela quando o INEP publicar o edital.",
  };
}

export function renderCountdownMarkup(countdown, { compact = false } = {}) {
  const after = countdown.phase === "after";
  return `
    <div class="enem-countdown${compact ? " is-compact" : ""}${after ? " is-done" : ""}">
      <p class="countdown-kicker">${countdown.kicker}</p>
      <p class="countdown-number">${countdown.number}</p>
      <p class="countdown-title">${countdown.title}</p>
      <p class="countdown-subtitle">${countdown.subtitle}</p>
    </div>
  `;
}
