import { API_BASE_URL } from "./config.js";
import { clearSession, getToken } from "./session.js";

const MESSAGE_BY_CODE = {
  INVALID_CREDENTIALS: "E-mail ou senha inválidos.",
  EMAIL_ALREADY_EXISTS: "Este e-mail já está cadastrado.",
  INVALID_RESET_TOKEN: "Token inválido ou expirado.",
  VALIDATION_ERROR: "Verifique os dados informados.",
  OVERLAP: "Esse horário já tem outro bloco.",
  PAST_WEEK: "Semanas passadas são somente leitura.",
  WEEK_NOT_EMPTY: "A semana já tem blocos. Nada foi copiado.",
  ACTIVE_SESSION: "Você já tem um Pomodoro em andamento.",
  INVALID_TRANSITION: "Essa ação não vale neste momento do Pomodoro.",
  BLOCK_NOT_FOUND: "Bloco não encontrado.",
  SUBJECT_NOT_FOUND: "Disciplina não encontrada.",
  SESSION_NOT_FOUND: "Sessão não encontrada.",
  QUESTION_NOT_FOUND: "Questão não encontrada.",
  LEVEL_LOCKED: "Este nível ainda está travado.",
  TOPIC_NOT_FOUND: "Tópico não encontrado.",
  INVALID_DIFFICULTY: "Dificuldade inválida.",
  GOAL_NOT_FOUND: "Meta não encontrada.",
  GOAL_ALREADY_COMPLETED: "Esta meta já foi concluída.",
  FORBIDDEN: "Você não tem permissão para esta ação.",
};

function flattenError(error) {
  if (!error) return null;
  if (typeof error === "string") return error;
  if (Array.isArray(error)) return error.map(flattenError).filter(Boolean).join(" ");
  if (typeof error === "object") {
    return Object.values(error).map(flattenError).filter(Boolean).join(" ");
  }
  return String(error);
}

function extractError(data, fallback = "Erro inesperado") {
  if (!data) return fallback;
  if (data.code && MESSAGE_BY_CODE[data.code]) return MESSAGE_BY_CODE[data.code];
  return flattenError(data.error) || fallback;
}

function isAuthPage() {
  return window.location.pathname.includes("/pages/authentication/");
}

function isAuthApi(path) {
  return path.startsWith("/auth/");
}

async function request(method, path, body) {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && !isAuthApi(path)) {
    clearSession();
    const data = await res.json().catch(() => null);
    if (!isAuthPage()) {
      window.location.href = "/pages/authentication/login.html";
    }
    throw new Error(extractError(data, "Sessão expirada. Faça login novamente."));
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const error = new Error(extractError(data));
    error.status = res.status;
    error.payload = data;
    throw error;
  }
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  del: (path, body) => request("DELETE", path, body),
};
