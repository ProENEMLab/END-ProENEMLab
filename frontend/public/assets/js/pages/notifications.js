import { api } from "../api.js";
import { showToast } from "../components/toast.js";

const TYPES = [
  { id: "daily_goal", label: "Meta diária não cumprida", timed: true },
  { id: "reviews_due", label: "Revisões do dia", timed: true },
  { id: "streak_at_risk", label: "Sequência em risco", timed: true },
  { id: "study_block", label: "Início de bloco do calendário", timed: false },
];

const LABELS = {
  daily_goal: "meta diária",
  reviews_due: "revisões",
  streak_at_risk: "sequência",
  study_block: "bloco de estudo",
  email: "e-mail",
  push: "navegador",
  sent: "enviado",
  failed: "falhou",
  skipped_quiet_hours: "pulado no silêncio",
  skipped_condition: "não era mais necessário",
  deferred_focus: "adiado pelo foco",
};

const errorBox = document.getElementById("notify-error");
const matrix = document.getElementById("type-matrix");
const pushState = document.getElementById("push-state");
const pushOn = document.getElementById("push-on");
const pushOff = document.getElementById("push-off");
let current = null;
let endpoint = null;

function showError(message) {
  errorBox.hidden = !message;
  errorBox.textContent = message || "";
}

function times() {
  const options = [];
  for (let hour = 0; hour < 24; hour += 1) {
    for (const minute of [0, 15, 30, 45]) {
      options.push(`${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
    }
  }
  return options;
}

function fillSelect(select, value) {
  select.innerHTML = times()
    .map((item) => `<option value="${item}" ${item === value ? "selected" : ""}>${item}</option>`)
    .join("");
}

function renderMatrix() {
  matrix.innerHTML = `
    <div class="notify-head"></div>
    <div class="notify-head">E-mail</div>
    <div class="notify-head">Push</div>
    <div class="notify-head">Horário</div>
    ${TYPES.map((type) => {
      const slot = current.types[type.id];
      const time = type.timed
        ? `<select data-kind="${type.id}" data-field="time">${times()
            .map((item) => `<option value="${item}" ${item === slot.time ? "selected" : ""}>${item}</option>`)
            .join("")}</select>`
        : "<span class=\"muted\">10 min antes</span>";
      return `
        <div>${type.label}</div>
        <label class="check-row"><input type="checkbox" data-kind="${type.id}" data-field="email" ${slot.email ? "checked" : ""}></label>
        <label class="check-row"><input type="checkbox" data-kind="${type.id}" data-field="push" ${slot.push ? "checked" : ""}></label>
        <div>${time}</div>`;
    }).join("")}`;
}

function collect() {
  const types = {};
  TYPES.forEach((type) => {
    const slot = {
      email: matrix.querySelector(`[data-kind="${type.id}"][data-field="email"]`).checked,
      push: matrix.querySelector(`[data-kind="${type.id}"][data-field="push"]`).checked,
    };
    if (type.timed) slot.time = matrix.querySelector(`[data-kind="${type.id}"][data-field="time"]`).value;
    types[type.id] = slot;
  });
  return {
    email_enabled: document.getElementById("email-enabled").checked,
    push_enabled: current.push_enabled,
    quiet_start: document.getElementById("quiet-start").value,
    quiet_end: document.getElementById("quiet-end").value,
    types,
  };
}

function urlBase64ToUint8Array(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let index = 0; index < raw.length; index += 1) output[index] = raw.charCodeAt(index);
  return output;
}

function pushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

async function describePush() {
  pushOn.hidden = true;
  pushOff.hidden = true;
  if (!pushSupported()) {
    pushState.textContent = "Este navegador não suporta notificações push.";
    return;
  }
  if (Notification.permission === "denied") {
    pushState.textContent =
      "O navegador bloqueou os avisos. Abra o cadeado na barra de endereço, permita notificações e recarregue a página.";
    return;
  }
  const registration = await navigator.serviceWorker.getRegistration("/");
  const subscription = registration ? await registration.pushManager.getSubscription() : null;
  endpoint = subscription ? subscription.endpoint : null;
  if (subscription && current.push_enabled) {
    pushState.textContent = "Push ativo neste navegador.";
    pushOff.hidden = false;
    return;
  }
  pushState.textContent = "Push ainda não está ativo neste navegador.";
  pushOn.hidden = false;
}

function renderLast(items) {
  const sent = items.find((item) => item.status === "sent");
  const target = document.getElementById("last-log");
  if (!sent) {
    target.textContent = "Nenhum lembrete enviado ainda.";
    return;
  }
  const when = sent.local_date ? sent.local_date.split("-").reverse().join("/") : "";
  target.textContent = `Último lembrete enviado: ${LABELS[sent.type] || sent.type} por ${LABELS[sent.channel] || sent.channel} em ${when} (${LABELS[sent.status] || sent.status}).`;
}

async function save(payload) {
  const data = await api.put("/notifications/preferences", payload || collect());
  current = data.preferences;
  document.getElementById("email-enabled").checked = current.email_enabled;
  fillSelect(document.getElementById("quiet-start"), current.quiet_start);
  fillSelect(document.getElementById("quiet-end"), current.quiet_end);
  renderMatrix();
  await describePush();
}

document.getElementById("save").addEventListener("click", async () => {
  try {
    showError("");
    await save();
    showToast("Preferências salvas.");
  } catch (err) {
    showError(err.message);
  }
});

pushOn.addEventListener("click", async () => {
  if (!pushSupported()) return;
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    await describePush();
    showToast("O navegador não autorizou os avisos.", "error");
    return;
  }
  try {
    const registration = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    const { public_key: publicKey } = await api.get("/notifications/push/public-key");
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
    const json = subscription.toJSON();
    await api.post("/notifications/push/subscriptions", {
      endpoint: json.endpoint,
      keys: json.keys,
    });
    endpoint = json.endpoint;
    const payload = collect();
    payload.push_enabled = true;
    await save(payload);
    showToast("Push ativo neste navegador.");
  } catch (err) {
    showError(err.message);
  }
});

pushOff.addEventListener("click", async () => {
  try {
    if (endpoint) await api.del("/notifications/push/subscriptions", { endpoint });
    const registration = await navigator.serviceWorker.getRegistration("/");
    const subscription = registration ? await registration.pushManager.getSubscription() : null;
    if (subscription) await subscription.unsubscribe();
    endpoint = null;
    const payload = collect();
    payload.push_enabled = false;
    await save(payload);
    showToast("Push desativado neste navegador.");
  } catch (err) {
    showError(err.message);
  }
});

async function sendTest(channel) {
  try {
    showError("");
    await api.post("/notifications/test", { channel });
    showToast(channel === "email" ? "Teste de e-mail enviado." : "Teste de push enviado.");
    renderLast((await api.get("/notifications/log?limit=20")).log || []);
  } catch (err) {
    showError(err.message);
  }
}

document.getElementById("test-email").addEventListener("click", () => sendTest("email"));
document.getElementById("test-push").addEventListener("click", () => sendTest("push"));

async function load() {
  try {
    current = (await api.get("/notifications/preferences")).preferences;
    document.getElementById("email-enabled").checked = current.email_enabled;
    fillSelect(document.getElementById("quiet-start"), current.quiet_start);
    fillSelect(document.getElementById("quiet-end"), current.quiet_end);
    renderMatrix();
    await describePush();
    renderLast((await api.get("/notifications/log?limit=20")).log || []);
  } catch (err) {
    showError(err.message);
  }
}

load();
