"""First-run data: the Super Admin login and (optionally) three demo companies with realistic call history.

Demo calls are produced by running scripted callers through the real agent code, so the dashboards
are never empty and every demo call is a genuine example of how the agent behaves."""
import random
from datetime import datetime, timedelta, timezone

from . import db, security
from .config import settings
from .providers.mock import MockLLM
from .services.session import VoiceSession

DEMO_PASSWORD = "Demo@12345"

DEMOS = [
    {"name": "Skyline Realty", "industry": "real_estate", "plan": "growth", "email": "demo.realty@voxora.local",
     "user": "Meera Kapoor", "calls": 46,
     "agents": [("Aarav", "en", "anushka"), ("Kavya", "hi", "kavitha"), ("Dhruv", "gu", "shubh")],
     "kb": [("Whitefield project", "Skyline Heights in Whitefield offers 2 and 3 BHK flats starting at 78 lakh. Possession is planned for March 2028."),
            ("Site visits", "Free site visits run on Saturday and Sunday from 10 AM to 5 PM with complimentary pickup within the city.")]},
    {"name": "CityCare Hospital", "industry": "healthcare", "plan": "scale", "email": "demo.hospital@voxora.local",
     "user": "Dr. Rahul Nair", "calls": 40,
     "agents": [("Asha", "en", "anushka"), ("Sneha", "hi", "kavitha")],
     "kb": [("OPD timings", "General OPD runs Monday to Saturday from 9 AM to 7 PM. Cardiology and orthopaedics visit on Tuesday, Thursday and Saturday."),
            ("Health check-up packages", "The basic health check-up costs 1499 rupees and takes about two hours. Fasting for 8 hours is needed.")]},
    {"name": "BrightPath Academy", "industry": "education", "plan": "starter", "email": "demo.academy@voxora.local",
     "user": "Prof. Nisha Rao", "calls": 32,
     "agents": [("Ishaan", "en", "shubh"), ("Tara", "gu", "rupali")],
     "kb": [("Course fees", "The Data Analytics certificate costs 45000 rupees and can be paid in three instalments. Classes run for four months."),
            ("Batch timings", "Weekday batches run from 6 PM to 8 PM and weekend batches run from 10 AM to 2 PM.")]},
]

NAMES = {"en": ["Rohan Mehta", "Priya Shah", "Amit Patel", "Neha Verma", "Karan Desai", "Sneha Iyer", "Vikram Singh", "Anjali Nair", "Imran Khan", "Pooja Joshi", "Arjun Reddy", "Divya Menon"],
         "hi": ["रोहन मेहता", "प्रिया शाह", "अमित पटेल", "नेहा वर्मा", "करण देसाई", "स्नेहा अय्यर"],
         "gu": ["જીગર પટેલ", "હેતલ શાહ", "ધ્રુવ દેસાઈ", "કિંજલ મહેતા", "મિત શાહ"]}

# Each script is what a caller says: an opening line, then one answer per question the agent asks.
SCRIPTS = {
    "real_estate": {
        "en": [["Hi, I'm looking to buy a flat", "{name}", "2 BHK flat", "Around 80 lakh", "Whitefield", "Within three months", "Saturday at 11 AM"],
               ["Hello, do you have 3 BHK flats?", "My name is {name}", "3 BHK apartment", "About 1.2 crore", "Sarjapur", "Six months", "no"],
               ["I want villa details", "{name}", "Villa", "Two crore", "Devanahalli", "This year", "Sunday at 4 PM, thank you"],
               ["I have a complaint about my booking, I want to speak to your manager"],
               ["Hi", "{name}"]],
        "hi": [["नमस्ते, मुझे फ्लैट चाहिए", "{name}", "2 BHK फ्लैट", "लगभग 80 लाख", "वाकड", "3 महीने में", "शनिवार सुबह 11 बजे"],
               ["नमस्ते", "मेरा नाम {name} है", "3 BHK", "1 करोड़", "हिंजवडी", "6 महीने", "नहीं"]],
        "gu": [["નમસ્તે, મારે ફ્લેટ જોઈએ છે", "{name}", "2 BHK ફ્લેટ", "આશરે 80 લાખ", "બોપલ", "ત્રણ મહિનામાં", "શનિવારે સવારે 11 વાગ્યે"],
               ["નમસ્તે", "મારું નામ {name} છે", "3 BHK", "દોઢ કરોડ", "ગોતા", "છ મહિના", "ના"]]},
    "healthcare": {
        "en": [["Hi, I want to book an appointment", "{name}", "Cardiology", "Regular check-up", "Tomorrow at 10 AM", "{phone}"],
               ["Hello, I need an appointment", "My name is {name}", "Orthopaedics", "Knee pain follow-up", "Friday morning", "{phone}"],
               ["Hello, my father has chest pain"],
               ["Hi", "{name}"]],
        "hi": [["नमस्ते, अपॉइंटमेंट चाहिए", "{name}", "कार्डियोलॉजी", "रूटीन चेकअप", "कल सुबह 10 बजे", "{phone}"]],
        "gu": [["નમસ્તે, મારે એપોઇન્ટમેન્ટ જોઈએ છે", "{name}", "ઓર્થોપેડિક", "ફોલો-અપ", "શુક્રવારે સાંજે", "{phone}"]]},
    "education": {
        "en": [["Hi, I want to know about your courses", "{name}", "Data Analytics certificate", "Bachelor's in commerce", "Weekdays after 6 PM", "{phone}"],
               ["Hello, what is the fee for data analytics?", "{name}", "Data Analytics", "B.Sc", "Saturday morning", "{phone}"],
               ["Hi", "{name}"]],
        "hi": [["नमस्ते, कोर्स की जानकारी चाहिए", "{name}", "डेटा एनालिटिक्स", "ग्रेजुएशन", "शाम 6 बजे के बाद", "{phone}"]],
        "gu": [["નમસ્તે, કોર્સ વિશે માહિતી જોઈએ છે", "{name}", "ડેટા એનાલિટિક્સ", "ગ્રેજ્યુએટ", "સાંજે 6 વાગ્યા પછી", "{phone}"]]},
}


