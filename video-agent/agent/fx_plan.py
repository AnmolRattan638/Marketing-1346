"""Animation effects the planner asks for (adapted from the RVE remotion-templates pack, see template/src/effects/NOTICE.md).

A scene can carry `fx` (overlays and camera moves) and a `transition` (how the scene arrives). Each fx is anchored to a SPOKEN word
(`at_word`, the word's start from Whisper) so the graphic appears when it is said, and every fx also gets a matching SFX cue in sfx_plan.

  stat        big number counting up with a label            (stat-counter)      "73%" ... "of customers search online first"
  glitch      RGB-split title that settles                   (glitch-text)       a hook or a problem word
  title       spring-in title card                           (bounce-text)       a key phrase
  lower_third name/role bar sliding in                       (lower-third)       who is speaking / the brand
  shake       decaying camera shake on the footage           (camera-shake)      an impact word

Transitions (how a scene ARRIVES; the cut itself stays a hard cut so audio and captions never move):
  settle (default), whip (whip-pan landing), zoom (zoom-through arrival), iris (iris open), glitch (RGB-glitch flash)
"""
from __future__ import annotations

import re

from .common import log

FX_TYPES = ("stat", "glitch", "title", "lower_third", "shake")
TRANSITIONS = ("settle", "whip", "zoom", "iris", "glitch")
DEFAULT_SECONDS = {"stat": 2.4, "glitch": 1.4, "title": 1.9, "lower_third": 2.6, "shake": 0.7}
SFX_FOR = {"stat": "pop", "glitch": "click", "title": "pop", "lower_third": "whoosh", "shake": "pop"}
MIN_SECONDS = 0.5
MAX_SECONDS = 4.0
START_AT = 0.15           # no word given: shortly after the scene starts
PARAMS = ("text", "label", "value", "prefix", "suffix")


def _norm(w: str) -> str:
    return re.sub(r"[^\w]+", "", w.lower(), flags=re.UNICODE)


def resolve_transition(scene: dict, index: int, cfg: dict) -> str:
    """How the scene arrives. The first scene has nothing to arrive from."""
    kind = scene.get("transition") or (cfg.get("fx") or {}).get("default_transition", "settle")
    if index == 0 or kind not in TRANSITIONS:
        return "settle"
    return kind


def plan_fx(scene: dict, words: list[dict], scene_seconds: float, cfg: dict) -> list[dict]:
    """Resolve the planner's fx hints to manifest entries: {type, atSecond, seconds, ...params}. Drops what cannot be placed honestly."""
    fcfg = cfg.get("fx") or {}
    if not fcfg.get("enabled", True):
        return []
    out: list[dict] = []
    for e in scene.get("fx", []):
        if len(out) >= fcfg.get("max_per_scene", 2):
            break
        kind = e.get("type")
        if kind not in FX_TYPES:
            continue
        if e.get("at_word"):
            target = _norm(e["at_word"])
            hit = next((w for w in words if _norm(w["text"]) == target), None)
            if not hit:
                log(f"fx '{kind}': word '{e['at_word']}' not found, skipped")
                continue          # a graphic at the wrong moment is worse than none
            at = hit["start"]
        else:
            at = START_AT
        seconds = min(max(float(e.get("seconds") or DEFAULT_SECONDS[kind]), MIN_SECONDS), MAX_SECONDS)
        seconds = min(seconds, scene_seconds - at - 0.1)           # stays inside its scene
        if seconds < MIN_SECONDS:
            log(f"fx '{kind}' at {at:.2f}s does not fit the scene, skipped")
            continue
        if kind != "shake" and any(o["type"] != "shake" and at < o["atSecond"] + o["seconds"] and o["atSecond"] < at + seconds for o in out):
            log(f"fx '{kind}' overlaps another graphic, skipped")
            continue          # one graphic on screen at a time; captions stay readable
        item = {"type": kind, "atSecond": round(at, 3), "seconds": round(seconds, 3)}
        item.update({k: e[k] for k in PARAMS if e.get(k) not in (None, "")})
        out.append(item)
    return out
