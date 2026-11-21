// Small UI toolkit: safe HTML templates, icons, toasts, modals, formatting.
const MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => MAP[c]);
export const raw = (s) => ({ __raw: true, s });
const val = (v) => (Array.isArray(v) ? v.map(val).join("") : v && v.__raw ? v.s : esc(v));
/** Tagged template. Every ${value} is escaped unless it came from another html`` call. */
export function html(strings, ...vals) {
  let out = "";
  strings.forEach((s, i) => { out += s + (i < vals.length ? val(vals[i]) : ""); });
  return raw(out);
}
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
export const mount = (el, tpl) => { el.innerHTML = tpl.s; return el; };

const ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  agents: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M9 13v1.5M15 13v1.5M2 13v3M22 13v3"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  phone: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
  records: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19V5M9 7h6"/>',
  card: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3 10h18M7 15h3"/>',
  building: '<path d="M4 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16M16 9h2a2 2 0 0 1 2 2v10M2 21h20M8 8h4M8 12h4M8 16h4"/>',
  overview: '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  send: '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 4 6"/>',
};
export const icon = (name) => raw(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`);

export const logo = (size = 34) => raw(`<svg width="${size}" height="${size}" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#123a40"/><g fill="#f6a21e"><rect x="6" y="13" width="3" height="6" rx="1.5"/><rect x="11" y="8" width="3" height="16" rx="1.5"/><rect x="16" y="5" width="3" height="22" rx="1.5"/><rect x="21" y="10" width="3" height="12" rx="1.5"/></g></svg>`);

// ---------- formatting ----------
export const fmtDate = (iso) => new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
export const fmtDay = (iso) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
export const fmtDur = (s) => (s >= 60 ? `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s` : `${s}s`);
export const fmtNum = (n) => Number(n || 0).toLocaleString("en-IN");
export const inr = (n) => (n ? "₹" + fmtNum(n) : "Free");
export const LANGS = { en: "English", hi: "Hindi", gu: "Gujarati" };
export const RECORD_NAMES = { real_estate: ["Lead", "Leads"], healthcare: ["Appointment", "Appointments"], education: ["Enquiry", "Enquiries"], sales: ["Lead", "Leads"], support: ["Ticket", "Tickets"] };
export const recordName = (industry, plural = true) => (RECORD_NAMES[industry] || ["Record", "Records"])[plural ? 1 : 0];

const STATUS = { completed: ["good", "Completed"], partial: ["warn", "Partial"], transferred: ["brand", "Transferred"], abandoned: ["", "Dropped"] };
const SENT = { positive: ["good", "Positive"], neutral: ["", "Neutral"], negative: ["bad", "Negative"] };
export const statusPill = (s) => html`<span class="pill ${(STATUS[s] || [""])[0]}">${(STATUS[s] || [0, s])[1]}</span>`;
export const sentimentPill = (s) => html`<span class="pill ${(SENT[s] || [""])[0]}"><span class="dot"></span>${(SENT[s] || [0, s])[1]}</span>`;
export const scoreBar = (n) => html`<span class="score num"><span class="meter ${n >= 70 ? "hot" : ""}"><i style="width:${n}%"></i></span>${n}</span>`;
export const skeleton = (rows = 4) => html`<div class="panel panel-body">${Array.from({ length: rows }, () => html`<div class="skeleton"></div>`)}</div>`;
export const empty = (title, text, action = "") => html`<div class="empty"><h3>${title}</h3><p>${text}</p>${action}</div>`;
export const debounce = (fn, ms = 250) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

// ---------- toasts, modals, drawers ----------
export function toast(message, type = "") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), type === "error" ? 6000 : 3500);
}

function overlay(cls, inner) {
  const root = document.createElement("div");
  root.className = `overlay ${cls}`;
  root.innerHTML = inner.s;
  const close = () => { root.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  document.addEventListener("keydown", onKey);
  root.addEventListener("mousedown", (e) => { if (e.target === root) close(); });
  $$("[data-close]", root).forEach((b) => b.addEventListener("click", close));
  document.body.append(root);
  const first = $("input, select, textarea, button.primary", root);
  if (first) first.focus();
  return { el: root, close };
}
const head = (title) => html`<div class="panel-head"><h2>${title}</h2><button class="btn ghost small" data-close aria-label="Close">${icon("x")}</button></div>`;
export const modal = (title, body) => overlay("", html`<div class="modal" role="dialog" aria-modal="true" aria-label="${title}">${head(title)}<div class="panel-body">${body}</div></div>`);
export const drawer = (title, body) => overlay("side", html`<aside class="drawer" role="dialog" aria-modal="true" aria-label="${title}">${head(title)}${body}</aside>`);

export function confirmBox(message, okLabel = "Delete") {
  return new Promise((resolve) => {
    const m = modal("Please confirm", html`<p>${message}</p><div class="row" style="margin-top:18px;justify-content:flex-end"><button class="btn" data-close>Cancel</button><button class="btn danger" id="ok">${okLabel}</button></div>`);
    $("#ok", m.el).addEventListener("click", () => { m.close(); resolve(true); });
    m.el.addEventListener("click", (e) => { if (e.target === m.el || e.target.closest("[data-close]")) resolve(false); });
  });
}

/** Submit helper: disables the button, shows errors under the form, closes on success. */
export function bindForm(form, handler) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("button[type=submit]", form), err = $(".err", form);
    if (err) err.textContent = "";
    btn.disabled = true;
    try { await handler(Object.fromEntries(new FormData(form))); }
    catch (ex) { if (err) err.textContent = ex.message; else toast(ex.message, "error"); }
    finally { btn.disabled = false; }
  });
}
export const options = (items, selected) => items.map(([v, l]) => html`<option value="${v}" ${String(v) === String(selected) ? raw("selected") : ""}>${l}</option>`);
