"""Google Gemini (free tier from Google AI Studio) as the LLM. Plain REST, no extra SDK."""
import json
import time

import httpx

from .base import LLMProvider, ProviderError


class GeminiLLM(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def generate(self, system_prompt, history, state):
        contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]} for m in history]
        while contents and contents[0]["role"] == "model":
            contents.pop(0)  # Gemini wants the conversation to start with the caller
        body = {"systemInstruction": {"parts": [{"text": system_prompt}]}, "contents": contents,
                "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json", "maxOutputTokens": 600}}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        resp = None
        for attempt in range(2):
            try:
                resp = httpx.post(url, headers=headers, json=body, timeout=25)
            except httpx.HTTPError as exc:
                raise ProviderError(f"Could not reach Gemini: {exc.__class__.__name__}") from exc
            if resp.status_code != 429:
                break
            time.sleep(2)  # free tier rate limit: wait once, then give up
        if resp.status_code == 404:
            raise ProviderError(f"Gemini model '{self.model}' was not found. Set GEMINI_MODEL in .env to a current model name.")
        if resp.status_code in (400, 401, 403):
            raise ProviderError("Gemini rejected the request. Check GEMINI_API_KEY in .env.")
        if resp.status_code == 429:
            raise ProviderError("Gemini free-tier limit reached. Wait a minute or switch LLM_PROVIDER=mock.")
        if resp.status_code != 200:
            raise ProviderError(f"Gemini error {resp.status_code}")
        try:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(text)
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderError("Gemini returned an answer in an unexpected format.") from exc
        if not isinstance(data, dict) or not str(data.get("reply", "")).strip():
            raise ProviderError("Gemini returned an empty reply.")
        return {"reply": str(data["reply"]).strip(), "fields": data.get("fields") or {},
                "action": data.get("action"), "sentiment": data.get("sentiment"), "asked": None}
