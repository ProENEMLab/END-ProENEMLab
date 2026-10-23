import { api } from "./api.js";
import { flushQueuedToasts } from "./components/toast.js";

const SETTINGS_KEY = "proenem.focus.settings";
const DND_KEY = "proenem.focus.dndSeen";

window.proenem = window.proenem || {};
window.proenem.focusActive = false;

let settings = readStored() || {
  focus_mode_enabled: false,
  focus_mode_fullscreen: true,
  focus_mode_sound: false,
};
let overlay;
let engaged = false;
let pending = false;
let mode = "idle";
let sessionId = null;
let announced = "";
let hiddenAt = 0;
let leftFullscreen = false;
let suppressInterrupt = false;
let wakeLock = null;
let reportsAllowed = () => true;
const frozen = new Set();

function readStored() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY) || "null");
  } catch {
    return null;
  }
}

function enabled() {
  return Boolean(settings.focus_mode_enabled);
}

function wantsFullscreen() {
  return settings.focus_mode_fullscreen !== false;
}

export function setFocusSettings(next) {
  if (!next) return;
  settings = {
    ...settings,
    focus_mode_enabled: Boolean(next.focus_mode_enabled),
    focus_mode_fullscreen: next.focus_mode_fullscreen !== false,
    focus_mode_sound: Boolean(next.focus_mode_sound),
  };
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  window.proenem.focusSound = settings.focus_mode_sound;
}

export function setInterruptionGate(fn) {
  reportsAllowed = fn;
}

function ensureStyle() {
  if (document.querySelector("link[href*='pages/study.css']")) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/assets/css/pages/study.css";
  document.head.appendChild(link);
}

function ensureOverlay() {
  if (overlay) return overlay;
  ensureStyle();
  overlay = document.createElement("section");
  overlay.id = "focus-overlay";
  overlay.hidden = true;
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-labelledby", "focus-title");
  overlay.innerHTML = `
    <p id="focus-title" class="focus-subject">Estudo</p>
    <p class="focus-clock" id="focus-clock" aria-hidden="true">...</p>
    <p id="focus-live" class="sr-only" aria-live="polite"></p>
    <p id="focus-cycle" class="focus-cycle"></p>
    <p id="focus-note" class="focus-note" role="status"></p>
    <p id="focus-dnd" class="focus-dnd" hidden>
      Ative o Não perturbe do celular ou do computador para silenciar avisos de outros aplicativos.
    </p>
    <div class="focus-actions">
      <button type="button" class="is-primary" id="focus-pause">Pausar</button>
      <button type="button" class="is-quiet" id="focus-finish">Encerrar</button>
      <button type="button" class="is-primary" id="focus-leave" hidden>Sair do foco</button>
      <button type="button" class="is-primary" id="focus-fs" hidden>Entrar em tela cheia</button>
      <button type="button" class="is-quiet" id="focus-dnd-ok" hidden>Entendi</button>
    </div>
    <p class="focus-hint">Tecla F alterna a tela cheia.</p>
  `;
  document.body.appendChild(overlay);
  overlay.querySelector("#focus-pause").addEventListener("click", () => {
    document.dispatchEvent(new CustomEvent("pomodoro:request-toggle"));
  });
  overlay.querySelector("#focus-finish").addEventListener("click", () => {
    document.dispatchEvent(new CustomEvent("pomodoro:request-finish"));
  });
  overlay.querySelector("#focus-leave").addEventListener("click", leaveFocus);
  overlay.querySelector("#focus-fs").addEventListener("click", () => requestFullscreen());
  overlay.querySelector("#focus-dnd-ok").addEventListener("click", () => {
    localStorage.setItem(DND_KEY, "1");
    overlay.querySelector("#focus-dnd").hidden = true;
    overlay.querySelector("#focus-dnd-ok").hidden = true;
  });
  return overlay;
}

function isFullscreen() {
  return Boolean(document.fullscreenElement || document.webkitFullscreenElement);
}

function requestFullscreen() {
  const el = document.documentElement;
  const ask = el.requestFullscreen || el.webkitRequestFullscreen;
  if (typeof ask !== "function") return;
  try {
    const pendingAsk = ask.call(el);
    if (pendingAsk && typeof pendingAsk.catch === "function") pendingAsk.catch(() => {});
  } catch {

  }
}

