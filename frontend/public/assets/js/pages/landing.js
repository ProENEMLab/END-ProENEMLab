import { getEnemCountdown, renderCountdownMarkup } from "../enem-dates.js";
import { api } from "../api.js";

const mount = document.getElementById("landing-countdown");
if (mount) {
  mount.innerHTML = renderCountdownMarkup(getEnemCountdown());
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "?";
}

async function loadTestimonials() {
  const section = document.getElementById("landing-testimonials");
  const grid = document.getElementById("landing-testimonials-grid");
  if (!section || !grid) return;
  try {
    const data = await api.get("/testimonials");
    const items = data.items || [];
    if (!items.length) {
      section.hidden = true;
      return;
    }
    grid.innerHTML = items.map((item) => `
      <article class="testimonial-card">
        <div class="testimonial-person">
          ${item.avatar_url
            ? `<img src="${escapeHtml(item.avatar_url)}" alt="">`
            : `<span class="testimonial-initials" aria-hidden="true">${escapeHtml(initials(item.display_name))}</span>`}
          <div>
            <strong>${escapeHtml(item.display_name)}</strong>
            <p class="muted">${escapeHtml(item.result_text)}</p>
          </div>
        </div>
        <blockquote>${escapeHtml(item.quote)}</blockquote>
      </article>
    `).join("");
    section.hidden = false;
  } catch {
    section.hidden = true;
  }
}

loadTestimonials();
