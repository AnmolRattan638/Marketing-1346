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


def make(topic: str, cfg: dict) -> dict:
    """No script on today's draft (a manual run, or the post pipeline skipped the day): build one the same way the post pipeline does, from a verified fact sheet.
    Raises RuntimeError with a plain reason when it cannot (no sources, fewer than 3 verified facts, no valid script): the run then fails loudly instead of
    improvising a generic video."""
    import sys
    repo = str(ROOT.parent)
    if repo not in sys.path:
        sys.path.append(repo)
    from src import web_research as wr
    from src.agents import factsheet, scriptwriter
    from . import edits
    service, clean = edits.detect_service(topic, cfg)
    focus = _focus(service)
    items = wr.evidence_for({"topic": clean}, focus)
    for p in wr.problems():
        print(f"[agent] {p}")
    if not items:
        raise RuntimeError(f"no web sources for '{clean}' (TAVILY_API_KEY / EXA_API_KEY missing, or web research is switched off)")
    sheet = factsheet.build(clean, items, wr.evidence_text(items, 1500))
    if not sheet.get("ok"):
        raise RuntimeError(f"only {len(sheet.get('facts', []))} verified facts for '{clean}' (need {factsheet.MIN_FACTS}); not making a video from guesses")
    history = []
    for f in sorted(DRAFTS.glob("*.json"))[-14:]:
        try:
            history.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    style = scriptwriter.pick_style(history)
    script = scriptwriter.run(sheet, focus, style)
    script["service"] = service
    return script


def _focus(service: str) -> dict:
    try:
        d = json.loads((ROOT.parent / "config" / "services.json").read_text(encoding="utf-8"))
        rows = d if isinstance(d, list) else d.get("services", [])
        row = next((r for r in rows if r.get("id") == service), None) or (rows[0] if rows else {})
        return {**row, "dm_keyword": row.get("dm_keyword", "")}
    except Exception:
        return {"id": service, "name": service, "pitch": "", "dm_keyword": ""}


def _digits(t: str) -> set[str]:
    return {d for d in re.findall(r"\d[\d,\.]*", t or "")}


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
    # nothing the planner adds may carry a claim: a stat/quote overlay or chip only survives when its number is in a verified fact
    ok = _digits(" ".join(f"{f.get('claim', '')} {f.get('figure') or ''}" for f in master.get("facts", [])))
    emo = {b["beat"]: b.get("emotion") for b in master["beats"]}
    for s in scenes:
        s["emotion"] = emo.get(s.get("beat")) or "calm"
        s["fx"] = [f for f in (s.get("fx") or []) if f.get("type") != "quote" and (f.get("type") != "stat" or (f.get("value") is not None and _digits(str(f.get("value"))) <= ok and ok))]
        g = s.get("graphic")
        if isinstance(g, dict) and g.get("chips"):
            g["chips"] = [c for c in g["chips"] if not _digits(c) or _digits(c) <= ok]
    plan["scenes"] = scenes
    return plan


def prompt_block(master: dict) -> str:
    beats = "\n".join(f"- {b['beat']}: \"{b['line']}\"  on screen: {b.get('screen', '')}  picture idea: {b.get('visual', '')}"
                      + (f"  STEPS to show as a step/checklist graphic, one per item: {' | '.join(b['steps'])}" if b.get("steps") else "") for b in master["beats"])
    return ("\nMASTER SCRIPT (fixed, fact-checked; you are the DIRECTOR). One scene per beat, in exactly this order, each with its `beat` field. Do NOT write or change any words: "
            "the scene's narration is the beat's line, copied. Your job is the picture: choose graphic layout, fx, camera, footage_query for each beat "
            "(pain = bold title/punch, poke = strike, fix = step/checklist/terminal, payoff = stat/punch, recap = title, cta = outro). Add no fact, number or claim.\n"
            f"Style: {master.get('style')}\n{beats}\n")
