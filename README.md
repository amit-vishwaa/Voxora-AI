# Voxora Voice

**Intelligent Conversations. Limitless Possibilities.**

A multi-tenant AI voice agent platform. One engine serves many industries (real estate, healthcare, education, sales, support) in **Hindi, English and Gujarati**. There are two kinds of login:

- **Super Admin** (your team): sees every company, creates companies and client logins, sets plans.
- **Client** (a customer company): sees only its own agents, calls, transcripts, summaries, leads or appointments, analytics and plan usage.

It costs nothing to run. The built-in mock agent works offline with no key. When you are ready, switch on **Gemini** (free tier) for the AI and **Sarvam AI** for speech, one line each in a settings file.

## Start in three steps (Windows 11)

1. Install **Python 3.12** from python.org. On the first screen tick **"Add python.exe to PATH"**.
2. Double-click **setup.bat** (once). Wait until it says "Setup finished".
3. Double-click **run.bat**. Your browser opens at http://localhost:8000. Click a demo login to explore.

New to all this? Follow the step-by-step guide: **docs/INSTALLATION_AND_RUN_GUIDE.md**.

## Documents

| File | What it is for |
|---|---|
| docs/INSTALLATION_AND_RUN_GUIDE.md | Install and run from zero, add API keys, troubleshooting |
| docs/PROJECT_DOCUMENTATION.md | Architecture, data model, API, how to extend |
| docs/MANUAL_SETUP_AND_NEXT_STEPS.md | Things only you can do (keys, passwords, phone numbers, going live) |
| docs/DEVELOPMENT_STATUS.md | What is finished, what was tested, what is not built yet |
| docs/CONTINUE_WITH_AI.md | A ready-made briefing to continue the project in Google Antigravity or OpenAI Codex |

## What is inside

```
backend/    FastAPI server, database, industry packs, AI provider adapters, tests
frontend/   The web app (plain HTML, CSS and JavaScript, no build step)
docs/       The guides above
setup.bat   One-time installer      run.bat   Start the app      test.bat   Run the tests
```
