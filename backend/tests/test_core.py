"""Core tests: they need only the Python standard library.   Run:  python -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["SEED_DEMO"] = "false"

from app import db, packs, security  # noqa: E402
from app.providers.mock import MockLLM, ascii_digits, find_knowledge  # noqa: E402
from app.services import agent_engine, analytics, scoring  # noqa: E402
from app.services.session import VoiceSession  # noqa: E402


class SecurityTests(unittest.TestCase):
    def test_password_roundtrip(self):
        stored = security.hash_password("Secret@123")
        self.assertTrue(security.verify_password("Secret@123", stored))
        self.assertFalse(security.verify_password("wrong", stored))
        self.assertFalse(security.verify_password("x", "not-a-hash"))

    def test_token_roundtrip_and_tampering(self):
        token = security.create_token({"sub": 7}, "secret", hours=1)
        self.assertEqual(security.decode_token(token, "secret")["sub"], 7)
        with self.assertRaises(ValueError):
            security.decode_token(token, "other-secret")
        head, body, sig = token.split(".")
        with self.assertRaises(ValueError):
            security.decode_token(f"{head}.{body}x.{sig}", "secret")

    def test_expired_token(self):
        token = security.create_token({"sub": 1}, "secret", hours=-1)
        with self.assertRaises(ValueError):
            security.decode_token(token, "secret")


class PackTests(unittest.TestCase):
    def test_all_packs_are_complete(self):
        for key, pack in packs.load_all().items():
            names = {f["name"] for f in pack["fields"]}
            for lang in ("en", "hi", "gu"):
                self.assertIn(lang, pack["greeting"], key)
                self.assertIn(lang, pack["closing"], key)
                for f in pack["fields"]:
                    self.assertTrue(f["ask"][lang].strip(), f"{key}.{f['name']}.{lang}")
            self.assertTrue(set(pack["scoring"]["fields"]) <= names, key)
            self.assertTrue(set(pack["title_fields"]) <= names, key)


def make_world():
    conn = db.connect(os.path.join(tempfile.mkdtemp(), "w.db"))
    db.init_db(conn)
    stamp = db.now_iso()
    ids = {}
    for name, industry in (("Alpha Realty", "real_estate"), ("Beta Hospital", "healthcare")):
        cid = db.run(conn, "INSERT INTO companies(name, industry, created_at) VALUES (?,?,?)", (name, industry, stamp))
        aid = db.run(conn, "INSERT INTO agents(company_id, name, pack_key, language, voice, created_at) VALUES (?,?,?,?,?,?)",
                     (cid, "Aarav", industry, "en", "anushka", stamp))
        ids[industry] = (cid, aid)
    return conn, ids


def session_for(conn, cid, aid, lang="en", knowledge=None):
    company = db.row(conn, "SELECT * FROM companies WHERE id = ?", (cid,))
    agent = db.row(conn, "SELECT * FROM agents WHERE id = ?", (aid,))
    agent["language"] = lang
    return VoiceSession(company, agent, knowledge or [], MockLLM(), MockLLM())


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.conn, self.ids = make_world()

    def test_full_real_estate_call_creates_call_transcript_and_record(self):
        cid, aid = self.ids["real_estate"]
        s = session_for(self.conn, cid, aid)
        s.start()
        for line in ["I want a flat", "my name is rohan mehta", "2 BHK", "80 lakh", "Whitefield", "3 months", "no"]:
            out = s.turn(line)
        self.assertEqual(out["action"], "complete")
        self.assertTrue(out["ended"])
        info = s.finish(self.conn)
        self.assertEqual(info["status"], "completed")
        self.assertEqual(db.row(self.conn, "SELECT name FROM agents WHERE id = ?", (aid,))["name"], "Aarav")
        record = db.row(self.conn, "SELECT * FROM records WHERE id = ?", (info["record_id"],))
        self.assertEqual(record["company_id"], cid)
        self.assertIn("Rohan Mehta", record["title"])
        self.assertGreaterEqual(db.row(self.conn, "SELECT COUNT(*) n FROM turns WHERE call_id = ?", (info["call_id"],))["n"], 14)

    def test_hindi_flow(self):
        cid, aid = self.ids["real_estate"]
        s = session_for(self.conn, cid, aid, "hi")
        s.start()
        out = s.turn("नमस्ते, मुझे फ्लैट चाहिए")
        self.assertIn("नाम", out["reply"])
        s.turn("मेरा नाम रोहन मेहता है")
        self.assertEqual(s.collected["name"], "रोहन मेहता")

    def test_emergency_hands_off_to_human_in_every_language(self):
        cid, aid = self.ids["healthcare"]
        for lang, phrase in (("en", "my father has chest pain"), ("hi", "मेरे पिता को सीने में दर्द है"), ("gu", "મને છાતીમાં દુખાવો છે")):
            s = session_for(self.conn, cid, aid, lang)
            s.start()
            out = s.turn(phrase)
            self.assertEqual(out["action"], "transfer_to_human", lang)
            self.assertEqual(s.status(), "transferred")

    def test_phone_needs_ten_digits_once(self):
        cid, aid = self.ids["healthcare"]
        s = session_for(self.conn, cid, aid)
        s.start()
        for line in ["book appointment", "Asha Rao", "cardiology", "check up", "tomorrow 10 am"]:
            s.turn(line)
        self.assertIn("ten digits", s.turn("12345")["reply"])
        out = s.turn("9876543210")
        self.assertEqual(out["action"], "complete")
        self.assertEqual(s.collected["phone"], "9876543210")

    def test_knowledge_answer_then_back_to_questions(self):
        cid, aid = self.ids["real_estate"]
        kb = [{"title": "Site visits", "content": "Free site visits run on Saturday and Sunday from 10 AM to 5 PM."}]
        s = session_for(self.conn, cid, aid, knowledge=kb)
        s.start()
        out = s.turn("When are the site visits?")
        self.assertIn("Saturday and Sunday", out["reply"])
        self.assertIn("name", out["reply"].lower())

    def test_call_with_no_caller_speech_is_not_saved(self):
        cid, aid = self.ids["real_estate"]
        s = session_for(self.conn, cid, aid)
        s.start()
        self.assertIsNone(s.finish(self.conn))

    def test_provider_failure_falls_back_to_mock(self):
        from app.providers.base import LLMProvider, ProviderError

        class Broken(LLMProvider):
            def generate(self, *a):
                raise ProviderError("limit reached")

        cid, aid = self.ids["real_estate"]
        s = session_for(self.conn, cid, aid)
        s.llm = Broken()
        s.start()
        out = s.turn("hello")
        self.assertTrue(out["degraded"])
        self.assertIn("name", out["reply"].lower())


class TenantDataTests(unittest.TestCase):
    def test_analytics_never_mix_companies(self):
        conn, ids = make_world()
        (c1, a1), (c2, a2) = ids["real_estate"], ids["healthcare"]
        s = session_for(conn, c1, a1)
        s.start()
        s.turn("hello")
        s.turn("Rohan")
        s.finish(conn)
        self.assertEqual(analytics.dashboard(conn, c1)["kpis"]["calls"], 1)
        self.assertEqual(analytics.dashboard(conn, c2)["kpis"]["calls"], 0)
        self.assertEqual(analytics.platform_overview(conn)["totals"]["calls_30d"], 1)


class HelperTests(unittest.TestCase):
    def test_digits_in_indian_scripts(self):
        self.assertEqual(ascii_digits("९८७६५ 43210"), "9876543210")

    def test_scoring_and_labels(self):
        pack = packs.get("real_estate")
        self.assertEqual(scoring.score(pack, {"budget": "x", "timeline": "y"}, False), 50)
        self.assertEqual(scoring.score(pack, {k: "x" for k in pack["scoring"]["fields"]}, True), 100)
        self.assertEqual(scoring.label(80), "hot")
        self.assertEqual(scoring.label(10), "cold")

    def test_normalize_drops_unknown_fields(self):
        pack = packs.get("sales")
        out = agent_engine.normalize({"reply": " hi ", "fields": {"name": "A", "hack": "x", "need": ""}, "action": "rm -rf"}, pack)
        self.assertEqual(out["fields"], {"name": "A"})
        self.assertIsNone(out["action"])

    def test_find_knowledge_needs_two_shared_words(self):
        docs = [{"title": "Course fees", "content": "The analytics certificate costs 45000 rupees."}]
        self.assertIsNone(find_knowledge("fees", docs))
        self.assertIsNotNone(find_knowledge("course fees please", docs))


if __name__ == "__main__":
    unittest.main()
