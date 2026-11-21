# Manual Setup and Next Steps

Things only you can do, in a sensible order.

## A. Before you show this to anyone

1. **Change the Super Admin password.** Sign in as admin@voxora.local, click **Password** (bottom left), and set a strong one. The starter password is public in this guide.
2. **Decide about demo data.** Keep `SEED_DEMO=true` for demos. For real use set `SEED_DEMO=false`, delete `backend\data\voxora.db`, and restart. Then create real companies from the Super Admin screen.
3. **Never share the demo logins** outside your team. If you keep the demo companies, change their passwords (Companies, Users, Reset password).

## B. Get your free keys (one time)

| Service | Where | Put in `.env` |
|---|---|---|
| Gemini | aistudio.google.com, Get API key | `GEMINI_API_KEY`, then `LLM_PROVIDER=gemini` |
| Sarvam AI | sarvam.ai, dashboard, API keys | `SARVAM_API_KEY`, then `STT_PROVIDER=sarvam` and `TTS_PROVIDER=sarvam` |

Both have free allowances that change over time. Check the current limits on their sites. If a limit is reached, calls keep working with the built-in agent and a notice appears in Voice Studio.

Model names for Gemini change. If you see "model not found", copy a current free model name into `GEMINI_MODEL`.

## C. Check the real services work (first time)

The Gemini and Sarvam connections were written from their public documentation but could not be called while this project was built. Test them once:

1. Turn them on as in section B and restart.
2. In Voice Studio, make one call per language (English, Hindi, Gujarati).
3. If something fails, the message on screen says why. Likely culprits: a wrong key, a changed model name, or a changed audio format (see DEVELOPMENT_STATUS.md, "Needs your attention").

## D. Real phone calls (later, will cost money)

Browser calls are free. Real phone numbers need a telephony provider. Common choices for India are Exotel, Ozonetel, Knowlarity and Twilio. They charge for the number and per minute, which goes beyond a zero-rupee budget. When you are ready, the work is a new adapter plus a webhook that opens a `VoiceSession` (see PROJECT_DOCUMENTATION.md section 9).

## E. Before real customers use it

- **Tell callers they are speaking to an AI** (the greeting can say so: edit it per agent in Agents).
- **Consent and privacy.** Voice and personal details are personal data. Check data-protection rules that apply to you (in India, the Digital Personal Data Protection Act) and telecom rules for outbound calling. This project is not legal advice.
- **Do not send real patient or customer data to free AI tiers.** Free tiers may use prompts to improve products. Use a paid tier with suitable terms for real data.
- **Run over HTTPS** and on a server, not a laptop (see F).
- **Back up** `backend/data/voxora.db` regularly (copy the file while the server is stopped).

## F. Putting it online (later)

Any small Linux server works: install Python, copy the project, run `uvicorn` behind a web server such as Caddy or Nginx that provides HTTPS and WebSocket support. For several customers move from SQLite to PostgreSQL (the data layer is isolated in `backend/app/db.py` and the routers). Run one server process, because the live-call counter and login rate limiter are kept in memory.

## G. Suggested roadmap

1. Prove the loop with Gemini and Sarvam in three languages (section C).
2. Store call audio (browser recording or telephony recording) and play it in the call drawer.
3. Add telephony (Exotel or Twilio) as a new adapter.
4. Barge-in (caller can interrupt the agent) and streaming replies for lower latency.
5. Better lead handling: assign leads to team members, export to CSV, WhatsApp or SMS follow-ups.
6. Email-based password reset and an audit log.
7. PostgreSQL, Docker image, backups, monitoring.
