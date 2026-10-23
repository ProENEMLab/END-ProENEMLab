import { api } from "./api.js";
import { showToast } from "./components/toast.js";
import {
  armFocusGesture,
  cancelFocusArm,
  setFocusSettings,
  setInterruptionGate,
  syncFocusTimer,
} from "./focus.js";

const STATE_KEY = "proenem.pomodoro.state";
const LOCK_KEY = "proenem.pomodoro.leader";
const SOUND_KEY = "proenem.pomodoro.sound";
const SKIP_KEY = "proenem.pomodoro.skip";
const TAB_ID = Math.random().toString(36).slice(2);

const PHASE_LABEL = {
  focus: "Foco",
  short_break: "Pausa curta",
  long_break: "Pausa longa",
};

let booted = false;
let session = null;
let phase = "focus";
let endsAt = 0;
let paused = false;
let frozenMs = 0;
let offset = 0;
let busy = false;
let week = null;
let armTimer = 0;
let countdownTimer = 0;
let offered = new Set();
let channel = null;
let originalTitle = document.title;
let root;
let banner;

function serverNow() {
  return Date.now() + offset;
}

function syncOffset(iso) {
  if (!iso) return;
  offset = Date.parse(iso) - Date.now();
}

function readState() {
  try {
    return JSON.parse(localStorage.getItem(STATE_KEY) || "null");
  } catch {
    return null;
  }
}

function persist() {
  if (!session) {
    localStorage.removeItem(STATE_KEY);
    return;
  }
  localStorage.setItem(
    STATE_KEY,
    JSON.stringify({
      sessionId: session.id,
      phase,
      endsAt,
      paused,
      frozenMs,
    }),
  );
}

