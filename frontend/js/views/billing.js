import { api } from "../api.js";
import { html, mount, $, skeleton, empty, fmtNum, inr } from "../ui.js";
import { barChart } from "../charts.js";

export async function render({ el }) {
  mount(el, html`<div class="page-head"><div><h1>Plan and usage</h1><p>Voice minutes used this month.</p></div></div><div id="body">${skeleton(5)}</div>`);
  let u;
  try { u = await api("/api/usage"); } catch (e) { return mount($("#body", el), html`<div class="panel">${empty("Could not load usage", e.message)}</div>`); }
  const hot = u.percent >= 80;
  mount($("#body", el), html`<div class="cols">
    <div class="stack">
      <section class="panel"><div class="panel-head"><h2>${u.plan.label} plan</h2><span class="pill ${hot ? "warn" : "good"}">${hot ? "Running low" : "On track"}</span></div>
        <div class="panel-body"><div class="band" style="grid-template-columns:repeat(3,1fr);border:0">
          <div style="border:0;padding-left:0"><div class="v num">${fmtNum(Math.round(u.minutes_used))}</div><div class="l">Minutes used</div></div>
          <div><div class="v num">${fmtNum(u.minutes_limit)}</div><div class="l">Minutes in plan</div></div>
          <div><div class="v num">${inr(u.plan.price_inr)}</div><div class="l">Per month</div></div></div>
          <div class="meter ${u.percent >= 100 ? "over" : hot ? "hot" : ""}" style="margin-top:12px" role="progressbar" aria-valuenow="${u.percent}" aria-valuemin="0" aria-valuemax="100"><i style="width:${u.percent}%"></i></div>
          <p class="muted small" style="margin-top:8px">${u.percent}% of this month's minutes used. When the plan is used up, new calls pause until the plan is upgraded.</p></div></section>
      <section class="panel"><div class="panel-head"><h2>Minutes per day, this month</h2></div><div class="panel-body">${barChart(u.daily, "minutes", " min")}</div></section>
    </div>
    <div class="stack">
      <section class="panel"><div class="panel-head"><h2>By agent</h2></div>${u.by_agent.length ? html`<div class="table-wrap"><table><thead><tr><th>Agent</th><th class="right">Calls</th><th class="right">Minutes</th></tr></thead><tbody>${u.by_agent.map((a) => html`<tr><td>${a.k}</td><td class="right num">${a.calls}</td><td class="right num">${a.minutes}</td></tr>`)}</tbody></table></div>` : empty("No usage yet", "Minutes appear after your first call this month.")}</section>
      <section class="panel"><div class="panel-head"><h2>Available plans</h2></div><div class="table-wrap"><table><thead><tr><th>Plan</th><th class="right">Minutes</th><th class="right">Price</th></tr></thead><tbody>
        ${u.plans.map((p) => html`<tr><td>${p.label} ${p.key === u.plan.key ? html`<span class="pill brand">Current</span>` : ""}</td><td class="right num">${fmtNum(p.minutes)}</td><td class="right num">${inr(p.price_inr)}</td></tr>`)}</tbody></table></div>
        <div class="panel-body small muted">Prices are placeholders you can edit in backend/app/config.py. Plan changes are made by the Voxora team.</div></section>
    </div></div>`);
}
