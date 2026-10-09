"""Daily draft run: strategist -> research -> analysis -> writer -> fact-check -> ad-check -> image/video -> Telegram."""
import datetime as dt
import sys, traceback
from . import config, tg
from .agents import analysis, factcheck, image, research, strategist, video, writer

today = dt.date.today().isoformat()


def pick_focus(brand, history):
    svcs = brand["services"]
    pool = [s for s in svcs if s["priority"] == 1]
    if dt.date.today().timetuple().tm_yday % 7 == 0:   # one day a week for the lower-priority services
        pool = [s for s in svcs if s["priority"] != 1] or pool
    last_used = {h.get("service"): h.get("date", "") for h in history}
    return min(pool, key=lambda s: last_used.get(s["id"], ""))


def stage(name, fn, fallback=None):
    try:
        return fn()
    except Exception as e:
        print(f"[{name}] failed: {e}", file=sys.stderr)
        traceback.print_exc()
        if fallback is None:
            raise RuntimeError(f"{name}: {e}") from e
        return fallback


def main():
    force = "--force" in sys.argv
    path = config.DRAFTS / f"{today}.json"
    if path.exists() and not force:
        print("Draft for today already exists; use --force to redo.")
        return
    brand, voice = config.services(), config.voice()
    history = config.load_json(config.DATA / "history.json", [])
    metrics = config.load_json(config.DATA / "metrics.json", {})
    focus = pick_focus(brand, history)

    try:
        guidance = stage("strategist.guide", lambda: strategist.guide(history, metrics),
                         fallback="No guidance today. Teach first, never sound like an ad.")
        (config.DATA / "strategy.md").write_text(guidance, encoding="utf-8")
        used = [h.get("topic") for h in history]
        topics = stage("research", lambda: research.run(brand, focus, used, guidance, today),
                       fallback=[{"topic": f"A practical tip about {focus['name']} for local businesses",
                                  "angle": focus["pitch"], "why_it_matters": "fallback topic"}])
        plan = stage("analysis", lambda: analysis.run(topics, focus, guidance, history))
        posts = stage("writer", lambda: writer.run(plan, focus, brand, voice, guidance))
        fc = stage("factcheck", lambda: factcheck.run(posts, focus, brand), fallback={"ok": None, "issues": ["fact-check unavailable"], "revised": {}})
        for k, v in (fc.get("revised") or {}).items():
            if k in posts and v:
                posts[k] = v[:300] if k == "bluesky" else v
        rv = stage("strategist.review", lambda: strategist.review(posts), fallback={"ad_score": None, "notes": ""})
        if (rv.get("ad_score") or 0) >= 7:
            posts = stage("writer.rewrite", lambda: writer.run(plan, focus, brand, voice, guidance, rv.get("notes", "")), fallback=posts)
        img = stage("image", lambda: image.run(plan, focus, today), fallback={"prompt": None, "path": None})
        vid = stage("video", lambda: video.run(plan, focus, posts), fallback={})
    except Exception as e:
        tg.send(f"Marketing pipeline failed on {today}: {e}\nNothing was posted. Check the Actions log.")
        raise

    draft = {"date": today, "status": "pending", "service": focus["id"], "topic": plan["topic"],
             "hooks": plan["hooks"], "chosen_hook": plan.get("chosen_hook", 0),
             "hook_style": plan["hooks"][plan.get("chosen_hook", 0)].get("style"),
             "posts": {k: posts[k] for k in config.PLATFORMS}, "replies": posts.get("replies", []),
             "image": img, "video": vid, "factcheck": fc, "ad_score": rv.get("ad_score")}
    config.save_json(path, draft)

    tg.send(f"Draft for {today}\nService: {focus['name']}\nTopic: {plan['topic']}\n"
            f"Fact-check: {'OK' if fc.get('ok') else fc.get('issues')}\nAd-score: {rv.get('ad_score')} (lower is better)")
    if img.get("path"):
        tg.send_photo(config.ROOT / img["path"], img.get("prompt") or "")
    for p in config.PLATFORMS:
        tg.send(f"[{p.upper()}]\n{posts[p]}")
    if vid:
        tg.send("[REEL IDEA, make it in Google Flow]\n" + vid.get("voiceover", "") + "\n\nFlow prompt:\n" + vid.get("flow_prompt", ""))
    if draft["replies"]:
        tg.send("[REPLY DRAFTS]\n" + "\n\n".join(f"If: {r['if_they_say']}\n-> {r['reply']}" for r in draft["replies"]))
    tg.send(f"Approve posting to Instagram, LinkedIn and Bluesky via Buffer?",
            buttons=[{"text": "Approve", "callback_data": f"approve:{today}"},
                     {"text": "Reject", "callback_data": f"reject:{today}"}])


if __name__ == "__main__":
    main()
