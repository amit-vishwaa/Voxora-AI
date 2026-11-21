"""Chooses the active provider for each job from settings. Missing keys fall back to free modes."""
from ..config import settings
from .gemini import GeminiLLM
from .mock import MockLLM, MockSTT, MockTTS
from .sarvam import SarvamSTT, SarvamTTS


def get_llm():
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return GeminiLLM(settings.gemini_api_key, settings.gemini_model)
    return MockLLM()


def get_fallback_llm():
    return MockLLM()


def get_stt():
    """None means the browser does speech-to-text on the caller's side."""
    if settings.stt_provider == "sarvam" and settings.sarvam_api_key:
        return SarvamSTT(settings.sarvam_api_key, settings.sarvam_stt_model)
    if settings.stt_provider == "mock":
        return MockSTT()
    return None


def get_tts():
    if settings.tts_provider == "sarvam" and settings.sarvam_api_key:
        return SarvamTTS(settings.sarvam_api_key, settings.sarvam_tts_model)
    if settings.tts_provider == "mock":
        return MockTTS()
    return None


def status() -> list:
    def line(kind, wanted, active, ok_note, miss_note, key_needed):
        missing_key = key_needed and active in ("mock", "browser")
        return {"kind": kind, "requested": wanted, "active": active, "note": miss_note if missing_key else ok_note}

    llm, stt, tts = get_llm().name, get_stt(), get_tts()
    return [
        line("llm", settings.llm_provider, llm, "Gemini is answering calls." if llm == "gemini" else "Built-in mock agent (free, offline).",
             "GEMINI_API_KEY is missing, so the mock agent is used.", settings.llm_provider == "gemini"),
        line("stt", settings.stt_provider, stt.name if stt else "browser",
             "Sarvam transcribes speech." if stt and stt.name == "sarvam" else "Your browser transcribes speech (Chrome or Edge).",
             "SARVAM_API_KEY is missing, so the browser is used.", settings.stt_provider == "sarvam"),
        line("tts", settings.tts_provider, tts.name if tts else "browser",
             "Sarvam speaks the replies." if tts and tts.name == "sarvam" else "Your browser speaks the replies.",
             "SARVAM_API_KEY is missing, so the browser is used.", settings.tts_provider == "sarvam"),
        {"kind": "telephony", "requested": "browser", "active": "browser",
         "note": "Calls run in the browser. A phone provider (Exotel, Twilio) is a later step."},
    ]