function exitFullscreen(suppress = false) {
  const active = document.fullscreenElement || document.webkitFullscreenElement;
  if (!active) return;
  if (suppress) suppressInterrupt = true;
  const leave = document.exitFullscreen || document.webkitExitFullscreen;
  if (typeof leave !== "function") {
    suppressInterrupt = false;
    return;
  }
  try {
    const pendingLeave = leave.call(document);
    if (pendingLeave && typeof pendingLeave.catch === "function") {
      pendingLeave.catch(() => {
        suppressInterrupt = false;
      });
    }
  } catch {
    suppressInterrupt = false;
  }
}

export function armFocusGesture() {
  if (!enabled()) return;
  ensureOverlay();
  if (engaged) {
    if (wantsFullscreen()) requestFullscreen();
    return;
  }
  pending = true;
  overlay.hidden = false;
  overlay.querySelector("#focus-title").textContent = "Entrando no foco...";
  overlay.querySelector("#focus-clock").textContent = "...";
  overlay.querySelector("#focus-cycle").textContent = "";
  overlay.querySelector("#focus-note").textContent = "";
  paintChrome();
  freezeBackground(true);
  if (wantsFullscreen()) requestFullscreen();
}

export function cancelFocusArm() {
  if (engaged) return;
  pending = false;
  closeAll();
}

function remember(detail) {
  if (detail?.settings) setFocusSettings(detail.settings);
  if (detail?.id) sessionId = detail.id;
}

function onFocusStart(event) {
  const detail = event.detail || {};
  remember(detail);
  if (!enabled()) {
    cancelFocusArm();
    return;
  }
  const same = engaged && mode === "focus" && sessionId === detail.id;
  pending = false;
  engaged = true;
  mode = "focus";
  window.proenem.focusActive = true;
  ensureOverlay();
  overlay.hidden = false;
  paintChrome();
  freezeBackground(true);
  showDndOnce();
  acquireWakeLock();
  if (!same) focusPrimary();
}

function onFocusEnd(event) {
  const detail = event.detail || {};
  remember(detail);
  if (detail.reason === "finish") return;
  if (!enabled()) return;
  if (!engaged && !pending) {
    engaged = true;
    window.proenem.focusActive = true;
    ensureOverlay();
    overlay.hidden = false;
    freezeBackground(true);
    showDndOnce();
  }
  if (!engaged) return;
  pending = false;
  mode = detail.reason === "pause" ? "paused" : "break";
  window.proenem.focusActive = true;
  paintChrome();
  focusPrimary();
}

function onSessionEnd() {
  if (!engaged && !pending) return;
  closeAll();
}

function leaveFocus() {
  closeAll();
}

function closeAll() {
  engaged = false;
  pending = false;
  mode = "idle";
  sessionId = null;
  hiddenAt = 0;
  announced = "";
  leftFullscreen = false;
  window.proenem.focusActive = false;
  if (overlay) overlay.hidden = true;
  releaseWakeLock();
  exitFullscreen(true);
  freezeBackground(false);
  flushQueuedToasts();
}

function paintChrome() {
  if (!overlay) return;
  const pause = overlay.querySelector("#focus-pause");
  const finish = overlay.querySelector("#focus-finish");
  const leave = overlay.querySelector("#focus-leave");
  const fs = overlay.querySelector("#focus-fs");
  const onBreak = mode === "break";
  pause.hidden = onBreak || pending || mode === "idle";
  finish.hidden = onBreak || pending || mode === "idle";
  leave.hidden = !onBreak;
  pause.textContent = mode === "paused" ? "Retomar" : "Pausar";
  const showFs = (engaged || pending) && wantsFullscreen() && !isFullscreen();
  fs.hidden = !showFs;
  fs.textContent = leftFullscreen ? "Voltar à tela cheia" : "Entrar em tela cheia";
}

function focusPrimary() {
  if (!overlay || overlay.hidden) return;
  const target = [...overlay.querySelectorAll("button")].find((button) => !button.hidden);
  target?.focus();
}

function showDndOnce() {
  if (!overlay) return;
  const seen = localStorage.getItem(DND_KEY) === "1";
  overlay.querySelector("#focus-dnd").hidden = seen;
  overlay.querySelector("#focus-dnd-ok").hidden = seen;
}

function awayText(seconds) {
  if (seconds < 60) return `Você ficou ${seconds} s fora do foco.`;
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `Você ficou ${minutes} min fora do foco.`;
}

