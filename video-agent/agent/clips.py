"""The presenter's clip library. You shoot a few short clips of the masked character (see the shoot guide), named  type_angle_take.mp4  (explain_F_01.mp4, pointr_L_02.mp4 ...).
This module reads them, cuts each into ~3 s slots (no files are cut: the renderer plays a slot straight from the source), and lays slots under the reel so that

* the clip type matches what is being said (a question gets the head-tilt clip, a call to action the point-down clip, a pain point the serious clip ...),
* a slot is never used twice in one reel, and the same source clip is never used on two cuts in a row,
* the angle alternates (front / left / right) and every cut has its own zoom and a small speed change, so it reads as an editor's jump cut.

The clips are private: they are read from a private checkout (assets/avatar-private, fetched by the workflow with a token) or, for local tests, assets/avatar/clips."""
from __future__ import annotations

import random
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .common import ROOT, WORK

SLOT = 3.2          # seconds of source per slot
EDGE = 0.3          # the first / last moments of a clip are the rest pose: never used as a cut point
ZOOMS = (1.0, 1.14, 1.28)
RATES = (0.95, 1.0, 1.05)
TYPES = ("explain", "question", "excited", "pointr", "pointl", "pointdown", "leanin", "pain", "agree", "count", "hook", "but", "idle")
ACTION = {"question", "excited", "pointr", "pointl", "pointdown", "leanin", "pain", "agree", "count", "hook", "but"}   # the gesture is in the middle of the clip
FALLBACK = {"pointl": ("pointr",), "pointr": ("pointl",), "hook": ("excited", "leanin"), "count": ("agree", "explain"), "but": ("question", "explain"), "pain": ("leanin", "explain"),
            "agree": ("explain",), "excited": ("explain",), "leanin": ("explain",), "question": ("explain",), "pointdown": ("pointr", "explain"), "idle": ("explain",), "explain": ("idle",)}
NAME = re.compile(r"^(?P<type>[a-z]+)_(?P<angle>[FLR])_(?P<take>\d+)\.mp4$", re.I)


@dataclass(frozen=True)
class Clip:
    path: Path
    type: str
    angle: str
    take: int
    seconds: float

    @property
    def name(self) -> str:
        return self.path.name


def folder() -> Path | None:
    """Where the clips are: the private checkout first, then a local folder (tests, or a machine that has them)."""
    for p in (ROOT / "assets" / "avatar-private" / "clips", ROOT / "assets" / "avatar-private", ROOT / "assets" / "avatar" / "clips"):
        if p.is_dir() and any(NAME.match(x.name) for x in p.glob("*.mp4")):
            return p
    return None


def _seconds(p: Path) -> float:
    try:
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True, timeout=30).stdout.strip())
    except Exception:
        return 0.0


def library() -> list[Clip]:
    f = folder()
    out = []
    for p in sorted(f.glob("*.mp4")) if f else []:
        m = NAME.match(p.name)
        if not m or m["type"].lower() not in TYPES:
            continue
        s = _seconds(p)
        if s >= SLOT / 2 + 2 * EDGE:
            out.append(Clip(p, m["type"].lower(), m["angle"].upper(), int(m["take"]), s))
    return out


