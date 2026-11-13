"""Animation effects the planner asks for (adapted from the RVE remotion-templates pack, see template/src/effects/NOTICE.md).

A scene can carry `fx` (overlays and camera moves) and a `transition` (how the scene arrives). Each fx is anchored to a SPOKEN word
(`at_word`, the word's start from Whisper) so the graphic appears when it is said, and every fx also gets a matching SFX cue in sfx_plan.

  stat        big number counting up with a label            (stat-counter)      "73%" ... "of customers search online first"
  glitch      RGB-split title that settles                   (glitch-text)       a hook or a problem word
  title       spring-in title card                           (bounce-text)       a key phrase
  lower_third name/role bar sliding in                       (lower-third)       who is speaking / the brand
  shake       decaying camera shake on the footage           (camera-shake)      an impact word
  quote       a testimonial/quote whose words light up and get underlined as they are SPOKEN (QuoteUnderline)

Transitions (how a scene ARRIVES; the cut itself stays a hard cut so audio and captions never move):
  settle (default), whip (whip-pan landing), zoom (zoom-through arrival), iris (iris open), glitch (RGB-glitch flash), circle (colour circle wipe)
"""
from __future__ import annotations

import re

from .common import log

FX_TYPES = ("stat", "glitch", "title", "lower_third", "shake", "quote")
TRANSITIONS = ("settle", "whip", "zoom", "iris", "glitch", "circle")      # circle = a colour disc opens onto the scene
DEFAULT_SECONDS = {"stat": 2.4, "glitch": 1.4, "title": 1.9, "lower_third": 2.6, "shake": 0.7, "quote": 5.0}
SFX_FOR = {"stat": "pop", "glitch": "click", "title": "pop", "lower_third": "whoosh", "shake": "pop", "quote": "click"}
MIN_SECONDS = 0.5
MAX_SECONDS = 4.0
QUOTE_MAX_SECONDS = 9.0
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


def align_quote(text: str, words: list[dict], start_at: str | None) -> tuple[float, list[float], list[float]] | None:
    """Match the quote's words to the narration's (Whisper) words, in order. -> (first spoken second, per-word start, per-word end), the last two
    relative to the first. Words the narrator skipped or changed are spread between their neighbours. None when less than half match."""
    q = [w for w in text.split() if _norm(w)]
    if not q or not words:
        return None
    i0 = 0
    if start_at:
        i0 = next((i for i, w in enumerate(words) if _norm(w["text"]) == _norm(start_at)), 0)
    times: list[tuple[float, float] | None] = []
    j = i0
    for qw in q:
        reach = len(words) if not any(times) else j + 5          # the first word may come after a spoken intro; the rest must follow closely
        hit = next((k for k in range(j, min(len(words), reach)) if _norm(words[k]["text"]) == _norm(qw)), None)
        if hit is None:
            times.append(None)
        else:
            times.append((words[hit]["start"], words[hit]["end"]))
            j = hit + 1
    if sum(t is not None for t in times) < len(q) / 2:
        return None
    known = [i for i, t in enumerate(times) if t]
    for a, b in zip(known, known[1:]):                       # fill gaps evenly
        for k in range(a + 1, b):
            f = (k - a) / (b - a)
            times[k] = (times[a][0] + (times[b][0] - times[a][0]) * f, times[a][0] + (times[b][0] - times[a][0]) * f + 0.2)
    for k in range(known[0] - 1, -1, -1):
        times[k] = (times[k + 1][0] - 0.2, times[k + 1][0])
    for k in range(known[-1] + 1, len(q)):
        times[k] = (times[k - 1][1], times[k - 1][1] + 0.2)
    first = times[0][0]
    return first, [round(t[0] - first, 3) for t in times], [round(t[1] - first, 3) for t in times]


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
        if kind == "quote":
            text = (e.get("text") or "").strip()
            al = align_quote(text, words, e.get("at_word")) if text else None
            if not al:
                log("fx 'quote': its words are not in the narration, skipped")
                continue                  # an underline that does not follow the voice is worse than none
            first, starts, ends = al
            at = max(0.0, first - 0.12)
            seconds = min(max(ends[-1] + 0.12 + 0.9, 1.5), QUOTE_MAX_SECONDS, scene_seconds - at - 0.05)
            if any(o["type"] != "shake" and at < o["atSecond"] + o["seconds"] and o["atSecond"] < at + seconds for o in out):
                log("fx 'quote' overlaps another graphic, skipped")
                continue
            out.append({"type": "quote", "atSecond": round(at, 3), "seconds": round(seconds, 3), "text": text, "label": e.get("label", ""),
                        "wordTimes": [round(x + (first - at), 3) for x in starts], "wordEnds": [round(x + (first - at), 3) for x in ends]})
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
