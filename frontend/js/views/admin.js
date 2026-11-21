import { api } from "../api.js";
import { html, mount, $, $$, skeleton, empty, modal, toast, bindForm, options, icon, fmtNum, fmtDay, inr } from "../ui.js";
import { barChart } from "../charts.js";

const INDUSTRY = { real_estate: "Real estate", healthcare: "Healthcare", education: "Education", sales: "Sales", support: "Support" };
const usageCell = (c) => { const p = c.minutes_limit ? Math.min(100, Math.round((100 * c.minutes_used) / c.minutes_limit)) : 0; return html`<div style="min-width:130px"><div class="meter ${p >= 100 ? "over" : p >= 80 ? "hot" : ""}"><i style="width:${p}%"></i></div><span class="muted small num">${fmtNum(Math.round(c.minutes_used))} / ${fmtNum(c.minutes_limit)} min</span></div>`; };

export async function renderOverview({ el, openCompany }) {
  mount(el, html`<div class="page-head"><div><h1>Platform overview</h1><p>Every company on Voxora Voice.</p></div><a class="btn primary" href="#/admin/companies">${icon("building")} Manage companies</a></div><div id="body">${skeleton(5)}</div>`);
  let d;
  try { d = await api("/api/admin/overview"); } catch (e) { return mount($("#body", el), html`<div class="panel">${empty("Could not load", e.message)}</div>`); }
  const t = d.totals;
  mount($("#body", el), html`<div class="band">
      <div><div class="v num">${t.companies}</div><div class="l">Companies, ${t.active} active</div></div>
      <div><div class="v num">${fmtNum(t.calls_30d)}</div><div class="l">Calls, last 30 days</div></div>
      <div><div class="v num">${fmtNum(Math.round(t.minutes_month))}</div><div class="l">Voice minutes this month</div></div>
      <div><div class="v num">${t.agents}</div><div class="l">Agents configured</div></div></div>
    <section class="panel" style="margin-top:18px"><div class="panel-head"><h2>Calls per day, all companies</h2></div><div class="panel-body">${barChart(d.daily)}</div></section>
    <section class="panel" style="margin-top:18px"><div class="panel-head"><h2>Companies</h2></div>${companyTable(d.companies, false)}</section>`);
  wireOpen(el, d.companies, openCompany);
}

function companyTable(list, manage) {
  if (!list.length) return empty("No companies yet", "Create the first client company to get started.");
  return html`<div class="table-wrap"><table><thead><tr><th>Company</th><th>Plan usage</th><th class="right">Calls (30d)</th><th>Status</th><th></th></tr></thead><tbody>
    ${list.map((c) => html`<tr><td><b>${c.name}</b><div class="muted small">${INDUSTRY[c.industry] || c.industry} · ${c.agents} agents · ${c.users} users</div></td><td>${usageCell(c)}</td><td class="right num">${c.calls_30d}</td>
      <td><span class="pill ${c.status === "active" ? "good" : "bad"}">${c.status === "active" ? "Active" : "Suspended"}</span></td>
      <td class="right" style="white-space:nowrap"><button class="btn small primary" data-open="${c.id}">Open</button>${manage ? html` <button class="btn small" data-edit="${c.id}">Edit</button> <button class="btn small" data-users="${c.id}">Users</button>` : ""}</td></tr>`)}</tbody></table></div>`;
}
const wireOpen = (el, list, openCompany) => $$("[data-open]", el).forEach((b) => b.addEventListener("click", () => openCompany(list.find((c) => c.id === +b.dataset.open))));

