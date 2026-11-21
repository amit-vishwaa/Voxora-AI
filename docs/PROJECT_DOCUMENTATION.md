# Project Documentation

## 1. Purpose

Voxora Voice lets a company deploy AI voice agents that talk to callers, collect details (a lead, an appointment, a support ticket), answer questions from a knowledge base, and report everything on a dashboard. One engine serves every industry; an industry is a **pack** (a JSON file), not new code.

## 2. Architecture

```
Browser (Admin dashboard | Client dashboard | Voice Studio)
        |  HTTPS/JSON and one WebSocket
FastAPI backend ─ Auth and roles ─ Tenant guard (company_id)
        ├─ Voice session  (STT -> agent -> TTS loop, state in memory, saved at hang-up)
        ├─ Agent engine   (prompt builder, safety rules, normaliser)
        ├─ Industry packs (JSON)
        ├─ Analytics      (read-only numbers)
        └─ Provider adapters  LLM: mock | Gemini     STT: browser | Sarvam | mock
                              TTS: browser | Sarvam | mock     Telephony: browser (later Exotel / Twilio)
SQLite (every business table has company_id)
```

Design rules:

1. **Tenant isolation is a server rule.** `deps.tenant()` returns the company a request may touch. Clients always get their own `company_id`; passing another one returns 403. Only the Super Admin may choose a company. Queries in `routers/client.py` always include `AND company_id = ?`.
2. **Every AI service is behind an adapter** (`providers/base.py`). Swapping or adding one never touches the rest of the app. A failing provider falls back to the mock agent for that turn, so a call never dies because a free tier ran out.
3. **Safety does not depend on the model.** Emergency words and "speak to a manager" are matched in code (`agent_engine.check_escalation`) before the LLM is asked.
4. **Costs nothing by default.** Defaults are mock agent plus browser speech.

## 3. Folder map

```
backend/app/
  main.py          App creation, middleware, serves the frontend
  config.py        Settings (.env), languages, voices, placeholder plans
  db.py            SQLite schema and helpers (plain SQL)
  security.py      scrypt password hashing, HS256 tokens (standard library only)
  deps.py          current_user, require_admin, require_writer, tenant
  schemas.py       Request validation (Pydantic)
  seed.py          First-run Super Admin and demo companies with simulated calls
  routers/         auth, meta, admin, client (company data), voice (WebSocket, STT, TTS)
  services/        session (live call), agent_engine, scoring, analytics
  providers/       base, mock, gemini, sarvam, registry
  packs/           real_estate, healthcare, education, sales, support (.json)
backend/tests/     Unit tests (standard library only)
backend/scripts/   smoke_test.py (checks a running server)
frontend/          index.html, css/app.css, js/ (main, api, ui, charts, views/*)
```

## 4. Roles

| Role | Company | Can do |
|---|---|---|
| `super_admin` | none | Everything. Manage companies, plans and logins. "Open" any company to see its client view. |
| `client_admin` | one | Manage own agents, knowledge, record statuses. View calls and usage. |
| `client_user` | one | View only. |

Suspended companies and disabled users are blocked on the next request, because the user is reloaded from the database every time.

## 5. Data model

`companies` (name, industry, plan, status) · `users` (company_id nullable only for super admin, role, active, must_change) · `agents` (company_id, pack_key, language, voice, greeting, instructions, active) · `knowledge` (company_id, optional agent_id) · `calls` (company_id, agent snapshot name, started_at, duration, status, sentiment, summary, score, collected_json) · `turns` (transcript lines) · `records` (leads, appointments, tickets, enquiries; data_json, score, status).

Call `status`: completed, partial, transferred, abandoned. Record `status`: new, contacted, won, closed.

## 6. How a call works

1. The browser opens `WS /api/voice/ws?token=...&agent_id=...`. The server checks the token, that the agent belongs to the user's company, that the company is active and has minutes left.
2. The server sends `ready` with the greeting and the list of fields to capture. The browser speaks it.
3. The caller speaks. The browser (Web Speech API) or Sarvam (`POST /api/voice/stt`) turns audio into text, which is sent as `{"type":"user_text","text":"..."}`.
4. `VoiceSession.turn()` checks escalation rules, builds the prompt, asks the LLM provider, normalises the answer (unknown fields dropped, actions validated), updates captured fields and replies with `agent`.
5. When all fields are captured (or the caller leaves, or a hand-off happens) the session is saved: a `calls` row, `turns`, and a `records` row when something useful was captured. The server sends `ended`.
6. Closing the browser tab also saves the call.

Messages from server: `ready`, `agent`, `ended`, `notice`, `error`. From browser: `user_text`, `end`.

## 7. Industry packs

