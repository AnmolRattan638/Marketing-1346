"""Real proof: blurred screenshots of real WhatsApp messages sent to local businesses as a mystery customer (assets/proof/index.json).

A proof may only claim what the screenshot shows: sent on a date, delivered, no reply as of the day it was checked. It is used only while that check is recent
(MAX_AGE_DAYS); once a business replies, delete its entry. Names, numbers and photos in the images are blurred before they enter the repo."""
from __future__ import annotations

import json
import shutil
from datetime import date, datetime

from .common import ROOT, WORK, log

DIR = ROOT / "assets" / "proof"
MAX_AGE_DAYS = 45


def _load() -> list[dict]:
    try:
        return json.loads((DIR / "index.json").read_text()).get("proofs", [])
    except (OSError, ValueError):
        return []


def entry(pid: str, today: date | None = None) -> dict | None:
    """The proof with this id (or the first one of this business type) if its image exists and its check is recent; else None."""
    today = today or date.today()
    pid = str(pid or "").strip().lower()
    for p in _load():
        if pid in (p.get("id"), p.get("business_type")) and (DIR / p.get("file", "")).exists():
            try:
                age = (today - datetime.strptime(p["checked"], "%Y-%m-%d").date()).days
            except (KeyError, ValueError):
                continue
            if 0 <= age <= MAX_AGE_DAYS and "no reply" in str(p.get("status", "")):
                return p
    return None


def _d(s: str) -> str:
    return datetime.strptime(s, "%Y-%m-%d").strftime("%-d %b")


def tag(p: dict) -> str:
    """The only claim the card makes: when it was sent and when it was last checked."""
    return f"REAL · sent {_d(p['sent'])}, {p['sent_time']} · no reply by {_d(p['checked'])}"


def stage(pid: str) -> str:
    """Copy the image next to the reel's other assets; returns the path the template loads."""
    p = entry(pid)
    if not p:
        raise KeyError(pid)
    (WORK / "proof").mkdir(parents=True, exist_ok=True)
    shutil.copy(DIR / p["file"], WORK / "proof" / p["file"])
    return f"assets/run/proof/{p['file']}"


def props(pid: str) -> dict | None:
    p = entry(pid)
    if not p:
        log(f"proof '{pid}' is missing or its check is older than {MAX_AGE_DAYS} days, not used")
        return None
    w, h = p.get("size", [720, 560])
    return {"id": p["id"], "tag": tag(p), "src": f"assets/run/proof/{p['file']}", "ratio": round(h / w, 4)}