function sendInterruption(body) {
  if (!reportsAllowed() || !sessionId) return;
  const id = sessionId;
  const post = () => api.post(`/sessions/${id}/interruptions`, body);
  post().catch(() => post().catch(() => {}));
}

export function syncFocusTimer(snapshot) {
  if (!engaged || !overlay || overlay.hidden || !snapshot) return;
  if (snapshot.session?.id) sessionId = snapshot.session.id;
  const clock = snapshot.clock || "00:00";
  overlay.querySelector("#focus-clock").textContent = clock;
  overlay.querySelector("#focus-title").textContent = snapshot.session?.subject?.name || "Estudo";
  const cycle = overlay.querySelector("#focus-cycle");
  if (mode === "break") {
    cycle.textContent = snapshot.label || "Pausa";
  } else {
    const done = snapshot.session?.completed_cycles || 0;
    const planned = snapshot.session?.planned_cycles || 1;
    cycle.textContent = `Ciclo ${done + 1} de ${planned}`;
  }
  const minute = clock.split(":")[0];
  if (minute !== announced) {
    announced = minute;
    const label = snapshot.label || "Foco";
    overlay.querySelector("#focus-live").textContent = `${label}. ${Number(minute)} minutos restantes.`;
  }
}

function freezeBackground(on) {
  if (!overlay) return;
  if (!on) {
    for (const child of frozen) child.removeAttribute("inert");
    frozen.clear();
    document.body.classList.remove("focus-lock");
    return;
  }
  for (const child of document.body.children) {
    if (child === overlay || child.tagName === "TOAST-CONTAINER") continue;
    if (child.hasAttribute("inert")) continue;
    child.setAttribute("inert", "");
    frozen.add(child);
  }
  document.body.classList.add("focus-lock");
}

async function acquireWakeLock() {
  if (!navigator.wakeLock?.request || !engaged) return;
  try {
    wakeLock = await navigator.wakeLock.request("screen");
  } catch {
    wakeLock = null;
  }
}

async function releaseWakeLock() {
  const current = wakeLock;
  wakeLock = null;
  if (!current) return;
  try {
    await current.release();
  } catch {

  }
}

function onFullscreenChange() {
  const active = isFullscreen();
  if (!active && suppressInterrupt) {
    suppressInterrupt = false;
    paintChrome();
    return;
  }
  if (!engaged) return;
  if (active) {
    leftFullscreen = false;
    paintChrome();
    return;
  }
  leftFullscreen = true;
  paintChrome();
  if (mode === "focus" && sessionId) {
    sendInterruption({
      kind: "fullscreen_exit",
      occurred_at: new Date().toISOString(),
    });
  }
}

function onVisibility() {
  if (document.visibilityState === "visible" && engaged) acquireWakeLock();
  if (!engaged || mode !== "focus") return;
  if (document.visibilityState === "hidden") {
    hiddenAt = Date.now();
    return;
  }
  if (!hiddenAt) return;
  const seconds = Math.round((Date.now() - hiddenAt) / 1000);
  hiddenAt = 0;
  if (seconds <= 0 || !overlay) return;
  overlay.querySelector("#focus-note").textContent = awayText(seconds);
  sendInterruption({
    kind: "tab_hidden",
    occurred_at: new Date().toISOString(),
    duration_seconds: seconds,
  });
}

function onKey(event) {
  if (!overlay || overlay.hidden) return;
  if ((event.key === "f" || event.key === "F") && !event.ctrlKey && !event.metaKey && !event.altKey) {
    event.preventDefault();
    if (isFullscreen()) exitFullscreen(false);
    else requestFullscreen();
    return;
  }
  if (event.key !== "Tab") return;
  const buttons = [...overlay.querySelectorAll("button")].filter((button) => !button.hidden);
  if (!buttons.length) return;
  const first = buttons[0];
  const last = buttons[buttons.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

document.addEventListener("pomodoro:focus-start", onFocusStart);
document.addEventListener("pomodoro:focus-end", onFocusEnd);
document.addEventListener("pomodoro:session-end", onSessionEnd);
document.addEventListener("fullscreenchange", onFullscreenChange);
document.addEventListener("webkitfullscreenchange", onFullscreenChange);
document.addEventListener("visibilitychange", onVisibility);
document.addEventListener("keydown", onKey);
