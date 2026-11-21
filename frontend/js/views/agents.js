import { api } from "../api.js";
import { html, mount, $, $$, skeleton, empty, modal, toast, confirmBox, bindForm, options, icon, LANGS } from "../ui.js";

export async function render({ el, state, company }) {
  const canEdit = state.user.role !== "client_user";
  const voices = state.config.voices;
  const packs = await api("/api/meta/packs");
  const packLabel = (k) => (packs.find((p) => p.key === k) || { label: k }).label;
  mount(el, html`<div class="page-head"><div><h1>Agents</h1><p>Each agent has an industry, a language and a voice. Test it live in Voice Studio.</p></div>
    ${canEdit ? html`<button class="btn primary" id="add">${icon("plus")} New agent</button>` : ""}</div><div id="grid">${skeleton(3)}</div>`);
  const grid = $("#grid", el);
  let agents = [];

  function form(agent) {
    const a = agent || { name: "", pack_key: company.industry, language: "en", voice: voices[0], greeting: "", instructions: "", active: 1 };
    const m = modal(agent ? "Edit agent" : "New agent", html`<form id="af">
      <div class="grid2"><div class="field"><label for="n">Agent name</label><input id="n" name="name" type="text" required minlength="2" maxlength="40" value="${a.name}"></div>
      <div class="field"><label for="p">Industry</label><select id="p" name="pack_key">${options(packs.map((p) => [p.key, p.label]), a.pack_key)}</select></div></div>
      <div class="grid2"><div class="field"><label for="l">Language</label><select id="l" name="language">${options(Object.entries(LANGS), a.language)}</select></div>
      <div class="field"><label for="v">Voice (used with Sarvam)</label><select id="v" name="voice">${options(voices.map((v) => [v, v]), a.voice)}</select></div></div>
      <div class="field"><label for="g">Greeting (optional)</label><textarea id="g" name="greeting" maxlength="400" style="min-height:70px" placeholder="Leave blank to use the industry greeting. You can use {agent} and {company}.">${a.greeting}</textarea></div>
      <div class="field"><label for="i">Extra instructions (optional)</label><textarea id="i" name="instructions" maxlength="1500" style="min-height:70px" placeholder="e.g. Always mention our free site-visit pickup.">${a.instructions}</textarea><span class="hint">Used by Gemini. The built-in mock agent ignores them.</span></div>
      <label class="switch" style="margin-bottom:14px"><input type="checkbox" name="active" ${a.active ? { __raw: true, s: "checked" } : ""}> Agent is active</label>
      <div class="err" role="alert"></div><div class="row" style="justify-content:flex-end"><button type="button" class="btn" data-close>Cancel</button><button class="btn primary" type="submit">${agent ? "Save changes" : "Create agent"}</button></div></form>`);
    bindForm($("#af", m.el), async (v) => {
      const body = { name: v.name.trim(), pack_key: v.pack_key, language: v.language, voice: v.voice, greeting: v.greeting, instructions: v.instructions, active: v.active === "on" };
      await api(agent ? `/api/agents/${agent.id}` : "/api/agents", { method: agent ? "PATCH" : "POST", body });
      m.close(); toast(agent ? "Agent updated" : "Agent created", "ok"); load();
    });
  }

  async function load() {
    try { agents = await api("/api/agents"); } catch (e) { return mount(grid, html`<div class="panel">${empty("Could not load agents", e.message)}</div>`); }
    if (!agents.length) return mount(grid, html`<div class="panel">${empty("No agents yet", "Create your first agent and test it in a live call.")}</div>`);
    mount(grid, html`<div class="agent-grid">${agents.map((a) => html`<article class="panel agent">
      <div class="top"><div class="row"><div class="avatar" aria-hidden="true">${a.name.slice(0, 1).toUpperCase()}</div><div><h3>${a.name}</h3><span class="muted small">${packLabel(a.pack_key)}</span></div></div>
        <span class="pill ${a.active ? "good" : ""}">${a.active ? "Active" : "Off"}</span></div>
      <div class="chips"><span class="pill brand">${LANGS[a.language]}</span><span class="pill">Voice: ${a.voice}</span><span class="pill">${a.calls} calls</span></div>
      <div class="row"><button class="btn small primary" data-test="${a.id}" ${a.active ? "" : { __raw: true, s: "disabled" }}>${icon("mic")} Test call</button>
        ${canEdit ? html`<button class="btn small" data-edit="${a.id}">Edit</button><button class="btn small danger" data-del="${a.id}">Delete</button>` : ""}</div></article>`)}</div>`);
    $$("[data-test]", grid).forEach((b) => b.addEventListener("click", () => { sessionStorage.setItem("voxora_studio_agent", b.dataset.test); location.hash = "#/studio"; }));
    $$("[data-edit]", grid).forEach((b) => b.addEventListener("click", () => form(agents.find((a) => a.id === +b.dataset.edit))));
    $$("[data-del]", grid).forEach((b) => b.addEventListener("click", async () => {
      const a = agents.find((x) => x.id === +b.dataset.del);
      if (!(await confirmBox(`Delete ${a.name}? Past calls stay in your history.`))) return;
      try { await api(`/api/agents/${a.id}`, { method: "DELETE" }); toast("Agent deleted", "ok"); load(); } catch (e) { toast(e.message, "error"); }
    }));
  }
  const add = $("#add", el);
  if (add) add.addEventListener("click", () => form(null));
  await load();
}
