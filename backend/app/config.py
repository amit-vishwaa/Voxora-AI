"""Central settings. Values come from environment variables or from backend/.env."""
import os
import secrets
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"


def _load_dotenv() -> None:
    f = BACKEND_DIR / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _secret_key() -> str:
    """Use SECRET_KEY if set, otherwise create one once and keep it in data/.secret_key."""
    configured = os.environ.get("SECRET_KEY", "").strip()
    if configured:
        return configured
    path = BACKEND_DIR / "data" / ".secret_key"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    value = secrets.token_urlsafe(48)
    path.write_text(value, encoding="utf-8")
    return value


class Settings:
    def __init__(self) -> None:
        e = os.environ.get
        self.app_name = "Voxora Voice"
        self.secret_key = _secret_key()
        self.token_hours = int(e("TOKEN_HOURS", "12"))
        self.db_path = e("DB_PATH") or str(BACKEND_DIR / "data" / "voxora.db")
        self.admin_email = e("ADMIN_EMAIL", "admin@voxora.local").strip().lower()
        self.admin_password = e("ADMIN_PASSWORD", "ChangeMe@123")
        self.seed_demo = _bool(e("SEED_DEMO", "true"))
        self.cors_origins = [o.strip() for o in e("CORS_ORIGINS", "").split(",") if o.strip()]
        # Providers: every one has a free "mock" or "browser" mode that needs no key.
        self.llm_provider = e("LLM_PROVIDER", "mock").strip().lower()      # mock | gemini
        self.stt_provider = e("STT_PROVIDER", "browser").strip().lower()   # browser | sarvam | mock
        self.tts_provider = e("TTS_PROVIDER", "browser").strip().lower()   # browser | sarvam | mock
        self.gemini_api_key = e("GEMINI_API_KEY", "").strip()
        self.gemini_model = e("GEMINI_MODEL", "gemini-2.5-flash").strip()
        self.sarvam_api_key = e("SARVAM_API_KEY", "").strip()
        self.sarvam_stt_model = e("SARVAM_STT_MODEL", "saaras:v3").strip()
        self.sarvam_tts_model = e("SARVAM_TTS_MODEL", "bulbul:v3").strip()
        # Limits that keep a small laptop happy.
        self.max_live_sessions = int(e("MAX_LIVE_SESSIONS", "5"))
        self.idle_timeout_sec = int(e("IDLE_TIMEOUT_SEC", "120"))


settings = Settings()

LANGUAGES = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}
LANG_CODES = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}
VOICES = ["anushka", "shubh", "kavitha", "mohit", "rupali", "rehan"]

# Placeholder plans. Edit freely: they only drive the usage meter and the billing screen.
PLANS = {
    "trial": {"label": "Free trial", "minutes": 100, "price_inr": 0},
    "starter": {"label": "Starter", "minutes": 500, "price_inr": 4999},
    "growth": {"label": "Growth", "minutes": 2000, "price_inr": 14999},
    "scale": {"label": "Scale", "minutes": 6000, "price_inr": 39999},
}
