"""Your own 16-sound pack (assets/sfx_custom, wav): every animation-style effect plays one of them, compulsory.

Each effect has two or three fitting sounds (from the pack's catalog tags); which one a reel gets rotates with the date, so over a few reels all 16 are used.
The sound starts at (moment on screen - its sync_at), so its peak lands on the moment. Heavy sounds (hits, risers, builds) are kept quiet because the reel is voice-led.
"""
from __future__ import annotations

import json
from datetime import date

from .common import ROOT

DIR = ROOT / "assets" / "sfx_custom"
EFFECT_SOUNDS = {
    "widgets": ("v2_pop_flip_shine", "v1_ding"),
    "bill": ("v1_paper",),
    "stamp": ("v1_cinematic_hit", "v2_low_hit"),
    "tier": ("v1_ding", "v2_pop"),
    "wall": ("v2_pop", "v2_pop_flip_shine"),
    "phonefan": ("v2_cinematic_whoosh",),
    "pullback": ("v1_riser", "v2_metallic_riser"),
    "countdown": ("v1_reverse_ticktock", "v2_counting"),
    "keyrain": ("v1_gear_metal",),
    "viewfinder": ("v2_camera_flash_shutter_combined", "v2_camera_flash"),
    "lockon": ("v2_glitch", "v1_ding"),
    "rabbit": ("v1_build_up", "v2_metallic_riser"),
    "giant": ("v1_cinematic_hit", "v2_glitch"),
    "collage": ("v2_low_hit", "v1_cinematic_hit"),
}
HEAVY = {"v1_cinematic_hit", "v2_low_hit", "v1_riser", "v2_metallic_riser", "v1_build_up", "v1_reverse_ticktock"}      # they can cover a voice: quieter
_cache: dict = {}


def load() -> dict:
    if "c" not in _cache:
        try:
            raw = json.loads((DIR / "catalog.json").read_text(encoding="utf-8"))["sounds"]
            _cache["c"] = {i: e for i, e in raw.items() if (DIR / f"{i}.wav").exists()}
        except Exception:
            _cache["c"] = {}
    return _cache["c"]


def all_ids() -> set:
    return {s for v in EFFECT_SOUNDS.values() for s in v}


def cues_for(built: dict, day: int | None = None) -> list[dict]:
    """The custom-sound cues of one built scene (agent/manifest.py `built` entry): one per effect, at the moment the effect lands."""
    g = built.get("graphic") or {}
    m = g.get("mock") or {}
    kind = m.get("type")
    if kind not in EFFECT_SOUNDS:
        return []
    cat = load()
    opts = [s for s in EFFECT_SOUNDS[kind] if s in cat]
    if not opts:
        return []
    day = date.today().toordinal() if day is None else day
    pick = opts[(day + sorted(EFFECT_SOUNDS).index(kind)) % len(opts)]
    t = g.get("times") or {}
    items = t.get("items") or []
    target = float(items[0] if kind in ("stamp", "lockon") and items else t.get("mock", 0.5))
    e = cat[pick]
    at = round(max(0.0, target - float(e.get("sync_at", 0.0))), 3)
    secs = float(built.get("narration_seconds", 0)) + 0.4
    if at >= secs - 0.15:
        return []
    return [{"src": f"assets/run/sfx/{pick}.wav", "atSecond": at, "volume": 0.2 if pick in HEAVY else 0.38, "type": "custom", "file": pick, "target": round(target, 3)}]


def add(built: list[dict], day: int | None = None) -> int:
    """Add the custom cues to every effect scene (in place), dropping a plain cue that would stack on the same moment. Returns how many were added."""
    n = 0
    for b in built:
        for c in cues_for(b, day):
            b["sfx"] = [x for x in b["sfx"] if abs(x["atSecond"] - c["atSecond"]) >= 0.25 or x.get("type") == "riser"]
            b["sfx"].append(c)
            b["sfx"].sort(key=lambda x: x["atSecond"])
            n += 1
    return n
