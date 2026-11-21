# Continue With an AI Coding Tool

Use this file to continue the project in Google Antigravity, OpenAI Codex, Claude Code, Cursor or any similar tool. Open the project folder in the tool, then paste the **Briefing** below as your first message.

## Briefing (copy everything in this box)

```
You are helping me continue "Voxora Voice", a multi-tenant AI voice agent SaaS.
Tagline: Intelligent Conversations. Limitless Possibilities.

Read first: README.md, docs/PROJECT_DOCUMENTATION.md, docs/DEVELOPMENT_STATUS.md.

Product
- Two logins: Super Admin (internal team, sees all companies) and Client (restricted to its own company: agents, calls, recordings, transcripts, summaries, analytics, billing).
- Languages: Hindi, English, Gujarati. Industries as JSON "packs": real estate, healthcare, education, sales, support.

Stack
- Backend: Python, FastAPI, SQLite via plain sqlite3 (backend/app/db.py), standard-library password hashing and JWT (backend/app/security.py).
- Frontend: plain HTML, CSS and ES-module JavaScript in frontend/ (no build step). All dynamic text goes through the html`` template tag, which escapes values.
- Providers behind adapters in backend/app/providers: LLM (mock, Gemini), STT (browser, Sarvam, mock), TTS (browser, Sarvam, mock). Telephony is not built.

Hard rules
1. Budget for external services is zero rupees. No paid APIs. No local LLMs (no Ollama). Free tiers and mocks only. Every provider must keep a working free or mock mode.
2. Never weaken tenant isolation. Every company-scoped query must filter by company_id obtained from deps.tenant(), never from the request body. Add a test for any new endpoint that reads or writes company data.
3. Safety rules (emergency and human hand-off) stay in code, not in the model prompt.
4. Keep backend dependencies minimal. Beginner-friendly Windows 11 setup must keep working (setup.bat, run.bat). The laptop has 8 GB of RAM.
5. Keep docs/ up to date when behaviour changes.

How to run: double-click setup.bat then run.bat (Windows), or see docs/INSTALLATION_AND_RUN_GUIDE.md.
How to test: python -m unittest discover -s tests (inside backend/), and python scripts/smoke_test.py against a running server.

Important: the first version was written without being able to start the server or open the UI in a browser. FIRST, run the server, fix any startup errors, run the smoke test, open the UI and fix visual or functional bugs. Report what you changed.

Then continue with this roadmap, one item at a time, asking me before big decisions:
1. Verify Gemini and Sarvam end to end in all three languages; fix model names or audio format issues.
2. Store call audio and play it in the call drawer.
3. Telephony adapter and webhook (Exotel or Twilio) that opens the same VoiceSession.
4. Barge-in and lower-latency streaming.
5. CSV export, lead assignment, WhatsApp or SMS follow-up.
6. PostgreSQL migration, Docker, email password reset, audit log.
```

## Handy first prompts after the briefing

- "Start the server, show me any errors, and fix them. Then run scripts/smoke_test.py."
- "Open the app and review the Voice Studio page on a laptop screen and a phone width. List visual problems before fixing."
- "Add CSV export to the Calls and Records pages, with a test proving a client only exports their own company's rows."
- "Add an Exotel telephony adapter following docs/PROJECT_DOCUMENTATION.md section 9. Use a mock Exotel webhook for tests."

## If you only have a chat assistant (no coding tool)

Paste the Briefing, then paste the contents of the file you want changed (for example `backend/app/routers/client.py`) and describe the change. Ask for the complete updated file so you can replace it directly.
