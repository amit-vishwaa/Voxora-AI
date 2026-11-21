from fastapi import APIRouter, Depends

from .. import packs
from ..config import LANGUAGES, PLANS, VOICES, settings
from ..deps import current_user
from ..providers import registry

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health():
    return {"ok": True, "app": settings.app_name}


@router.get("/meta/packs")
def list_packs(user=Depends(current_user)):
    return packs.summaries()


@router.get("/meta/config")
def config(user=Depends(current_user)):
    return {"languages": LANGUAGES, "voices": VOICES, "providers": registry.status(),
            "stt": "sarvam" if registry.get_stt() and registry.get_stt().name == "sarvam" else "browser",
            "tts": "sarvam" if registry.get_tts() and registry.get_tts().name == "sarvam" else "browser",
            "plans": [{**v, "key": k} for k, v in PLANS.items()]}
