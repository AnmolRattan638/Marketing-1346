"""Turn the plan's SFX hints, the word timings and the real shot cuts into cues for the Remotion manifest.

Function-first, as in claude-youtube-editor's suggest-sfx: whoosh = motion at a cut, riser = tension building to a word,
pop = emphasis on a word, click = small snap.

Everything is placed from times that exist in the edit, never "roughly near":
  - a pop/riser lands on the first sound of its word (Whisper word start);
  - a riser starts RISER_SECONDS earlier so it ends on that word;
  - a whoosh starts LEAD seconds BEFORE the cut it belongs to, so the swell peaks on the cut;
  - cutaways to B-roll (stock/photo) get a quiet whoosh, the return to your own footage a click; dissolves get nothing.
When cues compete for the same moment the important ones win: planner hints first, then the scene's opening whoosh, then cut sounds.
"""
from __future__ import annotations

import random
import re

from .common import log
from .fx_plan import SFX_FOR as fx_sfx

# Starting levels. Short-form narration is near-continuous and masks quiet effects,
# so these lean loud-ish. Tune by ear.
VOLUMES = {"whoosh": 0.55, "pop": 0.7, "riser": 0.5, "click": 0.6, "impact": 0.6}
CUT_VOLUMES = {"whoosh": 0.32, "click": 0.38}      # sounds on shot cuts stay under the voice and the planner's own effects
RISER_SECONDS = 1.4        # riser clips end on the word they build toward
LEAD = {"whoosh": 0.2, "riser": 0.0, "pop": 0.0, "click": 0.0, "impact": 0.0}   # seconds a cue starts before its anchor; a whoosh swells for ~0.3 s, so its peak lands on the cut
MIN_GAP = 0.3
MAX_PER_SCENE = 3          # fewer, better placed sounds; a sound on every cut and every scene felt like noise
POLICY = {"cut_sounds": False, "scene_whoosh": "wipes", "max_per_scene": MAX_PER_SCENE}
# cut_sounds: whoosh/click on the shot cuts inside a footage scene. scene_whoosh: "wipes" = only when the scene arrives with a visible
# transition (whip, zoom, iris, glitch, circle), "always" = every scene start, "never".


# ---- variety: which FILE plays each cue ----------------------------------------------------------------------------------------------------------
# plan_sfx decides WHAT and WHEN (a kind: whoosh, pop, click, riser, impact). assign_files() then gives every cue of the whole reel a concrete file from the
# kind's family, always the least-used one, never the same file twice in a row, and never one file more than MAX_USES times in the reel.
FAMILIES = {
    "whoosh": ("whoosh", "swipe"),
    "pop": ("pop", "boop", "ding", "sparkle"),
    "click": ("click", "tick"),
    "riser": ("riser",),
    "impact": ("impact",),
}
MAX_USES = 3


def stem_kind(stem: str) -> str:
    return re.sub(r"_\d+$", "", stem)


def kinds_available(stems: set) -> set:
    """The cue kinds the plan can ask for, given the files on disk (whoosh_3.mp3 counts for 'whoosh'; an old single whoosh.mp3 still works)."""
    bases = {stem_kind(s) for s in stems}
    return {k for k, fam in FAMILIES.items() if bases & set(fam)} | bases


def assign_files(scenes_cues: list[list[dict]], stems: set, seed: str = "", max_uses: int = MAX_USES) -> None:
    """Set cue['file'] (a stem, e.g. 'whoosh_4') on every cue, in playing order across the reel. Cues that cannot get a file within the cap are removed."""
    rng = random.Random(seed)
    uses: dict[str, int] = {}
    last: str | None = None
    for cues in scenes_cues:
        for c in list(sorted(cues, key=lambda c: c["atSecond"])):
            fam = FAMILIES.get(c["type"], (c["type"],))
            pool = sorted(s for s in stems if stem_kind(s) in fam and uses.get(s, 0) < max_uses)
            if not pool:
                log(f"sfx '{c['type']}' at {c['atSecond']:.2f}s dropped: every file of its family already played {max_uses} times")
                cues.remove(c)
                continue
            fresh = [s for s in pool if s != last] or pool
            low = min(uses.get(s, 0) for s in fresh)
            pick = rng.choice([s for s in fresh if uses.get(s, 0) == low])
            uses[pick] = uses.get(pick, 0) + 1
            last = pick
            c["file"] = pick
            c["src"] = f"assets/run/sfx/{pick}.mp3"


