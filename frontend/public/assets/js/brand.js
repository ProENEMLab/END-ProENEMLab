export function brandLockup({ href = "/", extraClass = "", linked = true } = {}) {
  const classes = ["brand-lockup", extraClass].filter(Boolean).join(" ");
  const inner = `
    <img class="brand-mark" src="/assets/images/logo-mark.png" alt="">
    <span class="brand-wordmark" aria-hidden="true">Pro<span>ENEM</span> Lab</span>
  `;
  if (!linked) {
    return `<span class="${classes}">${inner}</span>`;
  }
  return `<a class="${classes}" href="${href}" aria-label="ProENEM Lab">${inner}</a>`;
}
