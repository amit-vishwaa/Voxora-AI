"""Sarvam AI speech services (speech-to-text and text-to-speech) over plain REST."""
import httpx

from ..config import LANG_CODES
from .base import ProviderError, STTProvider, TTSProvider

_BASE = "https://api.sarvam.ai"


def _check(resp, what: str) -> None:
    if resp.status_code in (401, 403):
        raise ProviderError("Sarvam rejected the API key. Check SARVAM_API_KEY in .env.")
    if resp.status_code == 429:
        raise ProviderError("Sarvam rate limit or credits reached.")
    if resp.status_code != 200:
        raise ProviderError(f"Sarvam {what} failed with status {resp.status_code}.")


class SarvamSTT(STTProvider):
    name = "sarvam"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def transcribe(self, audio, mime, language):
        mime = (mime or "audio/webm").split(";")[0].strip()
        ext = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/wav": "wav", "audio/x-wav": "wav", "audio/mp4": "mp4"}.get(mime, "webm")
        try:
            resp = httpx.post(f"{_BASE}/speech-to-text", headers={"api-subscription-key": self.api_key},
                              files={"file": (f"audio.{ext}", audio, mime)},
                              data={"model": self.model, "mode": "transcribe", "language_code": LANG_CODES.get(language, "unknown")},
                              timeout=30)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not reach Sarvam: {exc.__class__.__name__}") from exc
        _check(resp, "speech-to-text")
        return str(resp.json().get("transcript", "")).strip()


class SarvamTTS(TTSProvider):
    name = "sarvam"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def synthesize(self, text, language, voice):
        body = {"text": text[:2400], "target_language_code": LANG_CODES.get(language, "en-IN"),
                "model": self.model, "speaker": voice or "anushka"}
        try:
            resp = httpx.post(f"{_BASE}/text-to-speech", headers={"api-subscription-key": self.api_key}, json=body, timeout=30)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not reach Sarvam: {exc.__class__.__name__}") from exc
        _check(resp, "text-to-speech")
        audios = resp.json().get("audios") or []
        if not audios:
            raise ProviderError("Sarvam returned no audio.")
        return {"audio_b64": audios[0], "mime": "audio/wav"}
