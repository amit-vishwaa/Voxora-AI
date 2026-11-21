// Voice Studio: a live test call in the browser. The caller speaks (or types), the agent answers out loud.
import { api, getToken, postAudio } from "../api.js";
import { html, mount, $, toast, icon, options, empty, statusPill, scoreBar, LANGS } from "../ui.js";
import { openCallDrawer } from "./calls.js";

const CODES = { en: "en-IN", hi: "hi-IN", gu: "gu-IN" };
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const LABELS = { idle: "Ready when you are", connecting: "Connecting…", listening: "Listening. Speak now", thinking: "Thinking…", speaking: "Speaking…", ended: "Call saved" };
const KINDS = { llm: "AI agent", stt: "Speech to text", tts: "Text to speech", telephony: "Phone line" };

export async function render({ el, state }) {
  const cfg = state.config;
  const agents = (await api("/api/agents")).filter((a) => a.active);
  mount(el, html`<div class="page-head"><div><h1>Voice Studio</h1><p>Make a live test call. Speak to the agent, or type what the caller says.</p></div></div>`);
  if (!agents.length) { el.append(Object.assign(document.createElement("div"), { className: "panel", innerHTML: empty("No active agents", "Create or switch on an agent first.", html`<a class="btn primary" href="#/agents">Go to Agents</a>`).s })); return; }

  const wrap = document.createElement("div");
  wrap.className = "studio";
  const pre = +sessionStorage.getItem("voxora_studio_agent");
  mount(wrap, html`<section class="panel stage">
      <div class="row"><select id="agent" aria-label="Agent">${options(agents.map((a) => [a.id, `${a.name} · ${LANGS[a.language]}`]), pre)}</select>
        <button class="btn live" id="start">${icon("phone")} Start call</button><button class="btn danger" id="end" hidden>${icon("stop")} End call</button></div>
      <button class="orb" id="orb" data-state="idle" aria-label="Microphone: tap to finish speaking or to speak again">${icon("mic")}</button>
      <div><div class="state-label" id="state" style="text-align:center">${LABELS.idle}</div><div class="live-caption" id="cap" aria-live="polite"></div></div>
      <div class="chat" id="chat" aria-live="polite"></div>
      <form class="composer" id="composer"><input id="typed" type="text" placeholder="Or type what the caller says" autocomplete="off" disabled aria-label="Type a message"><button class="btn" id="send" type="submit" disabled aria-label="Send">${icon("send")}</button></form>
    </section>
    <aside class="stack">
      <section class="panel"><div class="panel-head"><h2>Captured details</h2></div><div class="panel-body" id="slots"><p class="muted small">Start a call and watch the details fill in live.</p></div></section>
      <section class="panel" id="result" hidden></section>
      <section class="panel"><div class="panel-head"><h2>How this call runs</h2></div><div class="panel-body small">${cfg.providers.map((p) => html`<p style="margin-bottom:8px"><b>${KINDS[p.kind]}:</b> <span class="muted">${p.note}</span></p>`)}</div></section>
    </aside>`);
  el.append(wrap);

  let ws = null, phase = "idle", rec = null, recorder = null, stream = null, audioEl = null, lang = "en", voice = "", silent = 0, warned = false, voiceWarned = false;
  const $$q = (s) => $(s, wrap);
  const orb = $$q("#orb");
  const setPhase = (p) => { phase = p; orb.dataset.state = p; $$q("#state").textContent = LABELS[p]; };
  const chat = $$q("#chat");
  const addMsg = (who, text) => { const d = document.createElement("div"); d.className = `msg ${who}`; d.textContent = text; chat.append(d); chat.scrollTop = chat.scrollHeight; };
  const setBusy = (on) => { $$q("#start").hidden = on; $$q("#end").hidden = !on; $$q("#agent").disabled = on; $$q("#typed").disabled = !on; $$q("#send").disabled = !on; };
  const renderSlots = (fields) => { $$q("#slots").innerHTML = fields.map((f) => `<div class="slot"><span>${f.label}${f.required ? "" : " (optional)"}</span><span class="val ${f.value ? "" : "empty-v"}">${f.value ? "" : f.skipped ? "Skipped" : "Waiting…"}</span></div>`).join("");
    [...$$q("#slots").querySelectorAll(".val")].forEach((v, i) => { if (fields[i].value) v.textContent = fields[i].value; }); };

  function stopSpeaking() {
    if (audioEl) { const a = audioEl; audioEl = null; a.pause(); a.dispatchEvent(new Event("ended")); }
    if ("speechSynthesis" in window) speechSynthesis.cancel();
  }
  async function speak(text) {
    stopSpeaking();
    if (!text) return;
    if (cfg.tts === "sarvam") {
      try {
        const r = await api("/api/voice/tts", { method: "POST", body: { text, language: lang, voice } });
        if (r.audio_b64) return await new Promise((resolve) => { audioEl = new Audio(`data:${r.mime};base64,${r.audio_b64}`); audioEl.addEventListener("ended", resolve); audioEl.addEventListener("error", resolve); audioEl.play().catch(resolve); });
      } catch (e) { toast(`${e.message} Using the browser voice instead.`, "error"); }
    }
    return new Promise((resolve) => {
      if (!("speechSynthesis" in window)) return resolve();
      const voices = speechSynthesis.getVoices(), code = CODES[lang].toLowerCase();
      const match = voices.find((v) => v.lang.replace("_", "-").toLowerCase() === code) || voices.find((v) => v.lang.toLowerCase().startsWith(lang));
      if (!match && lang !== "en" && voices.length && !voiceWarned) { voiceWarned = true; toast(`Your browser has no ${LANGS[lang]} voice installed. Install one in Windows Settings (Time and language, Speech) or switch on Sarvam text-to-speech.`, "error"); }
      const u = new SpeechSynthesisUtterance(text);
      u.lang = CODES[lang]; if (match) u.voice = match;
      u.onend = u.onerror = () => resolve();
      speechSynthesis.speak(u);
    });
  }

  function killMic() {
    if (rec) { rec.onend = null; try { rec.abort(); } catch { /* already stopped */ } rec = null; }
    if (recorder) { recorder.onstop = null; try { recorder.stop(); } catch { /* already stopped */ } recorder = null; }
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    $$q("#cap").textContent = "";
  }

  function submit(text) {
    if (!ws || ws.readyState !== 1 || !text.trim()) return;
    killMic(); stopSpeaking(); silent = 0;
    addMsg("caller", text);
    setPhase("thinking");
    ws.send(JSON.stringify({ type: "user_text", text }));
  }

  function listen() {
    if (!ws || ws.readyState !== 1 || ["idle", "connecting", "ended"].includes(phase)) return;
    setPhase("listening");
    if (cfg.stt === "sarvam") { $$q("#cap").textContent = "Tap the microphone to start recording."; return; }
    if (!SR) { $$q("#cap").textContent = "This browser cannot hear you. Use Chrome or Edge, or type below."; return; }
    let finalText = "", blocked = false;
    rec = new SR();
    rec.lang = CODES[lang]; rec.interimResults = true; rec.continuous = false;
    rec.onresult = (e) => { let interim = ""; for (let i = e.resultIndex; i < e.results.length; i++) { const r = e.results[i]; if (r.isFinal) finalText += r[0].transcript; else interim += r[0].transcript; } $$q("#cap").textContent = finalText + interim; };
    rec.onerror = (e) => { if (e.error === "not-allowed" || e.error === "service-not-allowed") { blocked = true; toast("Microphone is blocked. Allow it in the address bar, or type your message below.", "error"); } };
    rec.onend = () => {
      rec = null;
      if (phase !== "listening") return;
      if (finalText.trim()) return submit(finalText.trim());
      if (blocked) return;
      if (++silent < 3) return listen();
      $$q("#cap").textContent = "I didn't hear anything. Tap the microphone to try again, or type below.";
    };
    try { rec.start(); } catch { /* already running */ }
  }

  async function toggleRecord() {
    if (recorder) { recorder.stop(); return; }
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch { toast("Microphone is blocked. Allow it in the address bar.", "error"); return; }
    const chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      const type = recorder ? recorder.mimeType : "audio/webm";
      stream.getTracks().forEach((t) => t.stop()); recorder = null; stream = null;
      setPhase("thinking"); $$q("#cap").textContent = "Transcribing…";
      try { const text = await postAudio(new Blob(chunks, { type }), lang); $$q("#cap").textContent = ""; if (text) submit(text); else { toast("I couldn't hear that. Please try again.", "error"); listen(); } }
      catch (e) { toast(e.message, "error"); $$q("#cap").textContent = ""; listen(); }
    };
    recorder.start();
    $$q("#cap").textContent = "Recording. Tap the microphone again when you finish.";
    setTimeout(() => { if (recorder && recorder.state === "recording") recorder.stop(); }, 25000);
  }

  orb.addEventListener("click", () => {
    if (phase === "speaking") return stopSpeaking();            // interrupt the agent, then the loop goes back to listening
    if (phase !== "listening") return;
    if (cfg.stt === "sarvam") return toggleRecord();
    if (rec) rec.stop(); else { silent = 0; listen(); }
  });

  function showResult(call) {
    const box = $$q("#result");
    if (!call) { toast("The call ended before anyone spoke, so nothing was saved."); return; }
    box.hidden = false;
    mount(box, html`<div class="panel-head"><h2>Call saved</h2>${statusPill(call.status)}</div><div class="panel-body"><p>${call.summary}</p><div class="row" style="margin:12px 0">Score ${scoreBar(call.score)}</div><button class="btn primary" id="open">Open full call</button></div>`);
    $("#open", box).addEventListener("click", () => openCallDrawer(call.call_id));
  }

  function start() {
    const id = +$$q("#agent").value;
    sessionStorage.setItem("voxora_studio_agent", id);
    chat.innerHTML = ""; $$q("#result").hidden = true; $$q("#slots").innerHTML = ""; warned = false; silent = 0;
    setBusy(true); setPhase("connecting");
    if ("speechSynthesis" in window) speechSynthesis.getVoices();   // wakes up the voice list
    ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/voice/ws?token=${encodeURIComponent(getToken())}&agent_id=${id}`);
    ws.onmessage = async (ev) => {
      const m = JSON.parse(ev.data);
      if (m.type === "ready") { lang = m.language; voice = m.voice; renderSlots(m.fields); addMsg("agent", m.reply); setPhase("speaking"); await speak(m.reply); if (phase === "speaking") listen(); }
      else if (m.type === "agent") {
        addMsg("agent", m.reply); renderSlots(m.fields);
        if (m.degraded && !warned) { warned = true; toast(`${m.note} The built-in agent is answering instead.`, "error"); }
        setPhase("speaking"); await speak(m.reply);
        if (phase === "speaking" && !m.ended) listen();
      } else if (m.type === "ended") { killMic(); setPhase("ended"); setBusy(false); showResult(m.call); }
      else if (m.type === "notice") toast(m.text);
      else if (m.type === "error") { toast(m.text, "error"); setBusy(false); setPhase("idle"); }
    };
    ws.onclose = () => { if (phase !== "ended" && phase !== "idle") { killMic(); stopSpeaking(); setBusy(false); setPhase("idle"); } };
    ws.onerror = () => toast("Could not open the call connection. Is the server still running?", "error");
  }

  $$q("#start").addEventListener("click", start);
  $$q("#end").addEventListener("click", () => { killMic(); stopSpeaking(); if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: "end" })); });
  $$q("#composer").addEventListener("submit", (e) => { e.preventDefault(); const t = $$q("#typed"); const v = t.value.trim(); t.value = ""; if (v) submit(v); });

  return () => { killMic(); stopSpeaking(); if (ws) { ws.onclose = null; try { ws.close(); } catch { /* closed */ } } };
}
