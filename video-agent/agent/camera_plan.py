"""Camera moves for footage (your raw clips are no longer shown as-is): zoom in on a subject, then pan down/up/sideways while the narration moves on.

The planner can direct it per scene (`camera`: [{move, at_word, focus, seconds, scale}]), e.g. "zoom_in" on focus "top" at the first words, then "pan_down" on
the word where the testimonials start. Without directions every shot gets an automatic move of its own (zoom into the upper part, drift down, or the reverse),
restarted at each cut, so nothing sits still and nothing repeats twice in a row.

Moves resolve to {move, atSecond, seconds, focus?, scale?} in scene seconds; template/src/effects/camera.ts turns them into a smooth transform
(a focus point is kept centred and clamped so the picture always covers the frame: no black edges).
"""
from __future__ import annotations

import re

from .common import log

MOVES = ("zoom_in", "zoom_out", "pan_down", "pan_up", "pan_left", "pan_right", "reset")
FOCUS = {"top": [0.5, 0.25], "upper": [0.5, 0.35], "center": [0.5, 0.5], "lower": [0.5, 0.65], "bottom": [0.5, 0.75], "left": [0.3, 0.5], "right": [0.7, 0.5]}
DEFAULT_SCALE = 1.3
AUTO_STYLES = (("upper", "pan_down"), ("lower", "pan_up"), ("center", "pan_right"), ("upper", "pan_left"))


def _norm(w: str) -> str:
    return re.sub(r"[^\w]+", "", w.lower(), flags=re.UNICODE)


def plan_camera(scene: dict, words: list[dict], scene_seconds: float, shots: list[dict] | None, index: int, cfg: dict) -> list[dict]:
    ccfg = cfg.get("camera") or {}
    if not ccfg.get("enabled", True):
        return []
    scale = float(ccfg.get("scale", DEFAULT_SCALE))
    out: list[dict] = []
    for e in scene.get("camera") or []:
        move = e.get("move")
        if move not in MOVES:
            continue
        at = 0.0
        if e.get("at_word"):
            target = _norm(e["at_word"])
            hit = next((w for w in words if _norm(w["text"]) == target), None)
            if not hit:
                log(f"camera '{move}': word '{e['at_word']}' not found, skipped")
                continue
            at = hit["start"]
        seconds = 0.0 if move == "reset" else min(max(float(e.get("seconds") or 0.9), 0.3), 4.0)
        item = {"move": move, "atSecond": round(at, 3), "seconds": round(seconds, 3), "scale": float(e.get("scale") or scale)}
        if e.get("focus") in FOCUS:
            item["focus"] = FOCUS[e["focus"]]
        out.append(item)
    if out:
        return sorted(out, key=lambda m: m["atSecond"])
    # automatic: each shot gets a zoom into one area, then a drift while it plays
    spans, t = [], 0.0
    for s in (shots or [{"seconds": scene_seconds}]):
        spans.append((t, float(s["seconds"])))
        t += float(s["seconds"])
    for k, (start, length) in enumerate(spans):
        focus, drift = AUTO_STYLES[(index + k) % len(AUTO_STYLES)]
        if k > 0:
            out.append({"move": "reset", "atSecond": round(start, 3), "seconds": 0.0, "scale": scale})
        zoom = min(0.9, max(0.35, length * 0.4))
        out.append({"move": "zoom_in", "atSecond": round(start, 3), "seconds": round(zoom, 3), "scale": scale, "focus": FOCUS[focus]})
        if length > zoom + 0.8:
            out.append({"move": drift, "atSecond": round(start + zoom, 3), "seconds": round(length - zoom, 3), "scale": scale})
    return out
