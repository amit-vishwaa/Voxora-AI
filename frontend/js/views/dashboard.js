import { api } from "../api.js";
import { html, mount, $, skeleton, empty, fmtDur, fmtNum, fmtDate, statusPill, sentimentPill, recordName, LANGS } from "../ui.js";
import { barChart, shareBars } from "../charts.js";
import { openCallDrawer } from "./calls.js";

const OUT = { completed: "Completed", partial: "Partial", transferred: "Transferred", abandoned: "Dropped" };
const OUT_C = { completed: "var(--good)", partial: "var(--saffron)", transferred: "var(--brand)", abandoned: "var(--neutral)" };
const SENT_C = { positive: "var(--good)", neutral: "var(--neutral)", negative: "var(--bad)" };
const PIPE_C = { new: "var(--brand)", contacted: "var(--saffron)", won: "var(--good)", closed: "var(--neutral)" };

export async function render({ el, company }) {
  let days = 14;
  mount(el, html`<div class="page-head"><div><h1>Dashboard</h1><p>${company.name}: how your voice agents are performing.</p></div>
    <div class="tabs" id="range"></div></div><div id="body"></div>`);
  const body = $("#body", el);
  const paint = async () => {
    $("#range", el).innerHTML = [7, 14, 30].map((d) => `<button data-d="${d}" aria-pressed="${d === days}">${d} days</button>`).join("");
    mount(body, skeleton(6));
    let d;
    try { d = await api("/api/dashboard", { query: { days } }); } catch (e) { return mount(body, html`<div class="panel">${empty("Could not load the dashboard", e.message)}</div>`); }
    const k = d.kpis, delta = k.calls_prev ? Math.round((100 * (k.calls - k.calls_prev)) / k.calls_prev) : null;
    if (!k.calls && !d.recent.length) return mount(body, html`<div class="panel">${empty("No calls yet", "Make a test call in Voice Studio and it will show up here.", html`<a class="btn primary" href="#/studio">Open Voice Studio</a>`)}</div>`);
    mount(body, html`
      <div class="band">
        <div><div class="v num">${fmtNum(k.calls)}${delta === null ? "" : html`<span class="delta ${delta >= 0 ? "up" : "down"}">${delta >= 0 ? "▲" : "▼"} ${Math.abs(delta)}%</span>`}</div><div class="l">Calls, last ${days} days</div></div>
        <div><div class="v num">${fmtNum(Math.round(k.minutes))}</div><div class="l">Talk minutes, avg ${fmtDur(k.avg_duration_sec)} per call</div></div>
        <div><div class="v num">${k.completion_rate}%</div><div class="l">Calls completed, ${k.positive_rate}% positive</div></div>
        <div><div class="v num">${fmtNum(k.records)}</div><div class="l">${recordName(company.industry)} captured, avg score ${k.avg_score}</div></div>
      </div>
      <div class="cols">
        <div class="stack">
          <section class="panel"><div class="panel-head"><h2>Calls per day</h2><span class="muted small">Today in saffron</span></div><div class="panel-body">${barChart(d.daily)}</div></section>
          <section class="panel"><div class="panel-head"><h2>Recent calls</h2><a href="#/calls" class="small">View all</a></div>
            <div class="table-wrap"><table><thead><tr><th>When</th><th>Agent</th><th>Outcome</th><th>Sentiment</th><th class="right">Duration</th></tr></thead><tbody>
            ${d.recent.map((c) => html`<tr class="click" data-id="${c.id}" tabindex="0"><td>${fmtDate(c.started_at)}</td><td>${c.agent_name}<div class="muted small">${LANGS[c.language]}</div></td><td>${statusPill(c.status)}</td><td>${sentimentPill(c.sentiment)}</td><td class="right num">${fmtDur(c.duration_sec)}</td></tr>`)}
            </tbody></table></div></section>
        </div>
        <div class="stack">
          <section class="panel"><div class="panel-head"><h2>Outcomes</h2></div><div class="panel-body">${shareBars(d.outcomes, OUT, OUT_C)}</div></section>
          <section class="panel"><div class="panel-head"><h2>Caller sentiment</h2></div><div class="panel-body">${shareBars(d.sentiment, {}, SENT_C)}</div></section>
          <section class="panel"><div class="panel-head"><h2>${recordName(company.industry)} pipeline</h2></div><div class="panel-body">${shareBars(d.pipeline, {}, PIPE_C)}</div></section>
          <section class="panel"><div class="panel-head"><h2>Busiest agents</h2></div><div class="panel-body">${shareBars(d.agents)}</div></section>
        </div>
      </div>`);
    body.querySelectorAll("tr.click").forEach((tr) => {
      const open = () => openCallDrawer(+tr.dataset.id);
      tr.addEventListener("click", open); tr.addEventListener("keydown", (e) => { if (e.key === "Enter") open(); });
    });
  };
  $("#range", el).addEventListener("click", (e) => { const b = e.target.closest("button[data-d]"); if (b) { days = +b.dataset.d; paint(); } });
  await paint();
}
