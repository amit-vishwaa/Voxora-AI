import { api } from "../api.js";
import { html, mount, $, $$, skeleton, empty, modal, toast, confirmBox, bindForm, options, fmtDay, icon } from "../ui.js";

export async function render({ el, state }) {
  const canEdit = state.user.role !== "client_user";
  mount(el, html`<div class="page-head"><div><h1>Knowledge base</h1><p>Facts your agents can use to answer callers: prices, timings, locations, policies.</p></div>
    ${canEdit ? html`<button class="btn primary" id="add">${icon("plus")} Add entry</button>` : ""}</div><div id="list">${skeleton(4)}</div>`);
  const list = $("#list", el);
  async function load() {
    let items;
    try { items = await api("/api/knowledge"); } catch (e) { return mount(list, html`<div class="panel">${empty("Could not load", e.message)}</div>`); }
    if (!items.length) return mount(list, html`<div class="panel">${empty("Nothing here yet", "Add a few facts and callers get accurate answers instead of 'I will check and call you back'.")}</div>`);
    mount(list, html`<div class="stack">${items.map((k) => html`<article class="panel"><div class="panel-head"><div><h3>${k.title}</h3><span class="muted small">${k.agent_name ? `Only for ${k.agent_name}` : "All agents"} · added ${fmtDay(k.created_at)}</span></div>
      ${canEdit ? html`<button class="btn danger small" data-del="${k.id}">Delete</button>` : ""}</div><div class="panel-body"><p style="white-space:pre-wrap">${k.content}</p></div></article>`)}</div>`);
    $$("[data-del]", list).forEach((b) => b.addEventListener("click", async () => {
      if (!(await confirmBox("Delete this entry? Agents will stop using it."))) return;
      try { await api(`/api/knowledge/${b.dataset.del}`, { method: "DELETE" }); toast("Entry deleted", "ok"); load(); } catch (e) { toast(e.message, "error"); }
    }));
  }
  const add = $("#add", el);
  if (add) add.addEventListener("click", async () => {
    const agents = await api("/api/agents");
    const m = modal("Add knowledge", html`<form id="kf"><div class="field"><label for="t">Title</label><input id="t" name="title" type="text" required maxlength="120" placeholder="e.g. Weekend site visits"></div>
      <div class="field"><label for="c">What should the agent know?</label><textarea id="c" name="content" required maxlength="4000" placeholder="Write it the way you would tell a new receptionist."></textarea><span class="hint">Keep each entry about one topic. Short and factual works best.</span></div>
      <div class="field"><label for="a">Who can use it?</label><select id="a" name="agent_id"><option value="">All agents</option>${options(agents.map((a) => [a.id, a.name]))}</select></div>
      <div class="err" role="alert"></div><div class="row" style="justify-content:flex-end"><button type="button" class="btn" data-close>Cancel</button><button class="btn primary" type="submit">Save entry</button></div></form>`);
    bindForm($("#kf", m.el), async (v) => {
      await api("/api/knowledge", { method: "POST", body: { title: v.title, content: v.content, agent_id: v.agent_id ? +v.agent_id : null } });
      m.close(); toast("Entry added", "ok"); load();
    });
  });
  await load();
}