def slots(c: Clip) -> list[float]:
    """Start seconds of the slots inside a clip, never in the rest pose at either end. Gesture clips: the middle slot comes first (the gesture is there)."""
    n = max(1, int((c.seconds - 2 * EDGE) // SLOT))
    s = [round(EDGE + k * ((c.seconds - 2 * EDGE - SLOT) / max(1, n - 1) if n > 1 else 0), 2) for k in range(n)]
    s = [min(x, max(0.0, c.seconds - SLOT - 0.05)) for x in s]
    if c.type in ACTION and n > 1:
        mid = n // 2
        s = [s[mid]] + [x for i, x in enumerate(s) if i != mid]
    return s


# what is said -> which clip. Order matters: the first rule that matches and has clips wins.
RULES = [
    ("question", re.compile(r"\?\s*$|^\s*(kya|kyun|kyu|kaise|kab|kaun|kitn\w+|क्या|क्यों|कैसे)\b|did you know|pata hai", re.I)),
    ("count", re.compile(r"\b(step\s*\d|steps?|three|teen|3|2|two|do|1|ek|pehla|doosra|teesra|first|second|third)\b.*\b(things?|steps?|tarike|cheezein|reasons?|points?|baatein)\b|\b\d\s*(things|steps|tarike|reasons)\b", re.I)),
    ("but", re.compile(r"\b(but|lekin|magar|par|however|asli|sach ye|sach yeh|truth|asal mein|asal me)\b", re.I)),
    ("pain", re.compile(r"\b(nahi|nuksan|loss|miss|problem|dikkat|waste|barbad|kho|gaya|lose|losing|ignore|bhool|mushkil|thak)\w*", re.I)),
    ("leanin", re.compile(r"\b(secret|raaz|rahasya|yaad rakh|sabse zaroori|important|dhyan|ek baat|most people|zyada log)\b", re.I)),
    ("agree", re.compile(r"\b(proof|result|study|research|data|case study|exactly|bilkul|sach|tested|verified)\b", re.I)),
    ("excited", re.compile(r"\b(free|double|10x|\d+\s*(x|percent|%)|zyada|badh|boost|grow|jackpot|mazaa|kamaal)\b", re.I)),
]
FULL = ("chat", "site", "ba", "tpl", "avatar", "hook")      # a picture fills the screen: the presenter shrinks / hides


def intent(text: str, i: int, n: int, layout: str | None, have: set[str]) -> str:
    """The clip type for one scene (the first cut of it). Later cuts of a long scene alternate explain / idle."""
    want = "explain"
    t = text or ""
    if i == n - 1 or re.search(r"\bcomment\b|कमेंट|comment mein|dm mein", t, re.I):
        want = "pointdown"
    elif i == 0:
        want = "hook"
    else:
        for typ, rx in RULES:
            if typ in have and rx.search(t):
                want = typ
                break
        else:
            if layout in ("step", "strike") and "pointr" in have:
                want = "pointr"
            elif layout in FULL and "idle" in have:
                want = "idle"
    for cand in (want, *FALLBACK.get(want, ()), "explain", "idle"):
        if cand in have:
            return cand
    return next(iter(have)) if have else "explain"


def plan(texts: list[str], layouts: list[str | None], frames: list[int], fps: int, lib: list[Clip], seed: str = "") -> list[dict]:
    """Cuts for the whole reel: [{f, n, src, from, rate, zoom, angle, type, frame}] in global frames. Pure and deterministic for a given seed (the date by default)."""
    if not lib:
        return []
    rng = random.Random(seed or date.today().isoformat())
    by: dict[str, list[Clip]] = {}
    for c in lib:
        by.setdefault(c.type, []).append(c)
    have = set(by)
    used: set[tuple[str, float]] = set()
    uses: dict[tuple[str, float], int] = {}
    last_clip, last_angle, zi = "", "", rng.randrange(3)
    cuts: list[dict] = []
    start = 0
    for i, (text, lay, fr) in enumerate(zip(texts, layouts, frames)):
        secs = fr / fps
        n_cuts = max(1, -(-int(secs * 10) // 30))              # ceil(secs / 3.0)
        if i == len(texts) - 1 and secs <= 4.6:
            n_cuts = 1                                          # the call to action is one clean point-down cut
        want = intent(text, i, len(texts), lay, have)
        for k in range(n_cuts):
            typ = want if (k == 0 and want != "pointdown") or (k == n_cuts - 1 and want == "pointdown") else rng.choice([t for t in ("explain", "explain", "idle") if t in have] or [want])
            pool = [c for c in by.get(typ, []) if c.name != last_clip] or by.get(typ, []) or lib
            pool_slots = [(c, s) for c in pool for s in slots(c)]
            fresh = [(c, s) for c, s in pool_slots if (c.name, s) not in used]
            if not fresh:                                       # every slot of the type is spent in this reel: reuse the least used one (a new zoom and speed hide it)
                fresh = sorted(pool_slots, key=lambda cs: uses.get((cs[0].name, cs[1]), 0))[:3]
            diff = [(c, s) for c, s in fresh if c.angle != last_angle] or fresh   # alternate the angle
            if typ in ACTION:
                diff.sort(key=lambda cs: slots(cs[0]).index(cs[1]))                # the gesture slot first
                c, s = diff[0]
            else:
                c, s = rng.choice(diff)
            length = min(secs / n_cuts, SLOT / 0.95)
            rate = min(rng.choice(RATES), SLOT / max(length, 0.1))
            zi = (zi + rng.choice((1, 2))) % 3
            f0 = start + int(k * fr / n_cuts)
            f1 = start + int((k + 1) * fr / n_cuts) if k < n_cuts - 1 else start + fr
            used.add((c.name, s)); uses[(c.name, s)] = uses.get((c.name, s), 0) + 1
            cuts.append({"f": f0, "n": f1 - f0, "src": c.name, "from": round(s, 3), "rate": round(rate, 3), "zoom": ZOOMS[zi], "angle": c.angle, "type": typ,
                         "frame": "none" if lay in ("hook", "logo") else ("compact" if lay in FULL or lay is None else "full")})
            last_clip, last_angle = c.name, c.angle
        start += fr
    return cuts


def stage(cuts: list[dict], lib: list[Clip]) -> dict[str, str]:
    """Copy only the source clips the reel uses into the render folder; returns {name: path relative to the template's public folder}."""
    dst = WORK / "avatar" / "clips"
    dst.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in sorted({c["src"] for c in cuts}):
        src = next(c.path for c in lib if c.name == name)
        shutil.copy(src, dst / name)
        out[name] = f"assets/run/avatar/clips/{name}"
    return out


def summary(cuts: list[dict]) -> str:
    kinds: dict[str, int] = {}
    for c in cuts:
        kinds[c["type"]] = kinds.get(c["type"], 0) + 1
    return ", ".join(f"{k} x{v}" for k, v in sorted(kinds.items()))
