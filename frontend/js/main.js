// App shell, routing and session handling.
import { api, getToken, setToken, getViewCompany, setViewCompany, onUnauthorized } from "./api.js";
import { html, mount, $, $$, icon, logo, toast, modal, bindForm, recordName } from "./ui.js";
import * as loginView from "./views/login.js";
import * as dashboard from "./views/dashboard.js";
import * as agents from "./views/agents.js";
import * as studio from "./views/studio.js";
import * as calls from "./views/calls.js";
import * as records from "./views/records.js";
import * as knowledge from "./views/knowledge.js";
import * as billing from "./views/billing.js";
import * as admin from "./views/admin.js";

const state = { user: null, config: null };
const app = $("#app");
let cleanup = null;

const CLIENT = [
  ["dashboard", "Dashboard", "dashboard", dashboard], ["agents", "Agents", "agents", agents], ["studio", "Voice Studio", "mic", studio],
  ["calls", "Calls", "phone", calls], ["records", "records", "records", records], ["knowledge", "Knowledge base", "book", knowledge], ["billing", "Plan and usage", "card", billing],
];
const ADMIN = [["admin", "Overview", "overview", { render: admin.renderOverview }], ["admin/companies", "Companies", "building", { render: admin.renderCompanies }]];
const isAdmin = () => state.user && state.user.role === "super_admin";
const company = () => getViewCompany() || (state.user && state.user.company_id ? { id: state.user.company_id, name: state.user.company_name, industry: state.user.company_industry } : null);

function logout(message) {
  setToken(null); setViewCompany(null); state.user = null; state.config = null;
  if (cleanup) { cleanup(); cleanup = null; }
  showLogin();
  if (message) toast(message);
}
onUnauthorized(() => logout("Your session ended. Please sign in again."));

function showLogin() {
  location.hash = "";
  loginView.render(app, async ({ token, user }) => {
    setToken(token); state.user = user; setViewCompany(null);
    state.config = await api("/api/meta/config");
    drawShell(); route();
  });
}

function drawShell() {
  const c = company(), admin_ = isAdmin(), viewing = admin_ && getViewCompany();
  const link = ([path, label, ic]) => html`<a href="#/${path}" data-path="${path}">${icon(ic)}<span>${path === "records" ? recordName(c && c.industry) : label}</span></a>`;
  mount(app, html`<div class="shell">
    <aside class="rail" id="rail"><div class="brand">${logo()}<div>Voxora Voice<small>Intelligent Conversations.</small></div></div>
      <nav class="nav" aria-label="Main">
        ${admin_ ? html`<div class="group">Voxora team</div>${ADMIN.map(link)}` : ""}
        ${c ? html`<div class="group">${admin_ ? html`Viewing ${c.name}` : c.name}</div>${CLIENT.map(link)}` : ""}
      </nav>
      <div class="rail-foot"><b>${state.user.name}</b>${state.user.email}<div class="row" style="margin-top:10px">
        <button class="btn small" id="pw" style="background:transparent;color:#fff;border-color:var(--ink-2)">${icon("key")} Password</button>
        <button class="btn small" id="out" style="background:transparent;color:#fff;border-color:var(--ink-2)">${icon("logout")} Sign out</button></div></div></aside>
    <div class="main">
      ${viewing ? html`<div class="viewing"><span>Super Admin view of <b>${c.name}</b>. Changes you make are real.</span><button class="btn small" id="exit">Back to companies</button></div>` : ""}
      <div class="topbar"><button class="btn ghost menu" id="menu" aria-label="Open menu">${icon("menu")}</button></div>
      <div id="notice" style="padding:0 32px"></div><main class="page" id="view"></main></div></div>`);
  $("#out").addEventListener("click", () => logout());
  $("#pw").addEventListener("click", changePassword);
  $("#menu").addEventListener("click", () => $("#rail").classList.toggle("open"));
  $("#rail").addEventListener("click", (e) => { if (e.target.closest("a")) $("#rail").classList.remove("open"); });
  const exit = $("#exit");
  if (exit) exit.addEventListener("click", () => { setViewCompany(null); drawShell(); location.hash = "#/admin/companies"; });
  if (state.user.must_change) {
    $("#notice").innerHTML = '<div class="notice"><span>You are using a starter password. Please change it now.</span><button class="btn small primary" id="pw2">Change password</button></div>';
    $("#pw2").addEventListener("click", changePassword);
  }
}

function changePassword() {
  const m = modal("Change password", html`<form id="pf"><div class="field"><label for="a">Current password</label><input id="a" name="current_password" type="password" autocomplete="current-password" required></div>
    <div class="field"><label for="b">New password</label><input id="b" name="new_password" type="password" autocomplete="new-password" required minlength="8"><span class="hint">At least 8 characters.</span></div>
    <div class="err" role="alert"></div><div class="row" style="justify-content:flex-end"><button type="button" class="btn" data-close>Cancel</button><button class="btn primary" type="submit">Update password</button></div></form>`);
  bindForm($("#pf", m.el), async (v) => {
    await api("/api/auth/change-password", { method: "POST", body: v });
    state.user.must_change = 0; m.close(); const n = $(".notice"); if (n) n.remove(); toast("Password updated", "ok");
  });
}

async function route() {
  if (!state.user) return;
  const first = isAdmin() && !getViewCompany() ? "admin" : "dashboard";
  const path = (location.hash.replace(/^#\/?/, "").split("?")[0]) || first;
  const adminRoute = ADMIN.find((r) => r[0] === path), clientRoute = CLIENT.find((r) => r[0] === path);
  if (!adminRoute && !clientRoute) { location.hash = `#/${first}`; return; }
  if (adminRoute && !isAdmin()) { location.hash = "#/dashboard"; return; }
  if (clientRoute && !company()) { toast("Choose a company first."); location.hash = "#/admin/companies"; return; }
  if (cleanup) { cleanup(); cleanup = null; }
  $$("#rail [data-path]").forEach((a) => { if (a.dataset.path === path) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  const view = $("#view");
  view.innerHTML = '<div class="panel panel-body"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>';
  document.title = `${(adminRoute || clientRoute)[1] === "records" ? "Records" : (adminRoute || clientRoute)[1]} · Voxora Voice`;
  const openCompany = (c) => { setViewCompany(c); drawShell(); location.hash = "#/dashboard"; };
  try {
    view.innerHTML = "";
    const mod = (adminRoute || clientRoute)[3];
    cleanup = (await mod.render({ el: view, state, company: company(), openCompany })) || null;
  } catch (e) {
    view.innerHTML = `<div class="panel empty"><h3>Something went wrong</h3><p></p></div>`;
    $("p", view).textContent = e.message || String(e);
  }
}

window.addEventListener("hashchange", route);

(async function boot() {
  if (!getToken()) return showLogin();
  try {
    state.user = await api("/api/auth/me");
    state.config = await api("/api/meta/config");
    if (!isAdmin()) setViewCompany(null);
    drawShell(); route();
  } catch { setToken(null); showLogin(); }
})();
