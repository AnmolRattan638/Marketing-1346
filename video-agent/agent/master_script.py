"""The master script written by the post pipeline (src/agents/scriptwriter.py, saved on today's draft in data/drafts/<date>.json).
When it exists the video agent is a DIRECTOR: the words are fixed, it only chooses pictures, graphics and camera for each beat."""
from __future__ import annotations
import json
import os
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFTS = ROOT.parent / "data" / "drafts"
_W = re.compile(r"\W+")


def load(path: str | None = None, today: str | None = None) -> dict | None:
    """--script PATH (a draft or a bare master script), else MASTER_SCRIPT env, else today's draft. None when there is no usable script."""
    path = path or os.environ.get("MASTER_SCRIPT") or str(DRAFTS / f"{today or date.today().isoformat()}.json")
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    m = d.get("master_script") if isinstance(d, dict) and "master_script" in d else d
    if not isinstance(m, dict) or not m.get("beats"):
        return None
    if isinstance(d, dict) and d.get("service") and not m.get("service"):
        m = {**m, "service": d["service"]}
    return m


def _norm(t: str) -> str:
    return _W.sub(" ", (t or "").lower()).strip()


def beat_order(master: dict) -> list[str]:
    return [b["beat"] for b in master["beats"]]


def problems(plan: dict, master: dict) -> list[str]:
    """Scenes must play the master's beats in order (fix may span several scenes)."""
    seq = []
    for s in plan.get("scenes", []):
        if not seq or seq[-1] != s.get("beat"):
            seq.append(s.get("beat"))
    want = beat_order(master)
    return [] if seq == want else [f"scene beats must follow the master script exactly: {want}, got {seq}"]


def enforce_words(plan: dict, master: dict) -> dict:
    """The spoken words belong to the scriptwriter: each non-fix beat's scene says its line verbatim; a fix beat's scenes together say the fix line
    (the first fix scene says it, extra fix scenes are dropped, so nothing the planner invented is spoken)."""
    lines = {b["beat"]: b["line"] for b in master["beats"]}
    seen, scenes = set(), []
    for s in plan["scenes"]:
        b = s.get("beat")
        if b not in lines or b in seen:
            continue
        seen.add(b)
        scenes.append({**s, "narration": lines[b]})
    plan["scenes"] = scenes
    return plan


def prompt_block(master: dict) -> str:
    beats = "\n".join(f"- {b['beat']}: \"{b['line']}\"  on screen: {b.get('screen', '')}  picture idea: {b.get('visual', '')}" for b in master["beats"])
    return ("\nMASTER SCRIPT (fixed, fact-checked; you are the DIRECTOR). One scene per beat, in exactly this order, each with its `beat` field. Do NOT write or change any words: "
            "the scene's narration is the beat's line, copied. Your job is the picture: choose graphic layout, fx, camera, footage_query for each beat "
            "(pain = bold title/punch, poke = strike, fix = step/checklist/terminal, payoff = stat/punch, recap = title, cta = outro). Add no fact, number or claim.\n"
            f"Style: {master.get('style')}\n{beats}\n")
