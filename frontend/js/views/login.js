import { api } from "../api.js";
import { html, mount, $, $$, logo, bindForm } from "../ui.js";

const DEMOS = [
  ["Super Admin", "admin@voxora.local", "ChangeMe@123"],
  ["Skyline Realty (client)", "demo.realty@voxora.local", "Demo@12345"],
  ["CityCare Hospital (client)", "demo.hospital@voxora.local", "Demo@12345"],
  ["BrightPath Academy (client)", "demo.academy@voxora.local", "Demo@12345"],
];

export function render(root, onSuccess) {
  const bars = Array.from({ length: 44 }, (_, i) => `<i style="--h:${30 + Math.round(60 * Math.abs(Math.sin(i * 0.55) * Math.cos(i * 0.21)))}%;--i:${i}"></i>`).join("");
  mount(root, html`<div class="login">
    <section class="hero">
      <div class="brand">${logo(38)}<div>Voxora Voice</div></div>
      <div><h1>Intelligent Conversations. Limitless Possibilities.</h1>
        <p>AI voice agents for real estate, healthcare, education, sales and support. In Hindi, English and Gujarati.</p></div>
      <div class="wave" aria-hidden="true">${{ __raw: true, s: bars }}</div>
    </section>
    <section class="login-form"><form id="f" novalidate>
      <h2>Sign in</h2><p class="muted" style="margin-bottom:22px">Use the login your Voxora admin gave you.</p>
      <div class="field"><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="username" required></div>
      <div class="field"><label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required></div>
      <div class="err" role="alert"></div>
      <button class="btn primary" type="submit" style="width:100%">Sign in</button>
      <div class="demo-box"><b>Demo logins</b> <span class="muted">(exist when SEED_DEMO=true)</span>
        ${DEMOS.map(([label], i) => html`<button type="button" data-i="${i}">${label}</button>`)}</div>
    </form></section></div>`);
  const form = $("#f", root);
  $$("[data-i]", root).forEach((b) => b.addEventListener("click", () => {
    const [, email, pw] = DEMOS[+b.dataset.i];
    $("#email", root).value = email; $("#password", root).value = pw; $("#email", root).focus();
  }));
  bindForm(form, async (v) => onSuccess(await api("/api/auth/login", { method: "POST", body: { email: v.email.trim(), password: v.password } })));
}
