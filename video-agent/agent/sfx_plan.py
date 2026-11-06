"""Turn the plan's SFX hints plus word timings into cues for the Remotion manifest.

Function-first, as in claude-youtube-editor's suggest-sfx: whoosh = motion at a cut,
riser = tension building to a word, pop = emphasis on a word, click = small snap.
"""
from __future__ import annotations

import re

from .common import log

# Starting levels. Short-form narration is near-continuous and masks quiet effects,
# so these lean loud-ish. Tune by ear.
VOLUMES = {"whoosh": 0.55, "pop": 0.7, "riser": 0.5, "click": 0.6}
RISER_SECONDS = 1.4  # riser clips end on the word they build toward
MIN_GAP = 0.25
MAX_PER_SCENE = 3


def _norm(w: str) -> str:
    return re.sub(r"[^\w]+", "", w.lower(), flags=re.UNICODE)


def plan_sfx(index: int, scene: dict, words: list[dict], available: set) -> list[dict]:
    raw: list[tuple[str, float]] = []
    if index > 0 and "whoosh" in available:
        raw.append(("whoosh", 0.0))  # the cut into this scene

    for e in scene.get("sfx", []):
        kind = e.get("type")
        if kind not in available:
            continue
        if e.get("at") == "cut":
            raw.append((kind, 0.0))
            continue
        target = _norm(e.get("at_word", ""))
        hit = next((w for w in words if _norm(w["text"]) == target), None) if target else None
        if not hit:
            log(f"sfx '{kind}': word '{e.get('at_word')}' not found, skipped")
            continue
        at = max(0.0, hit["start"] - RISER_SECONDS) if kind == "riser" else hit["start"]
        raw.append((kind, at))

    cues, last = [], -9.0
    for kind, at in sorted(raw, key=lambda x: x[1]):
        if at - last < MIN_GAP or len(cues) >= MAX_PER_SCENE:
            continue
        cues.append({"src": f"assets/run/sfx/{kind}.mp3", "atSecond": round(at, 2),
                     "volume": VOLUMES[kind], "type": kind})
        last = at
    return cues
