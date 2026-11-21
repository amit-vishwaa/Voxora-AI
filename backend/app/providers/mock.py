"""Free, offline mock providers. The mock LLM is a small rule-based agent that walks through the
pack's fields in three languages, so the whole product can be demonstrated with no API key."""
import re
import unicodedata

from .base import LLMProvider, STTProvider, TTSProvider

I18N = {
    "ack": {"en": ["Got it.", "Thank you.", "Understood.", "Noted."],
            "hi": ["जी, ठीक है।", "धन्यवाद।", "नोट कर लिया गया है।"],
            "gu": ["સારું.", "આભાર.", "નોંધ્યું."]},
    "intro": {"en": "Happy to help with that.", "hi": "जी, ज़रूर।", "gu": "જી, જરૂર."},
    "retry_phone": {"en": "I didn't catch the full number. Could you say it again with all ten digits?",
                    "hi": "पूरा नंबर समझ नहीं आया। कृपया दस अंकों का नंबर फिर से बताइए।",
                    "gu": "પૂરો નંબર સમજાયો નહીં. કૃપા કરીને દસ અંકનો નંબર ફરીથી જણાવો."},
    "goodbye": {"en": "Thank you for calling. Goodbye!", "hi": "कॉल करने के लिए धन्यवाद। नमस्ते!",
                "gu": "કૉલ કરવા બદલ આભાર. નમસ્તે!"},
    "kb": {"en": "Here is what I can share:", "hi": "इसकी जानकारी यह है:", "gu": "આની માહિતી આ છે:"},
    "back": {"en": "Now, ", "hi": "अब, ", "gu": "હવે, "},
    "skip": {"en": ["no", "skip", "not now", "later", "don't want"], "hi": ["नहीं", "बाद में", "स्किप"],
             "gu": ["ના", "પછી", "નહીં"]},
    "end": {"en": ["bye", "goodbye", "that's all", "that is all", "no thanks"], "hi": ["बाय", "अलविदा", "बस इतना ही"],
            "gu": ["બાય", "આટલું જ"]},
    "question": {"en": ["what", "how", "when", "where", "which", "do you", "can you", "is there", "tell me", "fee", "price", "cost"],
                 "hi": ["क्या", "कितना", "कितनी", "कब", "कहाँ", "कहां", "कैसे", "फीस", "कीमत"],
                 "gu": ["શું", "કેટલું", "કેટલી", "ક્યારે", "ક્યાં", "કેવી રીતે", "ફી", "કિંમત"]},
    "pos": {"en": ["thank", "great", "good", "perfect", "excellent", "happy", "awesome"],
            "hi": ["धन्यवाद", "शुक्रिया", "बढ़िया", "बहुत अच्छा", "शानदार"],
            "gu": ["આભાર", "સરસ", "બહુ સરસ", "ઉત્તમ"]},
    "neg": {"en": ["angry", "bad", "worst", "terrible", "complaint", "useless", "waste", "frustrated", "not happy", "delay"],
            "hi": ["गुस्सा", "खराब", "बेकार", "शिकायत", "परेशान", "देरी"],
            "gu": ["ગુસ્સો", "ખરાબ", "બેકાર", "ફરિયાદ", "પરેશાન", "મોડું"]},
}

_NAME_PREFIX = {"en": r"^(?:hi|hello)?[,\s]*(?:my name is|this is|i am|i'm|it's|name is)\s+",
                "hi": r"^(?:मेरा नाम है|मेरा नाम|मैं)\s+", "gu": r"^(?:મારું નામ|હું)\s+"}
_NAME_SUFFIX = {"en": r"$^", "hi": r"\s+(?:है|हूँ|हूं)\s*$", "gu": r"\s+(?:છે|છું)\s*$"}


def ascii_digits(text: str) -> str:
    out = []
    for ch in text:
        if ch.isdigit():
            try:
                out.append(str(unicodedata.digit(ch)))
            except ValueError:
                pass
    return "".join(out)


def _has(text: str, words: list, lang: str) -> bool:
    if lang == "en":
        return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)
    return any(w in text for w in words)


