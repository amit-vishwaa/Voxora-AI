"""Live voice: a WebSocket for the conversation, plus small endpoints for server-side speech services."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from .. import db
from ..config import PLANS, VOICES, settings
from ..deps import current_user, load_user
from ..providers import registry
from ..providers.base import ProviderError
from ..schemas import TTSIn
from ..services import analytics
from ..services.session import VoiceSession

router = APIRouter(prefix="/api/voice", tags=["voice"])
_live = 0  # live calls right now (protects a small laptop)


@router.post("/stt")
async def speech_to_text(request: Request, language: str = "en", user=Depends(current_user)):
    provider = registry.get_stt()
    if provider is None:
        raise HTTPException(400, "Speech-to-text runs in the browser. Set STT_PROVIDER=sarvam in .env to use Sarvam.")
    audio = await request.body()
    if not audio:
        raise HTTPException(400, "No audio received.")
    if len(audio) > 5_000_000:
        raise HTTPException(413, "Audio is too long. Keep each turn under 30 seconds.")
    try:
        text = await asyncio.to_thread(provider.transcribe, audio, request.headers.get("content-type", "audio/webm"), language)
    except ProviderError as exc:
        raise HTTPException(502, str(exc))
    return {"text": text}


@router.post("/tts")
async def text_to_speech(body: TTSIn, user=Depends(current_user)):
    provider = registry.get_tts()
    empty = {"audio_b64": None, "mime": None}
    if provider is None:
        return empty
    voice = body.voice if body.voice in VOICES else "anushka"
    try:
        return await asyncio.to_thread(provider.synthesize, body.text, body.language, voice) or empty
    except ProviderError as exc:
        raise HTTPException(502, str(exc))


def _save(session: VoiceSession):
    conn = db.connect()
    try:
        return session.finish(conn)
    finally:
        conn.close()


async def _fail(ws: WebSocket, text: str, code: int = 4403):
    await ws.send_json({"type": "error", "text": text})
    await ws.close(code=code)


@router.websocket("/ws")
async def live_call(ws: WebSocket, token: str = "", agent_id: int = 0):
    global _live
    await ws.accept()
    conn = db.connect()
    session, saved, counted = None, False, False
    try:
        try:
            user = load_user(conn, token)
        except PermissionError as exc:
            return await _fail(ws, str(exc), 4401)
        agent = db.row(conn, "SELECT * FROM agents WHERE id = ?", (agent_id,))
        if not agent or (user["role"] != "super_admin" and agent["company_id"] != user["company_id"]):
            return await _fail(ws, "Agent not found.")
        company = db.row(conn, "SELECT * FROM companies WHERE id = ?", (agent["company_id"],))
        if company["status"] != "active":
            return await _fail(ws, "This company account is suspended.")
        if not agent["active"]:
            return await _fail(ws, "This agent is switched off. Turn it on in Agents.")
        if analytics.minutes_used(conn, company["id"]) >= PLANS.get(company["plan"], PLANS["trial"])["minutes"]:
            return await _fail(ws, "All minutes in this plan are used. Upgrade the plan to keep calling.")
        if _live >= settings.max_live_sessions:
            return await _fail(ws, "Too many live calls right now. Please try again in a moment.")
        _live, counted = _live + 1, True
        knowledge = db.rows(conn, "SELECT title, content FROM knowledge WHERE company_id = ? AND (agent_id IS NULL OR agent_id = ?)",
                            (company["id"], agent["id"]))
        session = VoiceSession(company, agent, knowledge, registry.get_llm(), registry.get_fallback_llm())
        await ws.send_json({"type": "ready", "language": session.lang, "voice": agent["voice"], "agent": agent["name"],
                            "company": company["name"], **session.start()})
        while not session.ended:
            try:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=settings.idle_timeout_sec)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "notice", "text": "The call ended after a period of silence."})
                break
            except ValueError:
                continue  # not valid JSON, ignore
            kind = msg.get("type") if isinstance(msg, dict) else None
            if kind == "end":
                break
            if kind == "user_text":
                out = await asyncio.to_thread(session.turn, str(msg.get("text", "")))
                await ws.send_json({"type": "agent", **out})
        info = await asyncio.to_thread(_save, session)
        saved = True
        try:
            await ws.send_json({"type": "ended", "call": info})
            await ws.close()
        except (WebSocketDisconnect, RuntimeError):
            pass  # the browser already left; the call is saved either way
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if session is not None and not saved:
            await asyncio.to_thread(_save, session)
        if counted:
            _live -= 1
        conn.close()
