"""Provider interfaces. Every AI service sits behind one of these, so you can swap it in one place."""


class ProviderError(Exception):
    """Raised when an outside service fails. The app falls back to the mock provider for that turn."""


class LLMProvider:
    name = "base"

    def generate(self, system_prompt: str, history: list, state: dict) -> dict:
        """history is [{"role": "user"|"model", "text": str}], the last item being the caller's newest message.

        Return {"reply": str, "fields": {name: value}, "action": None|"complete"|"end_call",
                "sentiment": "positive"|"neutral"|"negative"|None, "asked": field name or None}.
        """
        raise NotImplementedError


class STTProvider:
    name = "base"

    def transcribe(self, audio: bytes, mime: str, language: str) -> str:
        raise NotImplementedError


class TTSProvider:
    name = "base"

    def synthesize(self, text: str, language: str, voice: str):
        """Return {"audio_b64": str, "mime": str} or None when the browser should speak instead."""
        raise NotImplementedError
