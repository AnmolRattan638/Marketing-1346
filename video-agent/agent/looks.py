"""A reel's LOOK: which caption style, colour theme and transition set it uses. Picked per run so videos differ, never one fixed style.

The pick is deterministic from the run seed (date + topic), and it avoids repeating the previous reel's caption style and theme
(remembered in state/last_look.json when the folder is writable). Force one with config.json -> looks.force, e.g. {"caption": "cinematic"}.
"""
from __future__ import annotations

import json
import os
from datetime import date

from .brand import load_palette
from .common import ROOT, log

CAPTIONS = ("pill", "cinematic", "karaoke", "stack", "typewriter")
TRANSITION_SETS = {
    "calm": ("settle", "zoom", "iris"),
    "energetic": ("whip", "glitch", "zoom", "circle"),
    "mixed": ("settle", "whip", "circle", "zoom"),
}
STATE = ROOT / "state" / "last_look.json"


def _mix(a: str, b: str, k: float) -> str:
    x, y = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(f"{round(int(x[i:i + 2], 16) * (1 - k) + int(y[i:i + 2], 16) * k):02X}" for i in (0, 2, 4))


def _rgba(h: str, a: float) -> str:
    h = h.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def palette_mode(mode: str, base: dict) -> dict:
    """The brand colours re-arranged (never a new hue): night = the website as is, ink = black + bright gold, royal = a brighter navy, paper = cream with dark gold and navy."""
    p = dict(base)
    gold, gold2, hot, navy, black = base["accent"], base["accent2"], base["hot"], base["bgBottom"], base["bgTop"]
    if mode == "ink":
        p.update(bgTop="#000000", bgBottom=_mix("#000000", navy, 0.35), card="#0A0A0A", cardEdge="#2A2A2A", ink="#000000", text="#FFFFFF", muted="#A8A8A8", accent=hot, accent2=gold)
    elif mode == "royal":
        royal = _mix(navy, "#2A4A8A", 0.45)
        p.update(bgTop=navy, bgBottom=royal, card=_mix(royal, "#000000", 0.25), cardEdge=_mix(royal, "#FFFFFF", 0.2), text="#F4F6FB", muted="#B6C0D6", accent=hot, accent2=gold)
    elif mode == "paper":
        cream = _mix(hot, "#FFFFFF", 0.72)
        deep = _mix(gold2, black, 0.42)
        p.update(bgTop=cream, bgBottom=_mix(cream, gold2, 0.22), card="#FFFFFF", cardEdge=_mix(cream, gold2, 0.5), ink=navy, text=navy, muted=_mix(navy, cream, 0.35), accent=deep, accent2=gold2, hot=deep, ok=deep)
    p["glow"], p["glowSoft"] = _rgba(p["accent"], 0.45), _rgba(p["accent"], 0.14)
    return p


# Eight art directions. Each changes the colour mode, the backdrop pattern, the caption style, the transition set and the template variant together, so two reels never share a look.
PRESETS = (
    dict(name="night-stack",      mode="night", bg="specks",  caption="stack",      transitions="calm",      variant="default",    vignette=0.38, direction="calm, elegant: big single headlines, one idea per scene, slow zooms"),
    dict(name="paper-editorial",  mode="paper", bg="dots",    caption="pill",       transitions="calm",      variant="minimal",    vignette=0.10, direction="editorial, light paper look: strike-through lists and checklists, quiet camera"),
    dict(name="ink-karaoke",      mode="ink",   bg="grid",    caption="karaoke",    transitions="energetic", variant="glass",      vignette=0.45, direction="high-contrast and fast: punch slides, step lists, hard zooms and whips"),
    dict(name="royal-cinematic",  mode="royal", bg="aurora",  caption="cinematic",  transitions="calm",      variant="neo",        vignette=0.30, direction="cinematic: slow push-ins, big titles, soft glow, few but strong visuals"),
    dict(name="night-rays",       mode="night", bg="rays",    caption="pill",       transitions="mixed",     variant="rounded",    vignette=0.40, direction="radiant: punch slides and stats first, bold emphasis on the number"),
    dict(name="ink-typewriter",   mode="ink",   bg="stripes", caption="typewriter", transitions="mixed",     variant="brutalist",  vignette=0.35, direction="raw and technical: terminal/checklist mocks, hard cuts, blunt headings"),
    dict(name="paper-pop",        mode="paper", bg="grid",    caption="pill",       transitions="energetic", variant="rounded",    vignette=0.08, direction="bright and playful: strike lists, chips, quick pops"),
    dict(name="royal-karaoke",    mode="royal", bg="dots",    caption="karaoke",    transitions="energetic", variant="glass",      vignette=0.34, direction="lively: step lists and stat reveals, rhythmic zooms"),
)


def _run_number() -> int:
    """GitHub's run counter when available (consecutive runs differ), else a local counter file."""
    try:
        return int(os.environ["GITHUB_RUN_NUMBER"])
    except (KeyError, ValueError):
        pass
    try:
        n = int(json.loads(STATE.read_text()).get("n", 0)) + 1
    except Exception:
        n = 0
    return n


def pick_look(seed: str, cfg: dict) -> dict:
    """Rotate through the presets by day + run number, so back-to-back reels never share a look (no history file needed in CI)."""
    lc = cfg.get("looks") or {}
    names = [p["name"] for p in PRESETS]
    forced = (lc.get("force") or {}).get("preset")
    n = _run_number()
    idx = names.index(forced) if forced in names else (date.today().toordinal() * 3 + n) % len(PRESETS)
    preset = dict(PRESETS[idx])
    preset.update({k: v for k, v in (lc.get("force") or {}).items() if k in ("caption", "transitions", "bg", "mode", "variant")})
    base = load_palette(cfg)
    look = {**preset, "palette": palette_mode(preset["mode"], base)}
    try:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps({"n": n, "preset": preset["name"]}))
    except OSError:
        pass
    log(f"look: preset {preset['name']} (captions={look['caption']}, colour={look['mode']}, backdrop={look['bg']}, transitions={look['transitions']}, templates={look['variant']})")
    return look


def pick_transition(scene: dict, index: int, look: dict, cfg: dict) -> str:
    """The planner's choice wins; otherwise cycle through this reel's transition set (never the same twice in a row, none on the first scene)."""
    if index == 0:
        return "settle"
    if scene.get("transition"):
        return scene["transition"]
    pool = TRANSITION_SETS.get(look.get("transitions"), TRANSITION_SETS["mixed"])
    return pool[(index - 1) % len(pool)]
