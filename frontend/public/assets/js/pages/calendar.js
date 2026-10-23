import { api } from "../api.js";
import { showToast } from "../components/toast.js";
import { setFocusSettings } from "../focus.js";
import { offerBlock, refreshSchedule, setSoundEnabled, startBlock, startSubject } from "../pomodoro.js";

const DAYS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"];
const SHORT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const OUTCOME = { done: "concluído", partial: "parcial", missed: "não feito" };
const SLOT_PX = 28;

const sheet = document.getElementById("cal-sheet");
const palette = document.getElementById("palette");
const label = document.getElementById("week-label");
const live = document.getElementById("cal-live");
const summary = document.getElementById("week-summary");
const form = document.getElementById("block-form");
const readonlyNote = document.getElementById("readonly-note");
const errorBox = document.getElementById("calendar-error");

let week = null;
let offset = 0;
let drag = null;

function mondayOf(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const weekday = date.getUTCDay();
  date.setUTCDate(date.getUTCDate() - (weekday === 0 ? 6 : weekday - 1));
  return date.toISOString().slice(0, 10);
}

function shiftDate(isoDate, days) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day + days));
  return date.toISOString().slice(0, 10);
}

function dayStamp(index) {
  const [year, month, day] = week.week_start.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day + index));
  return `${date.getUTCDate()}/${date.getUTCMonth() + 1}`;
}

