"""A reel's LOOK: which caption style, colour theme and transition set it uses. Picked per run so videos differ, never one fixed style.

The pick is deterministic from the run seed (date + topic), and it avoids repeating the previous reel's caption style and theme
(remembered in state/last_look.json when the folder is writable). Force one with config.json -> looks.force, e.g. {"caption": "cinematic"}.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from .common import ROOT, log

CAPTIONS = ("pill", "cinematic", "karaoke", "stack", "typewriter")
THEMES = ("ink", "sunset", "forest", "violet")
TRANSITION_SETS = {
    "calm": ("settle", "zoom", "iris"),
    "energetic": ("whip", "glitch", "zoom", "circle"),
    "mixed": ("settle", "whip", "circle", "zoom"),
}
STATE = ROOT / "state" / "last_look.json"


def _last() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def pick_look(seed: str, cfg: dict) -> dict:
    lc = cfg.get("looks") or {}
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    last = _last()
    caps = [c for c in lc.get("captions", CAPTIONS) if c in CAPTIONS] or list(CAPTIONS)
    themes = [t for t in lc.get("themes", THEMES) if t in THEMES] or list(THEMES)
    caps_ok = [c for c in caps if c != last.get("caption")] or caps
    themes_ok = [t for t in themes if t != last.get("theme")] or themes
    look = {"caption": rng.choice(caps_ok), "theme": rng.choice(themes_ok), "transitions": rng.choice(list(TRANSITION_SETS))}
    look.update({k: v for k, v in (lc.get("force") or {}).items() if k in look})
    try:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(look))
    except OSError:
        pass
    log(f"look: captions={look['caption']}, theme={look['theme']}, transitions={look['transitions']}")
    return look


def pick_transition(scene: dict, index: int, look: dict, cfg: dict) -> str:
    """The planner's choice wins; otherwise cycle through this reel's transition set (never the same twice in a row, none on the first scene)."""
    if index == 0:
        return "settle"
    if scene.get("transition"):
        return scene["transition"]
    pool = TRANSITION_SETS.get(look.get("transitions"), TRANSITION_SETS["mixed"])
    return pool[(index - 1) % len(pool)]
