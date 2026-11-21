import { api } from "../api.js";
import { html, raw, mount, $, $$, skeleton, empty, drawer, debounce, options, fmtDur, fmtDate, statusPill, sentimentPill, scoreBar, LANGS } from "../ui.js";

const pretty = (k) => k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export async function openCallDrawer(id) {
  const d = drawer("Call details", html`<div id="dbody">${skeleton(6)}</div>`);
  const slot = $("#dbody", d.el);
  try {
    const c = await api(`/api/calls/${id}`);
    mount(slot, html`<div class="panel-body">
        <div class="row" style="margin-bottom:14px">${statusPill(c.status)}${sentimentPill(c.sentiment)}<span class="pill">${LANGS[c.language]}</span>${c.record ? html`<span class="pill brand">${c.record.type}: ${c.record.status}</span>` : ""}</div>
        <dl class="kv"><dt>Agent</dt><dd>${c.agent_name}</dd><dt>Started</dt><dd>${fmtDate(c.started_at)}</dd><dt>Duration</dt><dd>${fmtDur(c.duration_sec)}</dd><dt>Score</dt><dd>${scoreBar(c.score)}</dd><dt>Channel</dt><dd>${c.channel} (audio is not stored in browser mode)</dd></dl>
        <h3 style="margin:20px 0 6px">Summary</h3><p>${c.summary}</p>
        <h3 style="margin:20px 0 6px">Captured details</h3>
        ${Object.keys(c.collected).length ? html`<dl class="kv">${Object.entries(c.collected).map(([k, v]) => html`<dt>${pretty(k)}</dt><dd>${v}</dd>`)}</dl>` : html`<p class="muted">Nothing captured.</p>`}
      </div>
      <div class="panel-head" style="border-top:1px solid var(--line)"><h3>Transcript</h3><span class="muted small">${c.turns.length} messages</span></div>
      <div class="chat">${c.turns.map((t) => html`<div class="msg ${t.speaker}">${t.text}<small>${t.speaker === "caller" ? "Caller" : c.agent_name} · ${new Date(t.at).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })}</small></div>`)}</div>`);
  } catch (e) { mount(slot, html`<div class="panel-body">${empty("Could not load this call", e.message)}</div>`); }
}

export async function render({ el }) {
  const f = { q: "", agent_id: "", status: "", sentiment: "" };
  let offset = 0, items = [], total = 0;
  const agents = await api("/api/agents");
  mount(el, html`<div class="page-head"><div><h1>Calls</h1><p>Every conversation, with transcript, summary and captured details.</p></div></div>
    <div class="panel"><div class="panel-head">
      <div class="row" style="flex:1"><div style="position:relative;flex:1;min-width:200px"><input id="q" type="text" placeholder="Search summaries and details" aria-label="Search calls"></div>
      <select id="agent" aria-label="Agent"><option value="">All agents</option>${options(agents.map((a) => [a.id, a.name]))}</select>
      <select id="status" aria-label="Outcome"><option value="">Any outcome</option>${options([["completed", "Completed"], ["partial", "Partial"], ["transferred", "Transferred"], ["abandoned", "Dropped"]])}</select>
      <select id="sent" aria-label="Sentiment"><option value="">Any sentiment</option>${options([["positive", "Positive"], ["neutral", "Neutral"], ["negative", "Negative"]])}</select></div></div>
      <div id="list">${skeleton(5)}</div></div>`);
  const list = $("#list", el);
  async function load(reset) {
    if (reset) { offset = 0; items = []; }
    try {
      const r = await api("/api/calls", { query: { ...f, limit: 25, offset } });
      items = items.concat(r.items); total = r.total; offset = items.length;
    } catch (e) { return mount(list, empty("Could not load calls", e.message)); }
    if (!items.length) return mount(list, empty("No calls match", "Try clearing the filters, or make a test call in Voice Studio.", html`<a class="btn primary" href="#/studio">Open Voice Studio</a>`));
    mount(list, html`<div class="table-wrap"><table><thead><tr><th>When</th><th>Agent</th><th>Summary</th><th>Outcome</th><th>Sentiment</th><th>Score</th><th class="right">Duration</th></tr></thead><tbody>
      ${items.map((c) => html`<tr class="click" data-id="${c.id}" tabindex="0"><td class="num" style="white-space:nowrap">${fmtDate(c.started_at)}</td><td>${c.agent_name}<div class="muted small">${LANGS[c.language]}</div></td>
        <td style="max-width:340px"><div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:340px">${c.summary}</div></td><td>${statusPill(c.status)}</td><td>${sentimentPill(c.sentiment)}</td><td>${scoreBar(c.score)}</td><td class="right num">${fmtDur(c.duration_sec)}</td></tr>`)}
      </tbody></table></div>
      <div class="panel-head" style="border-top:1px solid var(--line);border-bottom:0"><span class="muted small">Showing ${items.length} of ${total}</span>${items.length < total ? html`<button class="btn small" id="more">Load more</button>` : ""}</div>`);
    $$("tr.click", list).forEach((tr) => { const open = () => openCallDrawer(+tr.dataset.id); tr.addEventListener("click", open); tr.addEventListener("keydown", (e) => { if (e.key === "Enter") open(); }); });
    const more = $("#more", list); if (more) more.addEventListener("click", () => load(false));
  }
  $("#q", el).addEventListener("input", debounce((e) => { f.q = e.target.value.trim(); load(true); }));
  $("#agent", el).addEventListener("change", (e) => { f.agent_id = e.target.value; load(true); });
  $("#status", el).addEventListener("change", (e) => { f.status = e.target.value; load(true); });
  $("#sent", el).addEventListener("change", (e) => { f.sentiment = e.target.value; load(true); });
  await load(true);
}
