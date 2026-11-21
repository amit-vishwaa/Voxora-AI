"""Industry packs: JSON files in this folder. Add a new .json file and it appears in the app."""
import json
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_REQUIRED = ("key", "label", "record_type", "greeting", "fields", "closing", "scoring")


@lru_cache(maxsize=1)
def load_all() -> dict:
    packs = {}
    for f in sorted(_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        missing = [k for k in _REQUIRED if k not in data]
        if missing:
            raise ValueError(f"Pack {f.name} is missing: {', '.join(missing)}")
        packs[data["key"]] = data
    return packs


def get(key: str):
    return load_all().get(key)


def summaries() -> list:
    return [{"key": p["key"], "label": p["label"], "description": p.get("description", ""),
             "record_type": p["record_type"],
             "fields": [{"name": f["name"], "label": f["label"], "required": f.get("required", True)} for f in p["fields"]]}
            for p in load_all().values()]
