"""Scroll-stop gate: the reel goes through the ViralSim predictor (src/virality.py) before it reaches Telegram.

 1. stop_fix(plan, master): deterministic. Scene 1 is a full-colour `punch` slide whose headline is the hook's own 3-5 words (works on mute).
 2. forecast(plan, master): ViralSim scores the spoken script + on-screen hook, with the hook A/B; plus a scroll-stop checklist.
 3. report(): the text sent to Telegram BEFORE the video, so you read the verdict first. Advisory: the model is a coarse heuristic (see src/virality.py)."""
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.append(str(_REPO))

NUM = re.compile(r"\d")
LOOP = re.compile(r"(\bkya\b|\?|raat|subah|baje|\bagar\b|\bjab\b|\bkyun)", re.I)


def stop_check(plan: dict, master: dict | None = None) -> list[str]:
    """Why scene 1 might not stop a scroll (empty = fine)."""
    sc = (plan.get("scenes") or [{}])[0]
    g = sc.get("graphic") if isinstance(sc.get("graphic"), dict) else {}
    head = str(g.get("heading") or "").split()
    line = str(sc.get("narration") or "")
    out = []
    if not 2 <= len(head) <= 6:
        out.append("first-frame headline is not 3-5 bold words")
    if g.get("layout") not in ("punch", "title"):
        out.append("first frame is not a bold full-screen slide")
    if len(line.split()) > 16:
        out.append("spoken hook runs over 16 words")
    if not (NUM.search(line) or LOOP.search(line)):
        out.append("hook has no number, time or question to open a loop")
    return out


def stop_fix(plan: dict, master: dict | None = None) -> dict:
    """Scene 1 becomes a punch slide with the hook headline (the script's own `screen` words)."""
    scenes = plan.get("scenes") or []
    if not scenes:
        return plan
    hook = " ".join(str(((master or {}).get("beats") or [{}])[0].get("screen") or "").split()[:5])
    g = scenes[0].get("graphic") if isinstance(scenes[0].get("graphic"), dict) else {}
    head = " ".join(str(g.get("heading") or hook or "").split()[:5])
    if head:
        scenes[0]["graphic"] = {**g, "layout": "punch", "heading": head[:30]}
    return plan


def forecast(plan: dict, master: dict | None) -> dict:
    """-> {"virality": ViralSim result or None, "stop": [issues]}. Never raises: the predictor is advisory."""
    res = {"virality": None, "stop": stop_check(plan, master)}
    try:
        from src import virality
        text = " ".join(str(s.get("narration") or "") for s in plan.get("scenes", []))
        hooks = [{"text": h.get("text"), "style": h.get("style")} for h in (master or {}).get("hooks", []) if isinstance(h, dict)]
        chosen = next((i for i, h in enumerate(hooks) if h["text"] == (plan["scenes"][0].get("narration") if plan.get("scenes") else None)), 0)
        res["virality"] = virality.run({"instagram": text}, hooks if len(hooks) > 1 else None, chosen, llm=virality.make_llm())
    except Exception as e:
        print(f"[viral] predictor failed (advisory, continuing): {str(e)[:120]}")
    return res


def report(res: dict) -> str:
    """Telegram text. Shown before the video."""
    out = ["Predictor check (ViralSim, before you see the reel):"]
    v = res.get("virality") or {}
    ig = (v.get("platforms") or {}).get("instagram")
    if ig:
        weak = sorted((ig.get("dims") or {}).items(), key=lambda kv: kv[1])[:2]
        out.append(f"Score {ig['score']:.0f}/100 (coarse, advisory)" + (f"; weakest: {', '.join(f'{k} {x:g}' for k, x in weak)}" if weak else ""))
        ab = v.get("ab")
        if ab and ab.get("better") is not None:
            out.append(f"Another hook simulates better (hook {ab['better'] + 1}); this reel kept the script's hook.")
        hints = "; ".join(x["title"] for x in (ig.get("levers") or [])[:2])
        if hints:
            out.append("Could lift: " + hints)
    else:
        out.append("Predictor unavailable this run.")
    out.append("Scroll-stop check: " + ("passed (bold punch slide, hook headline on frame 1, concrete opener)" if not res.get("stop") else "weak: " + "; ".join(res["stop"])))
    return "\n".join(out)