def _simulate(conn, company, agent, knowledge, rng, now):
    scripts = SCRIPTS.get(agent["pack_key"], {}).get(agent["language"])
    if not scripts:
        return
    phone = "9" + "".join(rng.choice("0123456789") for _ in range(9))
    script = rng.choice(scripts)
    if len(script) > 4 and rng.random() < 0.2:
        script = script[:rng.randint(3, len(script) - 1)]  # the caller hangs up part-way
    session = VoiceSession(company, agent, knowledge, MockLLM(), MockLLM())
    session.start()
    name = rng.choice(NAMES[agent["language"]])
    for line in script:
        if session.turn(line.format(name=name, phone=phone))["ended"]:
            break
    days_ago = int(rng.random() ** 1.5 * 29)
    started = (now - timedelta(days=days_ago)).replace(hour=rng.randint(4, 14), minute=rng.randint(0, 59), second=rng.randint(0, 59))
    if started > now:
        started = now - timedelta(minutes=rng.randint(10, 180))
    info = session.finish(conn, started_at=started, duration_sec=max(25, len(session.turns) * rng.randint(9, 17)))
    if info and info["record_id"] and days_ago > 2:
        weights = [3, 3, 2, 1] if days_ago < 10 else [1, 3, 3, 2]
        conn.execute("UPDATE records SET status = ? WHERE id = ?", (rng.choices(["new", "contacted", "won", "closed"], weights)[0], info["record_id"]))
        conn.commit()


def seed_demo(conn) -> None:
    rng, now, stamp = random.Random(2026), datetime.now(timezone.utc), db.now_iso()
    pw = security.hash_password(DEMO_PASSWORD)
    for demo in DEMOS:
        cid = db.run(conn, "INSERT INTO companies(name, industry, plan, contact_email, created_at) VALUES (?,?,?,?,?)",
                     (demo["name"], demo["industry"], demo["plan"], demo["email"], stamp))
        db.run(conn, "INSERT INTO users(company_id, name, email, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
               (cid, demo["user"], demo["email"], pw, "client_admin", stamp))
        if demo["industry"] == "real_estate":
            db.run(conn, "INSERT INTO users(company_id, name, email, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
                   (cid, "Sales Viewer", "viewer.realty@voxora.local", pw, "client_user", stamp))
        for name, lang, voice in demo["agents"]:
            db.run(conn, "INSERT INTO agents(company_id, name, pack_key, language, voice, created_at) VALUES (?,?,?,?,?,?)",
                   (cid, name, demo["industry"], lang, voice, stamp))
        for title, content in demo["kb"]:
            db.run(conn, "INSERT INTO knowledge(company_id, title, content, created_at) VALUES (?,?,?,?)", (cid, title, content, stamp))
        company = db.row(conn, "SELECT * FROM companies WHERE id = ?", (cid,))
        agents = db.rows(conn, "SELECT * FROM agents WHERE company_id = ?", (cid,))
        knowledge = [{"title": t, "content": c} for t, c in demo["kb"]]
        for _ in range(demo["calls"]):
            _simulate(conn, company, rng.choice(agents), knowledge, rng, now)


def ensure_seed(conn) -> None:
    if not db.row(conn, "SELECT id FROM users WHERE role = 'super_admin'"):
        db.run(conn, "INSERT INTO users(company_id, name, email, password_hash, role, must_change, created_at) VALUES (NULL,?,?,?,?,?,?)",
               ("Voxora Admin", settings.admin_email, security.hash_password(settings.admin_password), "super_admin",
                1 if settings.admin_password == "ChangeMe@123" else 0, db.now_iso()))
    if settings.seed_demo and db.row(conn, "SELECT COUNT(*) n FROM companies")["n"] == 0:
        seed_demo(conn)
