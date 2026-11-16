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


def report(res: dict, video: dict | None = None, history: list | None = None) -> str:
    """Telegram text, sent BEFORE the video: the bots' verdict, weak points left, and how many fix rounds ran."""
    out = ["ViralSim check (before you see the reel):"]
    v = (res or {}).get("virality") or {}
    ig = (v.get("platforms") or {}).get("instagram")
    if ig:
        out.append(f"Script/text score {ig['score']:.0f}/100 (coarse, advisory)")
    if video and not video.get("failed") and video.get("bots"):
        out.append(f"Video bots: score {video['score']}/100 -> {'WORTH POSTING' if video['worth_posting'] else 'NOT convincing (best of the rounds shipped)'}; "
                   f"{video['hold3']:.0%} still watching at 3s, {video['avg_watch']:.0%} of the reel watched on average, {video['finish']:.0%} reach the end, muted viewers {video['sound_off_hold']:.0%}.")
        out.append("Bots: " + ", ".join(f"{k} {b['verdict']}" for k, b in video["bots"].items()))
        if history and len(history) > 1:
            out.append(f"Planner fix rounds: {len(history) - 1} (max 2). Scores per round: " + " -> ".join(str(h["score"]) for h in history))
        left = video.get("weak_points") or []
        if left:
            out.append("Weak points left: " + "; ".join(f"{w['kind']} at {w['t']}s ({w['detail']})" + ("" if w["planner"] else " [script-level]") for w in left[:4]))
    elif video and video.get("failed"):
        out.append("Video bot analysis was unavailable this run.")
    out.append("Scroll-stop check: " + ("passed" if not (res or {}).get("stop") else "weak: " + "; ".join(res["stop"])))
    return "\n".join(out)


def analyse_final(final, plan: dict, built: list, tail: float, rnd: int = 0) -> dict:
    """The rendered reel goes to the ViralSim viewer bots (viralsim/video.py: ffmpeg measurements + 6 personas). Never raises."""
    try:
        from viralsim import video
        total = sum(b["narration_seconds"] + tail for b in built) or 1.0
        dur = video.probe(str(final))["duration"] or total
        k, t0, spans = dur / total, 0.0, []
        for b, sc in zip(built, plan["scenes"]):
            d = (b["narration_seconds"] + tail) * k
            spans.append({"id": b["id"], "beat": sc.get("beat"), "start": t0, "end": t0 + d})
            t0 += d
        res = video.analyze_video(str(final), spans, seed=rnd)
        res["_feedback"] = video.feedback(res)
        return res
    except Exception as e:
        print(f"[viral] video analysis failed (advisory): {str(e)[:150]}")
        return {"score": 0.0, "worth_posting": True, "weak_points": [], "bots": {}, "threshold": 0, "curve": [], "failed": True}


def feedback(res: dict) -> str:
    """The detailed brief for the planner (weak points with times, scenes and fixes)."""
    return res.get("_feedback") or ""