A pack is `backend/app/packs/<key>.json`. Drop in a new file and it appears in the app and in the admin "industry" list.

```json
{
  "key": "real_estate", "label": "Real estate and builders", "record_type": "lead",
  "persona": "You are a courteous property consultant ...",
  "greeting": {"en": "Hello, this is {agent} from {company}. ...", "hi": "...", "gu": "..."},
  "fields": [
    {"name": "budget", "label": "Budget", "type": "text", "required": true,
     "ask": {"en": "What is your approximate budget?", "hi": "...", "gu": "..."}}
  ],
  "title_fields": ["name", "interest"],
  "closing": {"en": "Thank you, {name}. ...", "hi": "...", "gu": "..."},
  "scoring": {"fields": {"budget": 25, "timeline": 25}, "complete": 15},
  "escalate": {"en": ["emergency"], "hi": [], "gu": []},
  "handoff": {"en": "...", "hi": "...", "gu": "..."},
  "rules": ["Never quote a final price."]
}
```

`type` may be `text` or `phone` (phone needs ten digits). `tests/test_core.py` checks that every pack has all three languages. Run the tests after editing a pack.

## 8. API summary (interactive docs at /docs)

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/change-password` |
| Meta | `GET /api/health`, `GET /api/meta/packs`, `GET /api/meta/config` |
| Admin (Super Admin only) | `GET /api/admin/overview`, `GET/POST /api/admin/companies`, `PATCH /api/admin/companies/{id}`, `GET/POST /api/admin/companies/{id}/users`, `PATCH /api/admin/users/{id}` |
| Company data (client, or admin with `?company_id=`) | `GET /api/company`, `GET /api/dashboard?days=`, `GET/POST /api/agents`, `PATCH/DELETE /api/agents/{id}`, `GET /api/calls` (filters `agent_id`, `status`, `sentiment`, `q`, paging), `GET /api/calls/{id}`, `GET /api/records`, `PATCH /api/records/{id}`, `GET/POST /api/knowledge`, `DELETE /api/knowledge/{id}`, `GET /api/usage` |
| Voice | `WS /api/voice/ws`, `POST /api/voice/stt`, `POST /api/voice/tts` |

## 9. Adding a provider (for example another LLM or a phone provider)

1. Create `backend/app/providers/yourservice.py` with a class that extends `LLMProvider`, `STTProvider` or `TTSProvider` and implements one method. Raise `ProviderError("friendly message")` on failure.
2. Register it in `providers/registry.py` (`get_llm`, `get_stt`, `get_tts`) and add its settings in `config.py` and `.env.example`.
3. Add a line to `registry.status()` so the Voice Studio panel can describe it.

Telephony is not built yet. The intended shape: a webhook endpoint per provider that opens the same `VoiceSession`, with STT and TTS running server-side (`STT_PROVIDER` and `TTS_PROVIDER` set to a server provider).

## 10. Configuration reference (`backend/.env`)

| Setting | Default | Meaning |
|---|---|---|
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | admin@voxora.local, ChangeMe@123 | Used once to create the Super Admin |
| `SEED_DEMO` | true | Create demo companies and sample calls on an empty database |
| `SECRET_KEY` | auto | Signs login tokens. Auto-created in `backend/data/.secret_key` when empty |
| `LLM_PROVIDER` | mock | `mock` or `gemini` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | empty, gemini-2.5-flash | Gemini free tier |
| `STT_PROVIDER` | browser | `browser`, `sarvam`, `mock` |
| `TTS_PROVIDER` | browser | `browser`, `sarvam`, `mock` |
| `SARVAM_API_KEY`, `SARVAM_STT_MODEL`, `SARVAM_TTS_MODEL` | empty, saaras:v3, bulbul:v3 | Sarvam AI |
| `MAX_LIVE_SESSIONS` | 5 | Parallel live calls allowed (protects a small laptop) |
| `IDLE_TIMEOUT_SEC` | 120 | A silent call ends after this long |
| `TOKEN_HOURS` | 12 | Login lifetime |
| `DB_PATH` | backend/data/voxora.db | Database file |
| `CORS_ORIGINS` | empty | Only needed if the frontend is served from another address |

Plans (minutes and prices) are placeholders in `config.py` (`PLANS`).

## 11. Security notes

Passwords use scrypt with a random salt. Tokens are signed HS256 and expire. Login attempts are rate-limited per email and address (in memory). All SQL is parameterised. The frontend escapes every dynamic value before it writes HTML. The server adds basic security headers. Before exposing the app beyond your laptop: serve it over HTTPS, set a strong `ADMIN_PASSWORD` and `SECRET_KEY`, set `SEED_DEMO=false`, and review docs/MANUAL_SETUP_AND_NEXT_STEPS.md.