function hm(minute) {
  return `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
}

function announce(text) {
  live.textContent = text;
}

function showError(error) {
  errorBox.hidden = false;
  errorBox.textContent = error.message;
  showToast(error.message, "error");
}

function overlaps(start, duration, otherStart, otherDuration) {
  return start < otherStart + otherDuration && otherStart < start + duration;
}

function placementOk(day, start, duration, ignoreId) {
  const grid = week.grid;
  if (day < 0 || day > 6) return false;
  if (start < grid.day_start_minute || start + duration > grid.day_end_minute) return false;
  if (duration < grid.block_min_minutes || duration > grid.block_max_minutes) return false;
  if (start % grid.slot_minutes || duration % grid.slot_minutes) return false;
  return !week.blocks.some(
    (block) =>
      block.id !== ignoreId &&
      block.day_of_week === day &&
      overlaps(start, duration, block.start_minute, block.duration_minutes),
  );
}

function ariaLabel(block) {
  const end = block.start_minute + block.duration_minutes;
  const count = block.planned_cycles;
  const noun = count === 1 ? "pomodoro" : "pomodoros";
  return `${block.subject.name}, ${DAYS[block.day_of_week]}, ${hm(block.start_minute)} a ${hm(end)}, ${count} ${noun}`;
}

function fillSelect(select, options, selected) {
  select.innerHTML = options
    .map(([value, text]) => `<option value="${value}">${text}</option>`)
    .join("");
  if (selected != null) select.value = String(selected);
}

function fillForm() {
  const grid = week.grid;
  const subjects = week.subjects.map((item) => [item.id, item.name]);
  fillSelect(document.getElementById("block-subject"), subjects);
  fillSelect(
    document.getElementById("block-day"),
    DAYS.map((name, index) => [index, name]),
  );
  const starts = [];
  for (let minute = grid.day_start_minute; minute <= grid.day_end_minute - grid.block_min_minutes; minute += grid.slot_minutes) {
    starts.push([minute, hm(minute)]);
  }
  fillSelect(document.getElementById("block-start"), starts, 14 * 60);
  const durations = [];
  for (let minutes = grid.block_min_minutes; minutes <= grid.block_max_minutes; minutes += grid.slot_minutes) {
    durations.push([minutes, `${minutes} min`]);
  }
  fillSelect(document.getElementById("block-duration"), durations, grid.block_min_minutes);
  const settings = week.settings;
  document.getElementById("focus-minutes").value = settings.focus_minutes;
  document.getElementById("short-break").value = settings.short_break_minutes;
  document.getElementById("long-break").value = settings.long_break_minutes;
  document.getElementById("cycle-count").value = settings.cycles_before_long_break;
  document.getElementById("auto-start").checked = settings.auto_start_blocks;
  document.getElementById("focus-mode").checked = Boolean(settings.focus_mode_enabled);
  document.getElementById("focus-fullscreen").checked = settings.focus_mode_fullscreen !== false;
  document.getElementById("focus-sound").checked = Boolean(settings.focus_mode_sound);
  document.getElementById("sound-on").checked = localStorage.getItem("proenem.pomodoro.sound") !== "0";
  setFocusSettings(settings);
}

function renderPalette() {
  palette.innerHTML = week.subjects
    .map(
      (subject) => `
        <button type="button" class="subject-chip" data-subject-id="${subject.id}"
          style="border-left-color:${subject.color}" ${week.read_only ? "disabled" : ""}>
          ${subject.name}
        </button>`,
    )
    .join("");
}

function renderSummary() {
  const totals = new Map();
  for (const block of week.blocks) {
    if (!block.subject) continue;
    const row = totals.get(block.subject.id) || {
      name: block.subject.name,
      color: block.subject.color,
      minutes: 0,
    };
    row.minutes += block.duration_minutes;
    totals.set(block.subject.id, row);
  }
  if (!totals.size) {
    summary.innerHTML = "<p class='muted'>Nenhum minuto planejado nesta semana.</p>";
    return;
  }
  summary.innerHTML = [...totals.values()]
    .map(
      (row) =>
        `<span class="badge" style="border-left:4px solid ${row.color}">${row.name}: ${row.minutes} min</span>`,
    )
    .join("");
}

function render({ focusId } = {}) {
  const grid = week.grid;
  const slots = (grid.day_end_minute - grid.day_start_minute) / grid.slot_minutes;
  const height = slots * SLOT_PX;
  sheet.style.setProperty("--slot-px", `${SLOT_PX}px`);
  const todayIndex = Math.round(
    (Date.parse(`${week.today}T00:00:00Z`) - Date.parse(`${week.week_start}T00:00:00Z`)) / 86400000,
  );
  const heads = DAYS.map(
    (_, index) =>
      `<div class="cal-dayhead${index === todayIndex ? " is-today" : ""}">${SHORT[index]} ${dayStamp(index)}</div>`,
  ).join("");
  const times = [];
  for (let minute = grid.day_start_minute; minute < grid.day_end_minute; minute += 60) {
    const top = ((minute - grid.day_start_minute) / grid.slot_minutes) * SLOT_PX;
    times.push(`<span style="top:${top}px">${hm(minute)}</span>`);
  }
  const columns = DAYS.map((_, index) => {
    const blocks = week.blocks
      .filter((block) => block.day_of_week === index)
      .map((block) => blockMarkup(block, grid))
      .join("");
    return `<div class="cal-day" data-day="${index}" style="height:${height}px">${blocks}</div>`;
  }).join("");
  sheet.innerHTML = `<div class="cal-corner"></div>${heads}<div class="cal-times" style="height:${height}px">${times.join("")}</div>${columns}`;
  sheet.classList.toggle("is-readonly", week.read_only);
  label.textContent = `${dayStamp(0)} – ${dayStamp(6)}`;
  readonlyNote.hidden = !week.read_only;
  document.getElementById("week-copy").disabled = week.read_only;
  document.getElementById("open-form").disabled = week.read_only;
  renderPalette();
  renderSummary();
  placeNow();
  if (focusId) sheet.querySelector(`[data-block-id="${focusId}"]`)?.focus();
}

function blockMarkup(block, grid) {
  const top = ((block.start_minute - grid.day_start_minute) / grid.slot_minutes) * SLOT_PX;
  const height = (block.duration_minutes / grid.slot_minutes) * SLOT_PX;
  const outcome = block.outcome
    ? `<span class="outcome-${block.outcome}">${OUTCOME[block.outcome]}</span>`
    : "";
  const actions = week.read_only
    ? ""
    : `<div class="block-actions"><button type="button" class="btn btn-primary block-start">Iniciar</button></div><div class="resize-handle" data-resize></div>`;
  return `
    <article class="study-block" tabindex="0" role="button" data-block-id="${block.id}"
      aria-label="${ariaLabel(block)}"
      style="top:${top}px;height:${height}px;border-left-color:${block.subject.color};background:${block.subject.color}22">
      <strong>${block.subject.name}</strong>
      <span>${hm(block.start_minute)}–${hm(block.start_minute + block.duration_minutes)}</span>
      <span>${block.planned_cycles} ciclos</span>
      ${outcome}
      ${actions}
    </article>`;
}

function placeNow() {
  sheet.querySelectorAll(".now-line").forEach((line) => line.remove());
  const minute = (Date.now() + offset - Date.parse(week.today_start)) / 60000;
  const day = Math.round(
    (Date.parse(`${week.today}T00:00:00Z`) - Date.parse(`${week.week_start}T00:00:00Z`)) / 86400000,
  );
  const grid = week.grid;
  if (day < 0 || day > 6 || minute < grid.day_start_minute || minute > grid.day_end_minute) return;
  const column = sheet.querySelector(`.cal-day[data-day="${day}"]`);
  if (!column) return;
  const line = document.createElement("div");
  line.className = "now-line";
  line.style.top = `${((minute - grid.day_start_minute) / grid.slot_minutes) * SLOT_PX}px`;
  column.append(line);
}

async function load(weekStart) {
  errorBox.hidden = true;
  week = await api.get(`/calendar/weeks/${weekStart}`);
  offset = Date.parse(week.server_now) - Date.now();
  fillForm();
  render();
}

function findBlock(id) {
  return week.blocks.find((block) => String(block.id) === String(id));
}

async function commitCreate(payload) {
  const previous = week.blocks.map((block) => ({ ...block }));
  const temp = {
    id: `tmp-${Date.now()}`,
    ...payload,
    subject: week.subjects.find((item) => item.id === payload.subject_id),
    planned_cycles: 1,
    outcome: null,
    week_start: week.week_start,
  };
  week.blocks.push(temp);
  render();
  try {
    const saved = await api.post("/calendar/blocks", {
      ...payload,
      week_start: week.week_start,
    });
    week.blocks = week.blocks.filter((block) => block.id !== temp.id);
    week.blocks.push(saved.block);
    render({ focusId: saved.block.id });
    announce(ariaLabel(saved.block));
    refreshSchedule();
  } catch (error) {
    week.blocks = previous;
    render();
    showError(error);
  }
}

async function commitPatch(block, patch) {
  const previous = { ...block };
  Object.assign(block, patch);
  render({ focusId: block.id });
  try {
    const saved = await api.patch(`/calendar/blocks/${block.id}`, patch);
    Object.assign(block, saved.block);
    render({ focusId: block.id });
    announce(ariaLabel(saved.block));
    refreshSchedule();
  } catch (error) {
    Object.assign(block, previous);
    render({ focusId: block.id });
    showError(error);
  }
}

async function commitDelete(block) {
  if (!window.confirm(`Apagar o bloco de ${block.subject.name}?`)) return;
  const previous = week.blocks.slice();
  week.blocks = week.blocks.filter((item) => item.id !== block.id);
  render();
  try {
    await api.del(`/calendar/blocks/${block.id}`);
    announce(`Bloco de ${block.subject.name} apagado.`);
    refreshSchedule();
  } catch (error) {
    week.blocks = previous;
    render({ focusId: block.id });
    showError(error);
  }
}

function columnAt(x, y) {
  const element = document.elementFromPoint(x, y);
  return element?.closest(".cal-day") || null;
}

function minuteAt(column, clientY) {
  const rect = column.getBoundingClientRect();
  const raw = week.grid.day_start_minute + ((clientY - rect.top) / SLOT_PX) * week.grid.slot_minutes;
  const slot = week.grid.slot_minutes;
  return Math.round(raw / slot) * slot;
}

function updateGhost(event) {
  let column = columnAt(event.clientX, event.clientY);
  drag.ghost?.remove();
  if (!column) {
    drag.valid = false;
    drag.target = null;
    return;
  }
  let day = Number(column.dataset.day);
  let start = drag.origin.start;
  let duration = drag.origin.duration;
  if (drag.mode === "resize") {
    const pointer = minuteAt(column, event.clientY);
    duration = Math.max(week.grid.slot_minutes, pointer - drag.origin.start);
    const slot = week.grid.slot_minutes;
    duration = Math.round(duration / slot) * slot;
    start = drag.origin.start;
    column = sheet.querySelector(`.cal-day[data-day="${drag.block.day_of_week}"]`) || column;
    day = drag.block.day_of_week;
  } else {
    const snapped = minuteAt(column, event.clientY - drag.offsetY);
    start = snapped;
  }
  const valid = placementOk(day, start, duration, drag.block?.id);
  drag.valid = valid;
  drag.target = { day_of_week: day, start_minute: start, duration_minutes: duration };
  const top = ((start - week.grid.day_start_minute) / week.grid.slot_minutes) * SLOT_PX;
  const height = (duration / week.grid.slot_minutes) * SLOT_PX;
  const ghost = document.createElement("div");
  ghost.className = `block-ghost${valid ? "" : " is-invalid"}`;
  ghost.style.top = `${top}px`;
  ghost.style.height = `${height}px`;
  column.append(ghost);
  drag.ghost = ghost;
}

function startDrag(event, spec) {
  drag = {
    ...spec,
    pointerId: event.pointerId,
    x: event.clientX,
    y: event.clientY,
    started: spec.mode !== "move",
    valid: false,
    target: null,
    ghost: null,
    offsetY: spec.offsetY || 0,
  };
  sheet.setPointerCapture?.(event.pointerId);
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
}

function onPointerMove(event) {
  if (!drag || event.pointerId !== drag.pointerId) return;
  if (Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 4) drag.started = true;
  if (!drag.started) return;
  updateGhost(event);
}

function onPointerUp(event) {
  if (!drag || event.pointerId !== drag.pointerId) return;
  window.removeEventListener("pointermove", onPointerMove);
  window.removeEventListener("pointerup", onPointerUp);
  const current = drag;
  drag.ghost?.remove();
  drag = null;
  if (!current.started) {
    if (current.block) offerBlock(current.block);
    return;
  }
  if (!current.valid || !current.target) {
    announce("Soltura cancelada.");
    return;
  }
  if (current.mode === "create") {
    commitCreate({
      subject_id: current.subjectId,
      day_of_week: current.target.day_of_week,
      start_minute: current.target.start_minute,
      duration_minutes: current.target.duration_minutes,
    });
    return;
  }
  commitPatch(current.block, {
    day_of_week: current.target.day_of_week,
    start_minute: current.target.start_minute,
    duration_minutes: current.target.duration_minutes,
  });
}

function watchPress(event, begin) {
  if (week?.read_only || event.button > 0) return;
  if (event.pointerType === "mouse") {
    begin(event);
    return;
  }
  const pointerId = event.pointerId;
  const originX = event.clientX;
  const originY = event.clientY;
  let opened = false;
  const timer = setTimeout(() => {
    opened = true;
    begin(event);
  }, 300);
  const cancel = (move) => {
    if (move.pointerId !== pointerId) return;
    if (Math.hypot(move.clientX - originX, move.clientY - originY) > 10) {
      clearTimeout(timer);
      cleanup();
    }
  };
  const up = (end) => {
    if (end.pointerId !== pointerId) return;
    if (!opened) clearTimeout(timer);
    cleanup();
  };
  function cleanup() {
    window.removeEventListener("pointermove", cancel);
    window.removeEventListener("pointerup", up);
    window.removeEventListener("pointercancel", up);
  }
  window.addEventListener("pointermove", cancel);
  window.addEventListener("pointerup", up);
  window.addEventListener("pointercancel", up);
}

palette.addEventListener("pointerdown", (event) => {
  const chip = event.target.closest("[data-subject-id]");
  if (!chip) return;
  watchPress(event, (start) => {
    const subject = week.subjects.find((item) => item.id === Number(chip.dataset.subjectId));
    startDrag(start, {
      mode: "create",
      subjectId: subject.id,
      origin: { start: week.grid.day_start_minute, duration: week.grid.block_min_minutes },
      offsetY: 0,
    });
  });
});

sheet.addEventListener("pointerdown", (event) => {
  if (event.target.closest("button")) return;
  const blockEl = event.target.closest(".study-block");
  if (!blockEl) return;
  const block = findBlock(blockEl.dataset.blockId);
  if (!block) return;
  const resize = event.target.closest("[data-resize]");
  watchPress(event, (start) => {
    const rect = blockEl.getBoundingClientRect();
    startDrag(start, {
      mode: resize ? "resize" : "move",
      block,
      origin: {
        start: block.start_minute,
        duration: block.duration_minutes,
      },
      offsetY: start.clientY - rect.top,
    });
  });
});

sheet.addEventListener("click", (event) => {
  const button = event.target.closest(".block-start");
  if (!button) return;
  event.stopPropagation();
  const block = findBlock(button.closest(".study-block").dataset.blockId);
  if (block) startBlock(block.id, { gesture: true });
});

sheet.addEventListener("keydown", (event) => {
  const blockEl = event.target.closest(".study-block");
  if (!blockEl || week.read_only) return;
  if (event.target.closest("button")) return;
  const block = findBlock(blockEl.dataset.blockId);
  if (!block) return;
  const slot = week.grid.slot_minutes;
  let patch = null;
  if (event.key === "Enter") {
    event.preventDefault();
    blockEl.querySelector(".block-start")?.focus();
    return;
  }
  if (event.key === "Delete" || event.key === "Backspace") {
    event.preventDefault();
    commitDelete(block);
    return;
  }
  if (event.key === "ArrowUp" && event.shiftKey) {
    patch = { duration_minutes: block.duration_minutes - slot };
  } else if (event.key === "ArrowDown" && event.shiftKey) {
    patch = { duration_minutes: block.duration_minutes + slot };
  } else if (event.key === "ArrowUp") {
    patch = { start_minute: block.start_minute - slot };
  } else if (event.key === "ArrowDown") {
    patch = { start_minute: block.start_minute + slot };
  } else if (event.key === "ArrowLeft") {
    patch = { day_of_week: block.day_of_week - 1 };
  } else if (event.key === "ArrowRight") {
    patch = { day_of_week: block.day_of_week + 1 };
  }
  if (!patch) return;
  event.preventDefault();
  const next = {
    day_of_week: patch.day_of_week ?? block.day_of_week,
    start_minute: patch.start_minute ?? block.start_minute,
    duration_minutes: patch.duration_minutes ?? block.duration_minutes,
  };
  if (!placementOk(next.day_of_week, next.start_minute, next.duration_minutes, block.id)) {
    announce("Não dá para mover o bloco para esse horário.");
    return;
  }
  commitPatch(block, patch);
});

document.getElementById("week-prev").addEventListener("click", () => load(shiftDate(week.week_start, -7)));
document.getElementById("week-next").addEventListener("click", () => load(shiftDate(week.week_start, 7)));
document.getElementById("week-today").addEventListener("click", () => load(mondayOf(week.today)));
document.getElementById("week-copy").addEventListener("click", async () => {
  try {
    week = await api.post(`/calendar/weeks/${week.week_start}/copy-from-previous`);
    offset = Date.parse(week.server_now) - Date.now();
    render();
    announce("Semana anterior copiada.");
    refreshSchedule();
  } catch (error) {
    showError(error);
  }
});
document.getElementById("open-form").addEventListener("click", () => {
  form.hidden = !form.hidden;
  if (!form.hidden) document.getElementById("block-subject").focus();
});
form.addEventListener("submit", (event) => {
  event.preventDefault();
  commitCreate({
    subject_id: Number(document.getElementById("block-subject").value),
    day_of_week: Number(document.getElementById("block-day").value),
    start_minute: Number(document.getElementById("block-start").value),
    duration_minutes: Number(document.getElementById("block-duration").value),
  });
});
document.getElementById("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setSoundEnabled(document.getElementById("sound-on").checked);
  try {
    const saved = await api.put("/pomodoro/settings", {
      focus_minutes: Number(document.getElementById("focus-minutes").value),
      short_break_minutes: Number(document.getElementById("short-break").value),
      long_break_minutes: Number(document.getElementById("long-break").value),
      cycles_before_long_break: Number(document.getElementById("cycle-count").value),
      auto_start_blocks: document.getElementById("auto-start").checked,
      focus_mode_enabled: document.getElementById("focus-mode").checked,
      focus_mode_fullscreen: document.getElementById("focus-fullscreen").checked,
      focus_mode_sound: document.getElementById("focus-sound").checked,
    });
    setFocusSettings(saved);
    week.settings = {
      focus_minutes: saved.focus_minutes,
      short_break_minutes: saved.short_break_minutes,
      long_break_minutes: saved.long_break_minutes,
      cycles_before_long_break: saved.cycles_before_long_break,
      auto_start_blocks: saved.auto_start_blocks,
      focus_mode_enabled: saved.focus_mode_enabled,
      focus_mode_fullscreen: saved.focus_mode_fullscreen,
      focus_mode_sound: saved.focus_mode_sound,
    };
    await load(week.week_start);
    showToast("Preferências salvas.");
    refreshSchedule();
  } catch (error) {
    showError(error);
  }
});
document.getElementById("loose-start").addEventListener("click", () => {
  const subjectId = Number(document.getElementById("block-subject").value || week.subjects[0]?.id);
  if (subjectId) startSubject(subjectId, { gesture: true });
});
document.getElementById("sound-on").addEventListener("change", (event) => {
  setSoundEnabled(event.target.checked);
});

setInterval(placeNow, 30000);

api
  .get("/pomodoro/settings")
  .then((settings) => load(mondayOf(settings.today)))
  .catch((error) => showError(error));
