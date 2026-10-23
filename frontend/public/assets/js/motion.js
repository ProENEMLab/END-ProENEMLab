const REDUCE = window.matchMedia("(prefers-reduced-motion: reduce)");

const AUTO = [
  { sel: ".landing-band-dates", type: "clip" },
  { sel: ".landing-band > div:last-child", type: "slide" },
  { sel: ".landing-source-head", type: "rise" },
  { sel: ".source-facts > div", type: "rise", stagger: 70 },
  { sel: ".source-path li", type: "slide", stagger: 90 },
  { sel: ".feature-lead", type: "rise" },
  { sel: ".feature-card.is-lead", type: "clip" },
  { sel: ".feature-card:not(.is-lead)", type: "scale", stagger: 90 },
  { sel: ".landing-plans-lead", type: "rise" },
  { sel: ".landing-plan", type: "rise", stagger: 85 },
  { sel: ".landing-cta-inner", type: "clip" },
  { sel: ".public-footer-main", type: "fade" },
  { sel: ".plans-hero", type: "rise", eager: true },
  { sel: ".plan-card", type: "rise", stagger: 80 },
  { sel: ".plans-compare", type: "rise" },
  { sel: ".plans-faq", type: "rise" },
  { sel: ".page-header", type: "rise", eager: true },
  { sel: ".page-back", type: "fade", eager: true },
  { sel: ".filters", type: "rise", eager: true },
  { sel: ".dashboard-countdown-block", type: "clip", eager: true },
  { sel: ".dashboard-grid > *", type: "rise", stagger: 80 },
  { sel: ".stat-hero", type: "clip" },
  { sel: "#subject-focus", type: "rise" },
  { sel: ".progress-wrap", type: "rise" },
  { sel: ".question-sheet", type: "rise", eager: true },
  { sel: ".question-item", type: "rise", stagger: 45 },
  { sel: ".topic-item", type: "slide", stagger: 40 },
  { sel: ".option-card", type: "rise", stagger: 35 },
  { sel: ".topic-actions", type: "rise" },
  { sel: ".topic-notes", type: "fade" },
  { sel: ".note-card", type: "rise", stagger: 50 },
  { sel: ".grid-2 > .card", type: "scale", stagger: 80 },
  { sel: ".testimonial-card", type: "rise", stagger: 70 },
];

const SKIP = new WeakSet();
let io;

function reduced() {
  return REDUCE.matches;
}

function inView(el) {
  const rect = el.getBoundingClientRect();
  return rect.bottom > 0 && rect.top < window.innerHeight * 0.92;
}

function show(el) {
  if (el.classList.contains("is-in")) return;
  el.classList.add("is-in");
  if (reduced()) {
    el.classList.add("is-settled");
    return;
  }
  const settle = (event) => {
    if (event.target !== el) return;
    el.classList.add("is-settled");
    el.removeEventListener("animationend", settle);
  };
  el.addEventListener("animationend", settle);
  window.setTimeout(() => el.classList.add("is-settled"), 1200);
}

function mark(el, type, delay) {
  if (SKIP.has(el) || el.hasAttribute("data-reveal")) return;
  if (el.closest("[hidden]")) return;
  el.setAttribute("data-reveal", type);
  if (delay) el.style.setProperty("--motion-delay", `${delay}ms`);
  SKIP.add(el);
  if (reduced() || inView(el)) {
    show(el);
    return;
  }
  io?.observe(el);
}

function scan(root = document) {
  for (const rule of AUTO) {
    const nodes = root.querySelectorAll(rule.sel);
    nodes.forEach((el, i) => {
      const delay = rule.stagger ? i * rule.stagger : 0;
      mark(el, rule.type, delay);
      if (rule.eager && !reduced()) show(el);
    });
  }
  tickNumbers(root);
}

function tickNumbers(root) {
  if (reduced()) return;
  const nodes = root.querySelectorAll?.(".countdown-number, .stat-hero .value, #subject-focus .value") || [];
  nodes.forEach((el) => {
    if (el.dataset.counted === "1") return;
    if (el.closest("[hidden]")) return;
    const raw = el.textContent.trim().replace(/%$/, "");
    if (!/^\d+$/.test(raw)) return;
    const target = Number(raw);
    if (target === 0) return;
    const suffix = el.textContent.includes("%") ? "%" : "";
    el.dataset.counted = "1";
    el.classList.add("is-counting");
    const duration = Math.min(1100, 380 + Math.min(target, 200) * 3);
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) ** 3;
      el.textContent = `${Math.round(target * eased)}${suffix}`;
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = `${target}${suffix}`;
    };
    el.textContent = `0${suffix}`;
    requestAnimationFrame(step);
  });
}

function boot() {
  io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        show(entry.target);
        io.unobserve(entry.target);
      }
    },
    { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
  );

  scan();
  document.documentElement.classList.add("js-reveal");

  let queued = false;
  const mo = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      scan();
    });
  });
  mo.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["hidden"],
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}
