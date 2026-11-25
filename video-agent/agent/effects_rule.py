"""The compulsory style rule: every reel uses several DIFFERENT animation styles and several DIFFERENT caption styles.

  animation styles  the 14 effect mock-ups (graphics.EFFECTS: widgets, bill, stamp, tier, wall, phonefan, pullback, countdown, keyrain, viewfinder,
                    lockon, rabbit, giant, collage). At least MIN_EFFECTS different ones per reel, never the same one in two neighbouring scenes.
  caption styles    at least MIN_CAPTIONS different ones per reel, never the same style in two neighbouring scenes.

`enforce` repairs a plan that falls short (the planner is a language model and forgets): it upgrades scenes with a text-only effect built from the
scene's own words, never touching the hook, the call to action or the before/after and demo scenes. `check` reports what is still wrong.
"""
from __future__ import annotations

import random
import re

from .graphics import EFFECTS

MIN_EFFECTS = 4
MIN_CAPTIONS = 3
MAX_GRAPHIC_SHARE = 0.75          # never turn more than this share of a reel's scenes into graphics: the presenter and footage still carry the reel
TEXT_EFFECTS = ("giant", "lockon", "viewfinder", "rabbit", "collage", "pullback")      # effects that need only a word or a line: safe to build from any scene
CLASSIC_CAPTIONS = ("pill", "karaoke", "stack", "cinematic", "typewriter")            # what a graphic scene can show (it has its own heading)
PLACED_CAPTIONS = ("hierarchy", "glass", "bounce", "neon", "giant", "smoke", "depth", "outline", "retro", "explode")      # the placed reference styles: footage scenes


def effect_of(scene: dict) -> str | None:
    m = (scene.get("graphic") or {}).get("mock")
    t = m.get("type") if isinstance(m, dict) else None
    return t if t in EFFECTS else None


def check(scenes: list[dict]) -> list[str]:
    """What is wrong with the reel's animation styles; empty = fine."""
    used = [effect_of(s) for s in scenes]
    out = []
    n = len({u for u in used if u})
    if n < MIN_EFFECTS:
        out.append(f"only {n} different animation style(s), the reel needs {MIN_EFFECTS}")
    if any(a and a == b for a, b in zip(used, used[1:])):
        out.append("the same animation style in two scenes in a row")
    return out


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_][\w'-]*", text or "", flags=re.UNICODE)


def _key(scene: dict) -> str:
    h = str((scene.get("graphic") or {}).get("heading") or "").strip()
    if h:
        return h[:30]
    ws = [w for w in _words(scene.get("narration", "")) if len(w) >= 4]
    return (max(ws, key=len) if ws else "WATCH").upper()[:30]


def _items(effect: str, scene: dict) -> list[str]:
    key = _key(scene)
    first = key.split()[0]
    last = (_words(scene.get("narration", "")) or [first])[-1]
    return {
        "giant": [first.upper(), last.lower()],
        "lockon": [first.upper()],
        "viewfinder": [key],
        "rabbit": [first.lower()],
        "collage": [first.upper(), key.upper()],
        "pullback": [key],
    }[effect]


def enforce(scenes: list[dict], protect: set[int] | None = None, seed: str = "") -> list[str]:
    """Upgrade scenes in place until the reel has MIN_EFFECTS different effects and no neighbours alike. Returns the notes of what changed."""
    notes: list[str] = []
    protect = set(protect or ()) | {0, len(scenes) - 1}
    rng = random.Random(seed)
    graphic_n = sum(1 for s in scenes if s.get("graphic"))
    cap = int(len(scenes) * MAX_GRAPHIC_SHARE)

    def free(i: int) -> bool:
        return i not in protect and effect_of(scenes[i]) is None

    def clash(i: int, e: str) -> bool:
        return any(0 <= j < len(scenes) and effect_of(scenes[j]) == e for j in (i - 1, i + 1))

    pool = list(TEXT_EFFECTS)
    rng.shuffle(pool)
    while len({effect_of(s) for s in scenes} - {None}) < MIN_EFFECTS:
        have = {effect_of(s) for s in scenes}
        want = [e for e in pool if e not in have]
        # graphic scenes first (they already are pictures), then footage scenes, the middle of the reel before the edges
        order = sorted((i for i in range(len(scenes)) if free(i)), key=lambda i: (not scenes[i].get("graphic"), abs(i - len(scenes) / 2)))
        spot = next(((i, e) for i in order for e in want if not clash(i, e) and (scenes[i].get("graphic") or graphic_n < cap)), None)
        if not spot:
            notes.append("not enough free scenes to reach the animation-style minimum")
            break
        i, e = spot
        sc = scenes[i]
        if not sc.get("graphic"):
            graphic_n += 1
        g = dict(sc.get("graphic") or {})
        g.update({"layout": "step", "heading": g.get("heading") or _key(sc), "mock": {"type": e, "title": "", "items": _items(e, sc)}})
        sc["graphic"] = g
        notes.append(f"scene {i + 1}: animation style '{e}' added")
    for i in range(1, len(scenes)):            # neighbours alike: swap the later one to an unused text effect
        a, b = effect_of(scenes[i - 1]), effect_of(scenes[i])
        if a and a == b and i not in protect:
            used = {effect_of(s) for s in scenes}
            alt = next((e for e in TEXT_EFFECTS if e not in used and e != a), None)
            if alt:
                scenes[i]["graphic"]["mock"] = {"type": alt, "title": "", "items": _items(alt, scenes[i])}
                notes.append(f"scene {i + 1}: '{b}' changed to '{alt}' (it repeated the scene before)")
    return notes


def caption_plan(graphic: list[bool], look_caption: str, seed: str = "") -> list[str]:
    """One caption style per scene: at least MIN_CAPTIONS different in the reel, never the same in two scenes in a row. Graphic scenes can only show the classic styles
    (their own heading is the picture), footage scenes the placed reference styles; the reel's own look is used first."""
    rng = random.Random(seed)
    used: dict[str, int] = {}
    out: list[str] = []
    placed = list(PLACED_CAPTIONS)
    rng.shuffle(placed)
    for i, g in enumerate(graphic):
        pool = list(CLASSIC_CAPTIONS if g else placed)
        if look_caption in pool and look_caption not in used:
            pick = look_caption
        else:
            fresh = [c for c in pool if c != (out[-1] if out else None)]
            low = min(used.get(c, 0) for c in fresh)
            pick = next(c for c in fresh if used.get(c, 0) == low)
        used[pick] = used.get(pick, 0) + 1
        out.append(pick)
    # a reel made of few scenes can still fall short of the minimum: re-style from the other pool until it has enough
    guard = 0
    while len(set(out)) < min(MIN_CAPTIONS, len(out)) and guard < 20:
        guard += 1
        i = next(k for k in range(len(out)) if list(out).count(out[k]) > 1)
        pool = [c for c in (CLASSIC_CAPTIONS if graphic[i] else placed) if c not in out and c not in (out[i - 1] if i else "", out[i + 1] if i + 1 < len(out) else "")]
        if not pool:
            break
        out[i] = pool[0]
    return out