def _tokens(text: str) -> set:
    return {w for w in re.split(r"[\s,.;:!?।()\[\]\"'-]+", text.lower()) if len(w) > 3}


def find_knowledge(lowered: str, docs: list):
    query = _tokens(lowered)
    best, best_score = None, 0
    for d in docs:
        score = len(query & _tokens(d["title"] + " " + d["content"]))
        if score > best_score:
            best, best_score = d, score
    return best if best_score >= 2 else None


def _extract(field: dict, text: str, lang: str) -> str:
    value = text.strip()
    if field["name"] == "name":
        value = re.sub(_NAME_PREFIX[lang], "", value, flags=re.I)
        value = re.sub(_NAME_SUFFIX[lang], "", value).strip(" .,")
        if lang == "en":
            value = value.title()
    elif field["type"] == "phone":
        digits = ascii_digits(value)
        value = digits[-10:] if len(digits) >= 10 else value
    return value.strip(" .")[:200]


def _ask(field: dict, lang: str) -> str:
    return field["ask"].get(lang) or field["ask"]["en"]


class MockLLM(LLMProvider):
    name = "mock"

    def generate(self, system_prompt, history, state):
        pack, lang = state["pack"], state["lang"]
        text = history[-1]["text"].strip() if history else ""
        lowered = text.lower()
        fields = pack["fields"]
        collected, skipped = state["collected"], state["skipped"]
        retries = state.setdefault("retries", {})
        asked = state.get("asked")
        turn = state.get("turn", 0)
        sentiment = "neutral"
        if _has(lowered, I18N["neg"][lang], lang):
            sentiment = "negative"
        elif _has(lowered, I18N["pos"][lang], lang):
            sentiment = "positive"

        def result(reply, update=None, action=None, next_asked=None):
            return {"reply": reply, "fields": update or {}, "action": action, "sentiment": sentiment, "asked": next_asked}

        if _has(lowered, I18N["end"][lang], lang):
            return result(I18N["goodbye"][lang], action="end_call", next_asked=asked)

        field = next((f for f in fields if f["name"] == asked), None)
        pending = field or next((f for f in fields if f["name"] not in collected and f["name"] not in skipped), None)

        doc = find_knowledge(lowered, state.get("knowledge", []))
        if doc and _has(lowered, I18N["question"][lang], lang) + (1 if "?" in text else 0):
            reply = I18N["kb"][lang] + " " + doc["content"].strip()[:280]
            if pending:
                reply += " " + I18N["back"][lang] + _ask(pending, lang)
            return result(reply, next_asked=pending["name"] if pending else None)

        update = {}
        if field:
            if not field.get("required", True) and _has(lowered, I18N["skip"][lang], lang):
                skipped.add(field["name"])
            else:
                if field["type"] == "phone" and len(ascii_digits(text)) < 10 and retries.get(field["name"], 0) < 1:
                    retries[field["name"]] = retries.get(field["name"], 0) + 1
                    return result(I18N["retry_phone"][lang], next_asked=field["name"])
                value = _extract(field, text, lang)
                if value:
                    update[field["name"]] = value
                    collected = {**collected, **update}

        nxt = next((f for f in fields if f["name"] not in collected and f["name"] not in skipped), None)
        if nxt is None:
            name = collected.get("name", "")
            closing = pack["closing"].get(lang, pack["closing"]["en"]).format(name=name).replace(" ,", ",")
            return result(closing, update, action="complete")
        lead = I18N["intro"][lang] if not field else I18N["ack"][lang][turn % len(I18N["ack"][lang])]
        return result(f"{lead} {_ask(nxt, lang)}", update, next_asked=nxt["name"])


class MockSTT(STTProvider):
    name = "mock"

    def transcribe(self, audio, mime, language):
        return "This is a mock transcript." if language == "en" else "यह एक मॉक ट्रांसक्रिप्ट है।"


class MockTTS(TTSProvider):
    name = "mock"

    def synthesize(self, text, language, voice):
        return None
