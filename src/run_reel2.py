"""Second reel of the day. The daily draft makes reel 1 (same script as the carousel); this makes reel 2 for a DIFFERENT service from the same pipeline:
research -> verified fact sheet -> master script (all marketing + content rules) -> saved as data/master/<date>-2.json -> reel workflow (slot 2).
Safe to call any number of times: it does nothing if today's second script already exists (unless --force)."""
import os
import subprocess
import sys

import requests

from . import config, ideas, verticals, web_research, browser_research, tg
from .agents import analysis, factsheet, research, scriptwriter
from .run_daily import WARNINGS, ensure_fit, pick_focus, stage, today

SLOT = "2"


def other_focus(brand, history, first_id):
    """A service different from reel 1's: the normal weekday pick if it differs, else the least recently used of the others."""
    guess = pick_focus(brand, history + [{"service": first_id, "date": today}])
    if guess["id"] != first_id:
        return guess
    last_used = {h.get("service"): h.get("date", "") for h in history}
    others = [s for s in brand["services"] if s["id"] != first_id]
    return min(others, key=lambda s: last_used.get(s["id"], ""))


def first_reel(day):
    d = config.load_json(config.DATA / "master" / f"{day}.json", {}) or {}
    m = d.get("master_script") or {}
    return d.get("service") or m.get("service"), m.get("topic")


def series_from(day, brand):
    """Reel 2 as PART 2 of reel 1: same service, same verified facts (no new research, no extra LLM credits), and a script that answers what reel 1 left open.
    None (the old different-service reel 2) when REEL2_LOOP=0 or reel 1 has no usable script."""
    if os.getenv("REEL2_LOOP", "1").strip().lower() in ("0", "false", "off", "no"):
        return None
    d = config.load_json(config.DATA / "master" / f"{day}.json", {}) or {}
    m = d.get("master_script") or {}
    beats = m.get("beats") or []
    facts = [f for f in (m.get("facts") or []) if isinstance(f, dict) and f.get("claim")]
    sid = d.get("service") or m.get("service")
    focus = next((s for s in brand["services"] if s["id"] == sid), None)
    if len(beats) < 4 or len(facts) < 3 or not focus:
        return None
    rehook = next((b.get("line") for b in beats if b.get("beat") == "rehook"), "")
    steps = [b.get("line") for b in beats if b.get("beat") in ("fix", "payoff")][:3]
    cited = [str(f.get("figure")) for f in facts if f.get("figure") and str(f.get("figure")) in " ".join(str(b.get("line")) for b in beats)]
    return {"focus": focus, "sheet": {"ok": True, "facts": facts, "topic": m.get("topic")}, "style_used": m.get("style"),
            "series": {"hook": beats[0].get("line"), "rehook": rehook, "steps": steps, "facts_used": cited, "vertical": verticals.of(beats[0].get("line"))}}


def start_video(master, focus):
    token = os.getenv("GITHUB_TOKEN")
    if os.getenv("GITHUB_ACTIONS") != "true" or not token:
        print("not inside GitHub Actions: script saved locally only")
        return False
    r = requests.post(f"https://api.github.com/repos/{config.REPO}/actions/workflows/video-agent-fast.yml/dispatches", timeout=30,
                      headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                      json={"ref": os.getenv("GITHUB_REF_NAME") or "main", "inputs": {"slot": SLOT}})
    return r.status_code == 204


def main():
    force = "--force" in sys.argv
    path = config.DATA / "master" / f"{today}-{SLOT}.json"
    if path.exists() and not force:
        print(f"Second reel script for {today} already exists; nothing to do.")
        return 0
    brand, history = config.services(), config.history()
    first_id, first_topic = first_reel(today)
    loop = series_from(today, brand)
    if loop:                                                    # part 2 of reel 1: same service and facts, no research
        style = scriptwriter.pick_style(history + [{"script_style": loop["style_used"], "date": today}])
        if style["id"] == loop["style_used"]:
            style = next(s for s in scriptwriter.STYLES if s["id"] != loop["style_used"])
        focus = loop["focus"]
        master = stage("scriptwriter", lambda: scriptwriter.run(loop["sheet"], focus, style, series=loop["series"]), fallback=False)
        if master:
            master["service"] = focus["id"]
            master["series"] = {"part": 2, "of": loop["series"]["hook"]}
            config.save_json(path, {"master_script": master, "service": focus["id"], "slot": SLOT})
            if not start_video(master, focus):
                tg.send(f"Reel 2 (part 2 of reel 1, {focus['name']}) script is ready but the video could not be started automatically. Run 'Daily video' with slot 2.")
            print(f"reel 2 (part 2) started: {focus['id']}")
            return 0
        print("part 2 script failed; falling back to a separate reel 2")
    focus = other_focus(brand, history, first_id or "")
    used = [h.get("topic") for h in history] + ([first_topic] if first_topic else [])
    guidance = ""
    try:
        guidance = (config.DATA / "strategy.md").read_text(encoding="utf-8")
    except Exception:
        pass
    web = stage("web.trends", lambda: web_research.trend_context(focus, today), fallback="") if web_research.enabled() else ""
    web_kw = {"web": web} if web else {}
    topics = stage("research", lambda: research.run(brand, focus, used, guidance, today, ideas.ideas_text(ideas.for_service(focus["id"], ideas.used_ids(history))), **web_kw),
                   fallback=[{"topic": f"A practical tip about {focus['name']} for local businesses", "angle": focus["pitch"], "why_it_matters": "fallback topic"}])
    plan = stage("analysis", lambda: analysis.run(topics, focus, guidance, history))
    plan = ensure_fit(plan, topics, focus, brand, guidance, history)
    ev = stage("web.evidence", lambda: web_research.evidence_for(plan, focus), fallback=[]) if web_research.enabled() else []
    ev_text = web_research.evidence_text(ev)
    ev_full = browser_research.enrich(ev) if ev else ev
    sheet = stage("factsheet", lambda: factsheet.build(plan["topic"], ev_full, ev_text), fallback={"ok": False, "facts": []}) if ev else {"ok": False, "facts": []}
    if not sheet.get("ok"):
        tg.send(f"Reel 2 not made today: only {len(sheet.get('facts', []))} verified facts for '{plan.get('topic')}' ({focus['name']}). Nothing was posted.")
        return 1
    master = stage("scriptwriter", lambda: scriptwriter.run(sheet, focus, scriptwriter.pick_style(history)), fallback=False)
    if not master:
        tg.send(f"Reel 2 not made today: no valid script for '{plan.get('topic')}' ({focus['name']}). Reasons: {'; '.join(WARNINGS[-2:])[:300]}")
        return 1
    master["service"] = focus["id"]
    config.save_json(path, {"master_script": master, "service": focus["id"], "slot": SLOT})
    if os.getenv("GITHUB_ACTIONS") == "true":
        subprocess.run(["bash", "scripts/commit_state.sh", f"master: {today}-{SLOT}"], cwd=config.ROOT, timeout=300)
    if not start_video(master, focus):
        tg.send(f"Reel 2 script is ready ({focus['name']}) but the video could not be started automatically. Run 'Daily video' with slot 2.")
        return 1
    print(f"reel 2 started: {focus['id']} / {plan['topic']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