function skippedIds() {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(SKIP_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function skipBlock(id) {
  const ids = skippedIds();
  ids.add(id);
  sessionStorage.setItem(SKIP_KEY, JSON.stringify([...ids]));
}

function isLeader() {
  try {
    const lock = JSON.parse(localStorage.getItem(LOCK_KEY) || "null");
    return Boolean(lock && lock.id === TAB_ID && Date.now() - lock.at < 5000);
  } catch {
    return false;
  }
}

function claimLeader() {
  let lock = null;
  try {
    lock = JSON.parse(localStorage.getItem(LOCK_KEY) || "null");
  } catch {
    lock = null;
  }
  const now = Date.now();
  if (!lock || lock.id === TAB_ID || now - lock.at > 5000) {
    localStorage.setItem(LOCK_KEY, JSON.stringify({ id: TAB_ID, at: now }));
  }
}

function soundEnabled() {
  return localStorage.getItem(SOUND_KEY) !== "0";
}

export function setSoundEnabled(on) {
  localStorage.setItem(SOUND_KEY, on ? "1" : "0");
}

function timerError(error) {
  showToast(error.message, "error", { urgent: true });
}

function beep(kind) {
  const focusing = window.proenem?.focusActive;
  if (focusing) {
    if (kind !== "cycle-end" || !window.proenem.focusSound) return;
  } else if (!soundEnabled()) {
    return;
  }
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return;
  const ctx = new AudioCtx();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.frequency.value = 880;
  gain.gain.setValueAtTime(0.04, ctx.currentTime);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 0.18);
  osc.onended = () => ctx.close();
}

function emit(name, detail) {
  document.dispatchEvent(new CustomEvent(name, { detail }));
}

function broadcast() {
  persist();
  channel?.postMessage({
    tabId: TAB_ID,
    session,
    phase,
    endsAt,
    paused,
    frozenMs,
  });
}

function remainingMs() {
  if (!session) return 0;
  if (paused) return frozenMs;
  return endsAt - serverNow();
}

function formatClock(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function ensureChrome() {
  if (document.querySelector("link[href*='pages/study.css']")) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/assets/css/pages/study.css";
  document.head.appendChild(link);
}

function mount() {
  ensureChrome();
  root = document.createElement("section");
  root.id = "pomodoro-dock";
  root.hidden = true;
  root.innerHTML = `
    <p class="pomodoro-kicker" id="pomodoro-subject"></p>
    <p class="pomodoro-clock" id="pomodoro-clock">25:00</p>
    <p class="pomodoro-phase" id="pomodoro-phase">Foco</p>
    <div class="pomodoro-actions">
      <button type="button" class="btn btn-primary" id="pomodoro-toggle">Pausar</button>
      <button type="button" class="btn btn-ghost" id="pomodoro-skip">Pular pausa</button>
      <button type="button" class="btn btn-ghost" id="pomodoro-finish">Encerrar</button>
    </div>
  `;
  banner = document.createElement("section");
  banner.id = "pomodoro-banner";
  banner.hidden = true;
  banner.setAttribute("role", "dialog");
  banner.setAttribute("aria-live", "polite");
  banner.innerHTML = `
    <p id="pomodoro-banner-text"></p>
    <div class="pomodoro-actions">
      <button type="button" class="btn btn-primary" id="pomodoro-now">Iniciar agora</button>
      <button type="button" class="btn btn-ghost" id="pomodoro-snooze">Adiar 5 min</button>
      <button type="button" class="btn btn-ghost" id="pomodoro-dismiss">Pular</button>
    </div>
  `;
  document.body.append(root, banner);
  root.querySelector("#pomodoro-toggle").addEventListener("click", toggle);
  root.querySelector("#pomodoro-skip").addEventListener("click", skipBreak);
  root.querySelector("#pomodoro-finish").addEventListener("click", finish);
}

function paint() {
  if (!root) return;
  if (!session || session.status === "completed" || session.status === "abandoned") {
    root.hidden = true;
    if (document.title !== originalTitle) document.title = originalTitle;
    return;
  }
  root.hidden = false;
  const clock = formatClock(remainingMs());
  const label = PHASE_LABEL[phase] || "Foco";
  root.querySelector("#pomodoro-subject").textContent = session.subject?.name || "Estudo";
  root.querySelector("#pomodoro-clock").textContent = clock;
  root.querySelector("#pomodoro-phase").textContent = label;
  const toggle = root.querySelector("#pomodoro-toggle");
  const skip = root.querySelector("#pomodoro-skip");
  const onBreak = phase !== "focus";
  toggle.hidden = onBreak;
  skip.hidden = !onBreak;
  toggle.textContent = paused ? "Retomar" : "Pausar";
  if (window.proenem?.focusActive) document.title = clock;
  else document.title = `${clock} · ${label} · ProENEM Lab`;
  syncFocusTimer({ session, phase, paused, clock, label });
}

function applyServer(data, { keepBreak = false } = {}) {
  if (!data) {
    session = null;
    paint();
    persist();
    return;
  }
  syncOffset(data.server_now);
  session = data;
  if (data.status === "completed" || data.status === "abandoned") {
    session = null;
    paint();
    persist();
    broadcast();
    return;
  }
  const focusMs = data.settings.focus_minutes * 60000;
  const spent = (data.cycle_focused_seconds || 0) * 1000;
  if (data.status === "paused") {
    phase = "focus";
    paused = true;
    frozenMs = Math.max(0, focusMs - spent);
    endsAt = serverNow() + frozenMs;
  } else if (data.current_interval_started_at) {
    phase = "focus";
    paused = false;
    endsAt = Date.parse(data.current_interval_started_at) + Math.max(0, focusMs - spent);
  } else if (keepBreak) {
    const stored = readState();
    paused = false;
    if (stored && stored.sessionId === data.id && stored.phase !== "focus") {
      phase = stored.phase;
      endsAt = stored.endsAt;
    } else {
      phase = "short_break";
      endsAt = serverNow();
    }
  }
  paint();
  persist();
}

async function reloadActive() {
  const data = await api.get("/sessions/active");
  applyServer(data, { keepBreak: true });
  return data;
}

export async function startBlock(blockId, options = {}) {
  hideBanner();
  if (busy) return;
  if (options.gesture) armFocusGesture();
  busy = true;
  try {
    const data = await api.post("/sessions", { block_id: blockId });
    applyServer(data);
    emit("pomodoro:focus-start", { ...data, gesture: Boolean(options.gesture) });
    beep();
    broadcast();
  } catch (error) {
    cancelFocusArm();
    timerError(error);
    if (error.status === 409) await reloadActive().catch(() => {});
  } finally {
    busy = false;
  }
}

export async function startSubject(subjectId, options = {}) {
  if (busy) return;
  if (options.gesture) armFocusGesture();
  busy = true;
  try {
    const data = await api.post("/sessions", { subject_id: subjectId });
    applyServer(data);
    emit("pomodoro:focus-start", { ...data, gesture: Boolean(options.gesture) });
    beep();
    broadcast();
  } catch (error) {
    cancelFocusArm();
    timerError(error);
  } finally {
    busy = false;
  }
}

async function toggle() {
  if (!session || busy || phase !== "focus") return;
  const resuming = paused;
  if (resuming) armFocusGesture();
  busy = true;
  try {
    const path = resuming ? "resume" : "pause";
    const data = await api.post(`/sessions/${session.id}/${path}`);
    if (resuming) emit("pomodoro:focus-start", { ...data, gesture: true });
    else emit("pomodoro:focus-end", { ...data, reason: "pause" });
    applyServer(data);
    broadcast();
  } catch (error) {
    if (resuming) cancelFocusArm();
    timerError(error);
    await reloadActive().catch(() => {});
  } finally {
    busy = false;
  }
}

async function skipBreak() {
  if (!session || busy || phase === "focus") return;
  await resumeFocus({ gesture: true });
}

async function resumeFocus(options = {}) {
  if (!session || busy) return;
  if (options.gesture) armFocusGesture();
  busy = true;
  try {
    const data = await api.post(`/sessions/${session.id}/resume`);
    applyServer(data);
    emit("pomodoro:focus-start", { ...data, gesture: Boolean(options.gesture) });
    beep();
    broadcast();
  } catch (error) {
    if (options.gesture) cancelFocusArm();
    timerError(error);
    await reloadActive().catch(() => {});
  } finally {
    busy = false;
  }
}

async function completeFocus() {
  if (!session || busy) return;
  busy = true;
  try {
    const data = await api.post(`/sessions/${session.id}/complete-cycle`);
    beep("cycle-end");
    syncOffset(data.server_now);
    if (data.status !== "running") {
      emit("pomodoro:session-end", data);
      session = null;
      paint();
      persist();
      broadcast();
      refreshSchedule();
      return;
    }
    emit("pomodoro:focus-end", { ...data, reason: "break" });
    session = data;
    paused = false;
    const long = data.completed_cycles % data.settings.cycles_before_long_break === 0;
    phase = long ? "long_break" : "short_break";
    const minutes = long ? data.settings.long_break_minutes : data.settings.short_break_minutes;
    endsAt = serverNow() + minutes * 60000;
    paint();
    broadcast();
  } catch (error) {
    timerError(error);
    await reloadActive().catch(() => {});
  } finally {
    busy = false;
  }
}

async function finish() {
  if (!session || busy) return;
  if (!window.confirm("Encerrar a sessão de estudo?")) return;
  busy = true;
  try {
    const endingFocus = phase === "focus" && !paused;
    const data = await api.post(`/sessions/${session.id}/finish`);
    if (endingFocus) emit("pomodoro:focus-end", { ...data, reason: "finish" });
    emit("pomodoro:session-end", data);
    session = null;
    paint();
    persist();
    broadcast();
    refreshSchedule();
  } catch (error) {
    timerError(error);
  } finally {
    busy = false;
  }
}

function tick() {
  paint();
  if (!session || paused || busy || !isLeader()) return;
  if (remainingMs() > 0) return;
  if (phase === "focus") completeFocus();
  else resumeFocus();
}

function hideBanner() {
  clearInterval(countdownTimer);
  if (banner) banner.hidden = true;
}

function showOffer(block, { auto = false, remaining = 0, fromClick = false } = {}) {
  if (!banner) return;
  clearInterval(countdownTimer);
  const name = block.subject?.name || "disciplina";
  const text = banner.querySelector("#pomodoro-banner-text");
  const snooze = banner.querySelector("#pomodoro-snooze");
  const dismiss = banner.querySelector("#pomodoro-dismiss");
  snooze.hidden = !auto;
  dismiss.textContent = auto ? "Pular" : "Agora não";
  banner.hidden = false;
  banner._block = block;
  if (auto) {
    const deadline = Date.now() + 10000;
    const draw = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      text.textContent = `Bloco de ${name} começando — Pomodoro inicia em ${left} s`;
      if (left <= 0) {
        clearInterval(countdownTimer);
        startBlock(block.id);
      }
    };
    draw();
    countdownTimer = setInterval(draw, 250);
    return;
  }
  if (fromClick) {
    text.textContent = `Iniciar Pomodoro de ${name}?`;
    return;
  }
  const minutes = Math.max(1, Math.round(remaining / 60000));
  text.textContent = `Iniciar Pomodoro de ${name} (restam ${minutes} min)`;
}

function wireBanner() {
  banner.querySelector("#pomodoro-now").addEventListener("click", () => {
    const block = banner._block;
    if (block) startBlock(block.id, { gesture: true });
  });
  banner.querySelector("#pomodoro-snooze").addEventListener("click", () => {
    const block = banner._block;
    hideBanner();
    if (!block) return;
    setTimeout(() => {
      if (session || skippedIds().has(block.id)) return;
      showOffer(block, { auto: true });
    }, 5 * 60000);
  });
  banner.querySelector("#pomodoro-dismiss").addEventListener("click", () => {
    const block = banner._block;
    if (block && !banner.querySelector("#pomodoro-snooze").hidden) skipBlock(block.id);
    hideBanner();
    planNext();
  });
}

function mondayOf(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const weekday = date.getUTCDay();
  const delta = weekday === 0 ? 6 : weekday - 1;
  date.setUTCDate(date.getUTCDate() - delta);
  return date.toISOString().slice(0, 10);
}

function dayIndex(weekStart, today) {
  const start = Date.parse(`${weekStart}T00:00:00Z`);
  const current = Date.parse(`${today}T00:00:00Z`);
  return Math.round((current - start) / 86400000);
}

function planNext() {
  clearTimeout(armTimer);
  if (!week?.today_start || !week.today) return;
  const origin = Date.parse(week.today_start);
  const now = serverNow();
  const day = dayIndex(week.week_start, week.today);
  if (day < 0 || day > 6) return;
  const blocks = (week.blocks || [])
    .filter((block) => block.day_of_week === day)
    .sort((a, b) => a.start_minute - b.start_minute);
  const skipped = skippedIds();
  for (const block of blocks) {
    if (skipped.has(block.id)) continue;
    const start = origin + block.start_minute * 60000;
    const end = start + block.duration_minutes * 60000;
    if (now >= end) continue;
    if (now >= start) {
      if (!session && !offered.has(block.id)) {
        offered.add(block.id);
        showOffer(block, { auto: false, remaining: end - now });
      }
      continue;
    }
    armTimer = setTimeout(() => {
      if (session || skippedIds().has(block.id)) return;
      if (week.settings?.auto_start_blocks) showOffer(block, { auto: true });
    }, Math.max(0, start - now));
    return;
  }
}

export async function refreshSchedule() {
  try {
    const settings = await api.get("/pomodoro/settings");
    setFocusSettings(settings);
    syncOffset(settings.server_now);
    week = await api.get(`/calendar/weeks/${mondayOf(settings.today)}`);
    syncOffset(week.server_now);
    planNext();
  } catch {

  }
}

export function offerBlock(block) {
  showOffer(block, { fromClick: true });
}

function publishPhase() {
  if (!session || session.status === "completed" || session.status === "abandoned") {
    emit("pomodoro:session-end", session || {});
    return;
  }
  if (phase === "focus" && paused) emit("pomodoro:focus-end", { ...session, reason: "pause" });
  else if (phase === "focus") emit("pomodoro:focus-start", { ...session, gesture: false });
  else emit("pomodoro:focus-end", { ...session, reason: "break" });
}

function onStorage(event) {
  if (event.key !== STATE_KEY || isLeader()) return;
  if (!event.newValue) {
    session = null;
    paint();
    publishPhase();
    return;
  }
  try {
    const stored = JSON.parse(event.newValue);
    if (!session || session.id !== stored.sessionId) return;
    phase = stored.phase;
    endsAt = stored.endsAt;
    paused = stored.paused;
    frozenMs = stored.frozenMs || 0;
    paint();
    publishPhase();
  } catch {

  }
}

export function bootPomodoro() {
  if (booted) return;
  booted = true;
  originalTitle = document.title;
  mount();
  wireBanner();
  if ("BroadcastChannel" in window) {
    channel = new BroadcastChannel("proenem-pomodoro");
    channel.onmessage = (event) => {
      const message = event.data;
      if (!message || message.tabId === TAB_ID) return;
      session = message.session;
      phase = message.phase;
      endsAt = message.endsAt;
      paused = message.paused;
      frozenMs = message.frozenMs || 0;
      if (session?.server_now) syncOffset(session.server_now);
      paint();
      publishPhase();
    };
  }
  setInterruptionGate(isLeader);
  document.addEventListener("pomodoro:request-toggle", () => {
    toggle();
  });
  document.addEventListener("pomodoro:request-finish", () => {
    finish();
  });
  window.addEventListener("storage", onStorage);
  claimLeader();
  setInterval(claimLeader, 1000);
  setInterval(tick, 250);
  reloadActive()
    .catch(() => {})
    .finally(() => {
      publishPhase();
      refreshSchedule();
    });
}