export async function renderCompanies({ el, state, openCompany }) {
  const packs = await api("/api/meta/packs");
  const plans = state.config.plans;
  mount(el, html`<div class="page-head"><div><h1>Companies</h1><p>Create client companies, set their plan, and manage their logins.</p></div><button class="btn primary" id="new">${icon("plus")} New company</button></div><section class="panel" id="list">${skeleton(4)}</section>`);
  const list = $("#list", el);
  let companies = [];
  const planOpts = (sel) => options(plans.map((p) => [p.key, `${p.label}, ${fmtNum(p.minutes)} min, ${inr(p.price_inr)}`]), sel);
  const packOpts = (sel) => options(packs.map((p) => [p.key, p.label]), sel);

  async function load() {
    try { companies = await api("/api/admin/companies"); } catch (e) { return mount(list, empty("Could not load companies", e.message)); }
    mount(list, companyTable(companies, true));
    wireOpen(list, companies, openCompany);
    $$("[data-edit]", list).forEach((b) => b.addEventListener("click", () => edit(companies.find((c) => c.id === +b.dataset.edit))));
    $$("[data-users]", list).forEach((b) => b.addEventListener("click", () => users(companies.find((c) => c.id === +b.dataset.users))));
  }

  $("#new", el).addEventListener("click", () => {
    const m = modal("New company", html`<form id="cf">
      <div class="field"><label for="n">Company name</label><input id="n" name="name" type="text" required minlength="2" maxlength="80"></div>
      <div class="grid2"><div class="field"><label for="i">Industry</label><select id="i" name="industry">${packOpts()}</select></div><div class="field"><label for="p">Plan</label><select id="p" name="plan">${planOpts("trial")}</select></div></div>
      <div class="field"><label for="ce">Company contact email (optional)</label><input id="ce" name="contact_email" type="email"></div>
      <h3 style="margin:6px 0 10px">First client login</h3>
      <div class="grid2"><div class="field"><label for="an">Name</label><input id="an" name="admin_name" type="text" required minlength="2"></div><div class="field"><label for="ae">Email</label><input id="ae" name="admin_email" type="email" required></div></div>
      <div class="field"><label for="ap">Temporary password</label><input id="ap" name="admin_password" type="text" required minlength="8" autocomplete="off"><span class="hint">At least 8 characters. Share it securely; the client can change it after signing in.</span></div>
      <div class="err" role="alert"></div><div class="row" style="justify-content:flex-end"><button type="button" class="btn" data-close>Cancel</button><button class="btn primary" type="submit">Create company</button></div></form>`);
    bindForm($("#cf", m.el), async (v) => { await api("/api/admin/companies", { method: "POST", body: { ...v, name: v.name.trim() } }); m.close(); toast("Company created", "ok"); load(); });
  });

  function edit(c) {
    const m = modal(`Edit ${c.name}`, html`<form id="ef">
      <div class="field"><label for="n">Company name</label><input id="n" name="name" type="text" required minlength="2" value="${c.name}"></div>
      <div class="grid2"><div class="field"><label for="i">Industry</label><select id="i" name="industry">${packOpts(c.industry)}</select></div><div class="field"><label for="p">Plan</label><select id="p" name="plan">${planOpts(c.plan)}</select></div></div>
      <div class="field"><label for="s">Status</label><select id="s" name="status">${options([["active", "Active"], ["suspended", "Suspended (logins and calls blocked)"]], c.status)}</select></div>
      <div class="err" role="alert"></div><div class="row" style="justify-content:flex-end"><button type="button" class="btn" data-close>Cancel</button><button class="btn primary" type="submit">Save changes</button></div></form>`);
    bindForm($("#ef", m.el), async (v) => { await api(`/api/admin/companies/${c.id}`, { method: "PATCH", body: v }); m.close(); toast("Company updated", "ok"); load(); });
  }

  async function users(c) {
    const m = modal(`Logins for ${c.name}`, html`<div id="ul">${skeleton(2)}</div>`);
    const draw = async () => {
      const us = await api(`/api/admin/companies/${c.id}/users`);
      mount($("#ul", m.el), html`<table><tbody>${us.map((u) => html`<tr><td style="padding-left:0"><b>${u.name}</b><div class="muted small">${u.email} · ${u.role === "client_admin" ? "Can edit" : "View only"}</div></td>
        <td class="right" style="padding-right:0;white-space:nowrap"><button class="btn small" data-reset="${u.id}">Reset password</button> <button class="btn small ${u.active ? "danger" : ""}" data-toggle="${u.id}">${u.active ? "Disable" : "Enable"}</button></td></tr>`)}</tbody></table>
        <form id="uf" style="margin-top:16px;border-top:1px solid var(--line);padding-top:16px"><h3 style="margin-bottom:10px">Add a login</h3>
        <div class="grid2"><div class="field"><input name="name" type="text" placeholder="Name" required minlength="2" aria-label="Name"></div><div class="field"><input name="email" type="email" placeholder="Email" required aria-label="Email"></div></div>
        <div class="grid2"><div class="field"><input name="password" type="text" placeholder="Temporary password" required minlength="8" autocomplete="off" aria-label="Password"></div>
        <div class="field"><select name="role" aria-label="Role"><option value="client_user">View only</option><option value="client_admin">Can edit</option></select></div></div>
        <div class="err" role="alert"></div><button class="btn primary" type="submit">Add login</button></form>`);
      $$("[data-toggle]", m.el).forEach((b) => b.addEventListener("click", async () => { const u = us.find((x) => x.id === +b.dataset.toggle); try { await api(`/api/admin/users/${u.id}`, { method: "PATCH", body: { active: !u.active } }); draw(); } catch (e) { toast(e.message, "error"); } }));
      $$("[data-reset]", m.el).forEach((b) => b.addEventListener("click", async () => {
        const pw = prompt("New temporary password (at least 8 characters):");
        if (!pw) return;
        try { await api(`/api/admin/users/${b.dataset.reset}`, { method: "PATCH", body: { password: pw } }); toast("Password reset. They will be asked to change it.", "ok"); } catch (e) { toast(e.message, "error"); }
      }));
      bindForm($("#uf", m.el), async (v) => { await api(`/api/admin/companies/${c.id}/users`, { method: "POST", body: v }); toast("Login added", "ok"); load(); draw(); });
    };
    draw().catch((e) => toast(e.message, "error"));
  }
  await load();
}
