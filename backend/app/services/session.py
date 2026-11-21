"""One live conversation. It holds the state in memory and saves everything when the call ends."""
import json
from datetime import datetime, timedelta, timezone

from .. import packs
from ..config import LANGUAGES
from ..providers.base import ProviderError
from . import agent_engine, scoring


def build_summary(pack: dict, collected: dict, status: str) -> str:
    parts = [f"{f['label']}: {collected[f['name']]}" for f in pack["fields"] if f["name"] in collected]
    outcome = {"completed": "Completed.", "transferred": "Transferred to a human.",
               "partial": "Caller left before finishing.", "abandoned": "Caller left early."}[status]
    body = "; ".join(parts) if parts else "No details collected"
    return f"{pack['label']} call. {body}. {outcome}"


class VoiceSession:
    def __init__(self, company: dict, agent: dict, knowledge: list, llm, fallback):
        self.company, self.agent, self.knowledge = company, agent, knowledge
        self.pack = packs.get(agent["pack_key"])
        if self.pack is None:
            raise ValueError(f"Unknown pack '{agent['pack_key']}'")
        self.lang = agent["language"] if agent["language"] in LANGUAGES else "en"
        self.llm, self.fallback = llm, fallback
        self.state = {"pack": self.pack, "lang": self.lang, "collected": {}, "skipped": set(), "asked": None,
                      "retries": {}, "turn": 0, "knowledge": knowledge}
        self.collected, self.skipped = self.state["collected"], self.state["skipped"]
        self.turns, self.sentiments = [], []
        self.started = datetime.now(timezone.utc)
        self.ended, self.final_action = False, None
        self.degraded, self.last_error = False, ""

    # -- helpers ---------------------------------------------------------------------------
    def _add(self, speaker: str, text: str) -> None:
        self.turns.append({"speaker": speaker, "text": text, "at": datetime.now(timezone.utc)})

    def _next_missing(self):
        return next((f["name"] for f in self.pack["fields"] if f["name"] not in self.collected and f["name"] not in self.skipped), None)

    def _closing(self) -> str:
        text = self.pack["closing"].get(self.lang) or self.pack["closing"]["en"]
        return text.format(name=self.collected.get("name", "")).replace(" ,", ",")

    def fields_status(self) -> list:
        return [{"name": f["name"], "label": f["label"], "required": f.get("required", True),
                 "value": self.collected.get(f["name"]), "skipped": f["name"] in self.skipped} for f in self.pack["fields"]]

    def _payload(self, reply: str, action) -> dict:
        return {"reply": reply, "fields": self.fields_status(), "action": action, "ended": self.ended,
                "degraded": self.degraded, "note": self.last_error if self.degraded else ""}

    # -- conversation ----------------------------------------------------------------------
    def greeting(self) -> str:
        template = (self.agent.get("greeting") or "").strip() or self.pack["greeting"].get(self.lang) or self.pack["greeting"]["en"]
        return template.replace("{agent}", self.agent["name"]).replace("{company}", self.company["name"])

    def start(self) -> dict:
        text = self.greeting()
        self._add("agent", text)
        return self._payload(text, None)

    def turn(self, user_text: str) -> dict:
        text = " ".join((user_text or "").split())[:1000]
        if self.ended or not text:
            return self._payload("", None)
        self._add("caller", text)
        self.state["turn"] = sum(1 for t in self.turns if t["speaker"] == "caller")

        handoff = agent_engine.check_escalation(self.pack, self.lang, text)
        if handoff:
            reply, action = handoff, "transfer_to_human"
            self.sentiments.append("negative")
        else:
            history = [{"role": "user" if t["speaker"] == "caller" else "model", "text": t["text"]} for t in self.turns]
            system = agent_engine.build_system_prompt(self.company, self.agent, self.pack, self.lang, self.knowledge, self.collected)
            try:
                raw = self.llm.generate(system, history, self.state)
            except ProviderError as exc:
                self.degraded, self.last_error = True, str(exc)
                raw = self.fallback.generate(system, history, self.state)
            result = agent_engine.normalize(raw, self.pack)
            self.collected.update(result["fields"])
            self.skipped.update(result["skipped"])
            self.state["asked"] = result["asked"] or self._next_missing()
            if result["sentiment"]:
                self.sentiments.append(result["sentiment"])
            reply, action = result["reply"], result["action"]
            required_missing = [f for f in self.pack["fields"] if f.get("required", True) and f["name"] not in self.collected]
            if action == "complete" and required_missing:
                action = None
            if action is None and self._next_missing() is None:
                action = "complete"
            if action == "complete":
                reply = self._closing()
            elif not reply:
                reply = self.pack["fields"][0]["ask"].get(self.lang, "")
        if action in ("complete", "transfer_to_human", "end_call"):
            self.ended, self.final_action = True, action
        self._add("agent", reply)
        return self._payload(reply, action)

    # -- saving ----------------------------------------------------------------------------
    def status(self) -> str:
        if self.final_action == "complete":
            return "completed"
        if self.final_action == "transfer_to_human":
            return "transferred"
        return "partial" if len(self.collected) >= 2 else "abandoned"

    def finish(self, conn, started_at=None, duration_sec=None):
        """Save the call, its transcript and (when useful) a lead/appointment/ticket record."""
        callers = [t for t in self.turns if t["speaker"] == "caller"]
        if not callers:
            return None
        self.ended = True
        status = self.status()
        start = started_at or self.started
        duration = duration_sec if duration_sec is not None else max(1, int((datetime.now(timezone.utc) - self.started).total_seconds()))
        neg, pos = self.sentiments.count("negative"), self.sentiments.count("positive")
        # Simple heuristic: angry words or a hand-off mean negative; thanks or a finished booking mean positive.
        if status == "transferred" or (neg and neg >= pos):
            sentiment = "negative"
        elif pos or status == "completed":
            sentiment = "positive"
        else:
            sentiment = "neutral"
        value = scoring.score(self.pack, self.collected, status == "completed")
        summary = build_summary(self.pack, self.collected, status)
        iso = lambda d: d.isoformat(timespec="seconds")
        with conn:
            cur = conn.execute(
                "INSERT INTO calls(company_id, agent_id, agent_name, channel, language, started_at, duration_sec, status,"
                " sentiment, summary, score, collected_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (self.company["id"], self.agent["id"], self.agent["name"], "browser", self.lang, iso(start), duration,
                 status, sentiment, summary, value, json.dumps(self.collected, ensure_ascii=False)))
            call_id = cur.lastrowid
            n = len(self.turns)
            for i, t in enumerate(self.turns):
                at = start + timedelta(seconds=duration * i / max(n, 1)) if started_at else t["at"]
                conn.execute("INSERT INTO turns(call_id, company_id, idx, speaker, text, at) VALUES (?,?,?,?,?,?)",
                             (call_id, self.company["id"], i, t["speaker"], t["text"], iso(at)))
            record_id = None
            if self.collected and status != "abandoned":
                title = " - ".join(self.collected[k] for k in self.pack.get("title_fields", []) if self.collected.get(k)) or f"Call {call_id}"
                cur = conn.execute(
                    "INSERT INTO records(company_id, call_id, agent_id, type, title, data_json, score, status, created_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (self.company["id"], call_id, self.agent["id"], self.pack["record_type"], title,
                     json.dumps(self.collected, ensure_ascii=False), value, "new", iso(start)))
                record_id = cur.lastrowid
        return {"call_id": call_id, "record_id": record_id, "status": status, "summary": summary, "score": value,
                "sentiment": sentiment, "duration_sec": duration}
