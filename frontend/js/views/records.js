import { api } from "../api.js";
import { html, mount, $, $$, skeleton, empty, modal, toast, fmtDate, scoreBar, recordName } from "../ui.js";

const pretty = (k) => k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const STATUSES = ["new", "contacted", "won", "closed"];

export async function render({ el, state, company }) {
  const canEdit = state.user.role !== "client_user";
  let status = "";
  mount(el, html`<div class="page-head"><div><h1>${recordName(company.industry)}</h1><p>Captured by your agents. Update the status as your team follows up.</p></div>
    <div class="tabs" id="tabs"></div></div><div class="panel" id="list">${skeleton(5)}</div>`);
  const list = $("#list", el);
  async function load() {
    $("#tabs", el).innerHTML = ["", ...STATUSES].map((s) => `<button data-s="${s}" aria-pressed="${s === status}">${s ? pretty(s) : "All"}</button>`).join("");
    let r;
    try { r = await api("/api/records", { query: { status, limit: 100 } }); } catch (e) { return mount(list, empty("Could not load records", e.message)); }
    if (!r.items.length) return mount(list, empty(`No ${recordName(company.industry).toLowerCase()} here yet`, "They appear automatically when an agent finishes a call.", html`<a class="btn primary" href="#/studio">Make a test call</a>`));
    mount(list, html`<div class="table-wrap"><table><thead><tr><th>Record</th><th>Details</th><th>Score</th><th>Status</th><th>Captured</th></tr></thead><tbody>
      ${r.items.map((x) => html`<tr class="click" data-id="${x.id}" tabindex="0"><td><b>${x.title}</b><div class="muted small">${pretty(x.type)}</div></td>
        <td class="small muted" style="max-width:300px">${Object.entries(x.data).filter(([k]) => k !== "name").slice(0, 3).map(([k, v]) => html`<div>${pretty(k)}: ${v}</div>`)}</td>
        <td>${scoreBar(x.score)} <span class="pill ${x.label === "hot" ? "warn" : ""}">${x.label}</span></td>
        <td>${canEdit ? html`<select data-s="${x.id}" aria-label="Status">${STATUSES.map((s) => html`<option value="${s}" ${s === x.status ? { __raw: true, s: "selected" } : ""}>${pretty(s)}</option>`)}</select>` : html`<span class="pill">${pretty(x.status)}</span>`}</td>
        <td class="num small">${fmtDate(x.created_at)}</td></tr>`)}</tbody></table></div>`);
    $$("select[data-s]", list).forEach((s) => {
      s.addEventListener("click", (e) => e.stopPropagation());
      s.addEventListener("change", async () => { try { await api(`/api/records/${s.dataset.s}`, { method: "PATCH", body: { status: s.value } }); toast("Status updated", "ok"); } catch (e) { toast(e.message, "error"); load(); } });
    });
    $$("tr.click", list).forEach((tr) => tr.addEventListener("click", (e) => {
      if (e.target.closest("select")) return;
      const x = r.items.find((i) => i.id === +tr.dataset.id);
      modal(x.title, html`<dl class="kv">${Object.entries(x.data).map(([k, v]) => html`<dt>${pretty(k)}</dt><dd>${v}</dd>`)}</dl><p class="muted small" style="margin-top:14px">Captured ${fmtDate(x.created_at)}. Score ${x.score}/100.</p>`);
    }));
  }
  $("#tabs", el).addEventListener("click", (e) => { const b = e.target.closest("button[data-s]"); if (b) { status = b.dataset.s; load(); } });
  await load();
}