def _norm(w: str) -> str:
    return re.sub(r"[^\w]+", "", w.lower(), flags=re.UNICODE)


def emphasis_beats(scene: dict, words: list[dict]) -> list[tuple[str, float]]:
    """The planner's emphasis words ((word, start second) pairs) that exist in the narration. Used for pops, risers, caption emphasis and the zoom pulse."""
    out = []
    for e in scene.get("sfx", []):
        if e.get("type") in ("pop", "riser") and e.get("at") != "cut":
            target = _norm(e.get("at_word", ""))
            hit = next((w for w in words if _norm(w["text"]) == target), None) if target else None
            if hit:
                out.append((hit["text"], hit["start"]))
    return out


def plan_sfx(index: int, scene: dict, words: list[dict], available: set, cuts: list[dict] | None = None, fx: list[dict] | None = None,
             transition: str = "settle", graphic_cues: list[dict] | None = None, policy: dict | None = None) -> list[dict]:
    pol = {**POLICY, **(policy or {})}
    cands: list[tuple[int, str, float, float]] = []      # (priority, kind, anchor second, volume); lower priority number wins
    for gc in graphic_cues or []:                         # the soft UI sounds of a motion-graphic scene (agent/graphics.py)
        if gc["type"] in available:
            cands.append((0, gc["type"], gc["atSecond"], gc["volume"]))

    for e in scene.get("sfx", []):
        kind = e.get("type")
        if kind not in available:
            continue
        if e.get("at") == "cut":
            cands.append((0, kind, 0.0, VOLUMES[kind]))
            continue
        target = _norm(e.get("at_word", ""))
        hit = next((w for w in words if _norm(w["text"]) == target), None) if target else None
        if not hit:
            log(f"sfx '{kind}': word '{e.get('at_word')}' not found, skipped")
            continue
        anchor = hit["start"] - RISER_SECONDS if kind == "riser" else hit["start"]
        cands.append((0, kind, max(0.0, anchor), VOLUMES[kind]))

    for f in fx or []:                      # a graphic appears WITH its sound (agent/fx_plan.py SFX_FOR)
        kind = fx_sfx.get(f["type"])
        if kind in available:
            cands.append((0, kind, f["atSecond"], VOLUMES[kind]))

    if index > 0 and "whoosh" in available and (pol["scene_whoosh"] == "always" or (pol["scene_whoosh"] == "wipes" and transition != "settle")):
        cands.append((1, "whoosh", 0.0, VOLUMES["whoosh"]))      # the scene arrives with a visible wipe, so it gets its sound

    for c in (cuts or []) if pol["cut_sounds"] else []:
        if c.get("kind") != "cut":
            continue          # a dissolve is its own transition and needs no sound
        kind = "whoosh" if c.get("type") in ("stock", "photo") else "click"
        if kind in available:
            cands.append((2, kind, float(c["at"]), CUT_VOLUMES[kind]))

    cues: list[dict] = []
    for _, kind, anchor, vol in sorted(cands, key=lambda c: (c[0], c[2])):
        at = max(0.0, anchor - LEAD[kind])
        # transients (pop, click, whoosh) must not stack; a riser starts as a near-silent fade-in, so it may overlap them
        if len(cues) >= pol["max_per_scene"] or (kind != "riser" and any(abs(at - c["atSecond"]) < MIN_GAP for c in cues if c["type"] != "riser")):
            continue
        cues.append({"src": f"assets/run/sfx/{kind}.mp3", "atSecond": round(at, 3), "volume": vol, "type": kind})
    return sorted(cues, key=lambda c: c["atSecond"])
