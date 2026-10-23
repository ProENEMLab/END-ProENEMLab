const TOKEN_KEY = "proenem_token";
const USER_KEY = "proenem_user";
const THEME_KEY = "proenem_theme";
const FLASH_KEY = "proenem_flash";
const ROADMAP_CACHE_KEY = "proenem_roadmap";
const QUESTION_QUEUE_KEY = "proenem_question_queue";
const PENDING_FILTER_SAVE_KEY = "proenem_pending_filter_save";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function setSession(token, user) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function logout() {
  clearSession();
  window.location.href = "/";
}

export function setFlash(message, type = "success") {
  sessionStorage.setItem(FLASH_KEY, JSON.stringify({ message, type }));
}

export function consumeFlash() {
  const raw = sessionStorage.getItem(FLASH_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(FLASH_KEY);
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function cacheRoadmap(topics) {
  sessionStorage.setItem(ROADMAP_CACHE_KEY, JSON.stringify(topics));
}

export function getCachedRoadmap() {
  try {
    return JSON.parse(sessionStorage.getItem(ROADMAP_CACHE_KEY) || "null");
  } catch {
    return null;
  }
}

export function setQuestionQueue(ids, filters = {}) {
  sessionStorage.setItem(QUESTION_QUEUE_KEY, JSON.stringify({ ids, filters }));
}

export function getQuestionQueue() {
  try {
    return JSON.parse(sessionStorage.getItem(QUESTION_QUEUE_KEY) || "null");
  } catch {
    return null;
  }
}

export function setPendingFilterSave(payload) {
  sessionStorage.setItem(PENDING_FILTER_SAVE_KEY, JSON.stringify(payload));
}

export function consumePendingFilterSave() {
  const raw = sessionStorage.getItem(PENDING_FILTER_SAVE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(PENDING_FILTER_SAVE_KEY);
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function safeNextPath(fallback = "/pages/dashboard/index.html") {
  const next = new URLSearchParams(window.location.search).get("next");
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("://")) {
    return fallback;
  }
  return next;
}

export { TOKEN_KEY, THEME_KEY, USER_KEY, PENDING_FILTER_SAVE_KEY };
