"""Daily draft run: strategist (incl. Instagram state check) -> research -> analysis -> writer -> fact-check -> ad-check -> image/video -> Telegram."""
import datetime as dt
import os, secrets
import sys, traceback
import requests
from . import analytics, config, llm, tg
from .agents import analysis, factcheck, image, research, strategist, video, writer

today = dt.date.today().isoformat()
WARNINGS = []


def pick_focus(brand, history):
    svcs, sched = brand["services"], brand.get("schedule", {})
    wd = dt.date.today().weekday()
    if wd == sched.get("website_weekday", 5):               # websites: one post a week
        pool = [s for s in svcs if s["priority"] == 2]
    elif wd == sched.get("other_weekday", 2):               # scripts / SEO: one slot a week
        pool = [s for s in svcs if s["priority"] == 3]
    else:                                                   # chatbots, AI ads, lead gen
        pool = [s for s in svcs if s["priority"] == 1]
    pool = pool or [s for s in svcs if s["priority"] == 1]
    last_used = {h.get("service"): h.get("date", "") for h in history}
    return min(pool, key=lambda s: last_used.get(s["id"], ""))


def should_skip(path, force):
    """Skip only if today's draft is still alive (pending, publishing or published). A rejected or failed one is replaced."""
    if force or not path.exists():
        return False, ""
    status = config.load_json(path, {}).get("status")
    if status == "publishing":      # an earlier run died while posting: do NOT make a new draft until the owner has checked the accounts
        return True, ("Today's draft was being published when a run stopped, so it may already be live. Check Instagram, LinkedIn and Bluesky first. "
                      "If nothing was posted, run Daily draft and tick 'Redo today's draft'.")
    if status in ("pending", "published", "partial"):
        return True, (f"Today's draft already exists (status: {status}), so I did not create another. "
                      + ("Find its message above and tap Approve or Reject. " if status == "pending" else "")
                      + "To make a new one, run Daily draft and tick 'Redo today's draft'.")
    return False, ""


def check_repo_public():
    """Images reach Instagram/LinkedIn through raw.githubusercontent.com and the approval wait burns ~170 runner-hours a month,
    so the repo must be public. Warn in Telegram if GitHub says it is not (unauthenticated lookup 404s for private repos)."""
    if not os.getenv("GITHUB_REPOSITORY"):
        return
    try:
        r = requests.get(f"https://api.github.com/repos/{config.REPO}", timeout=20)
        if r.status_code == 404:
            WARNINGS.append("repo looks PRIVATE: image links will 404 for the posting tools and the approval wait will use your free Actions minutes. Make it public or change the design.")
    except Exception:
        pass


def stage(name, fn, fallback=None):
    try:
        return fn()
    except Exception as e:
        WARNINGS.append(f"{name}: {str(e)[:160]}")
        print(f"[{name}] failed: {e}", file=sys.stderr)
        traceback.print_exc()
        if fallback is None:
            raise RuntimeError(f"{name}: {e}") from e
        return fallback


def main():
    force = "--force" in sys.argv
    path = config.DRAFTS / f"{today}.json"
    skip, why = should_skip(path, force)
    if skip:
        print(why)
        tg.send(why)          # never skip silently: say so in Telegram
        return
    brand, voice = config.services(), config.voice()
    history = config.history()
    metrics = config.load_json(config.DATA / "metrics.json", {})
    check_repo_public()
    # Read-only: the Analytics sync workflow (every 6 hours) owns data/analytics.json. This long-running job must never write it,
    # or its end-of-run commit could overwrite a newer sync.
    live_digest, live_signals = analytics.load_digest()
    focus = pick_focus(brand, history)
    ig_mode = "manual_reel" if dt.date.today().weekday() in brand.get("instagram", {}).get("manual_reel_weekdays", [2]) else "auto_image"

    try:
        state = stage("strategist.guide",
                      lambda: strategist.guide(history, metrics, focus, today, brand, live_digest),
                      fallback={"stage": "unknown", "summary": "", "instructions": {}, "manual_tips": [],
                                "guidance": "No guidance today. Teach first, never sound like an ad."})
        guidance = state.get("guidance") or "Teach first, never sound like an ad."
        (config.DATA / "strategy.md").write_text(guidance, encoding="utf-8")
        config.save_json(config.DATA / "account_state.json", {"date": today, **state, "weak_signals": live_signals})

        def g(agent):
            note = (state.get("instructions") or {}).get(agent)
            return guidance + (f"\n\nSTRATEGIST BRIEF (current Instagram state: {state.get('stage')}): {note}" if note else "")

        used = [h.get("topic") for h in history]
        topics = stage("research", lambda: research.run(brand, focus, used, g('research'), today),
                       fallback=[{"topic": f"A practical tip about {focus['name']} for local businesses",
                                  "angle": focus["pitch"], "why_it_matters": "fallback topic"}])
        plan = stage("analysis", lambda: analysis.run(topics, focus, g('analysis'), history))
        posts = stage("writer", lambda: writer.run(plan, focus, brand, voice, g('writer'), ig_mode=ig_mode))
        fc = stage("factcheck", lambda: factcheck.run(posts, focus, brand), fallback={"ok": None, "issues": ["fact-check unavailable"], "revised": {}})
        for k, v in (fc.get("revised") or {}).items():
            if k in posts and v:
                posts[k] = v[:300] if k == "bluesky" else v
        rv = stage("strategist.review", lambda: strategist.review(posts), fallback={"ad_score": None, "notes": ""})
        if (rv.get("ad_score") or 0) >= 7:
            posts = stage("writer.rewrite", lambda: writer.run(plan, focus, brand, voice, g('writer'), rv.get("notes", ""), ig_mode=ig_mode), fallback=posts)
            fc2 = stage("factcheck.2", lambda: factcheck.run(posts, focus, brand), fallback={"ok": None, "issues": [], "revised": {}})
            for k, v in (fc2.get("revised") or {}).items():
                if k in posts and v:
                    posts[k] = v[:300] if k == "bluesky" else v
            fc = fc2
        img = stage("image", lambda: image.run(plan, focus, today, g('image')), fallback={"prompt": None, "path": None})
        if img.get("engine") == "text_card" or not img.get("path"):
            WARNINGS.append(("image: AI engines failed, used a plain text card. " if img.get("path") else "image: no image at all. ") + " | ".join(dict.fromkeys(img.get("errors", [])))[:400])
        vid = stage("video", lambda: video.run(plan, focus, posts, g('video')), fallback={}) if ig_mode == "manual_reel" else {}
    except Exception as e:
        tg.send(f"Marketing pipeline failed on {today}: {e}\nNothing was posted. Check the Actions log.")
        raise

    draft = {"id": f"{today}-{secrets.token_hex(3)}", "date": today, "status": "pending", "service": focus["id"], "topic": plan["topic"],
             "hooks": plan["hooks"], "chosen_hook": plan.get("chosen_hook", 0),
             "hook_style": plan["hooks"][plan.get("chosen_hook", 0)].get("style"),
             "posts": {k: posts[k] for k in config.PLATFORMS}, "replies": posts.get("replies", []),
             "image": img, "instagram_mode": ig_mode, "video": vid, "factcheck": fc, "ad_score": rv.get("ad_score")}
    config.save_json(path, draft)

    tg.send(("WARNINGS (a step failed and a fallback was used):\n- " + "\n- ".join(WARNINGS) + "\n\n" if WARNINGS else "") +
            f"Draft for {today}\nService: {focus['name']}\nTopic: {plan['topic']}\n"
            f"Instagram today: {'MANUAL reel (post it yourself)' if ig_mode == 'manual_reel' else 'auto-posted image + caption'}\nFact-check: {'OK' if fc.get('ok') else fc.get('issues')}\nAd-score: {rv.get('ad_score')} (lower is better)\n\n"
            f"Account check ({state.get('stage')}): {state.get('summary')}" +
            (("\nLive weak spots: " + "; ".join(f"[{s['platform']}] {s['detail']}" for s in live_signals[:2])) if live_signals else "") +
            "\n\nModels that answered: " + (" | ".join(dict.fromkeys(llm.LOG))[:700] or "n/a") +
            ("\nManual tips:\n- " + "\n- ".join(map(str, state.get("manual_tips") or [])) if state.get("manual_tips") else ""))
    if img.get("path"):
        tg.send_photo(config.ROOT / img["path"], img.get("prompt") or "")
    for p in config.PLATFORMS:
        tg.send(f"[{p.upper()}{' CAPTION FOR YOUR REEL' if p == 'instagram' and ig_mode == 'manual_reel' else (' CAPTION, auto-posted with the image' if p == 'instagram' else '')}]\n{posts[p]}")
    if vid:
        parts = vid.get("parts") or []
        tg.send("[REEL, 30 seconds = 3 clips of 10s in Google Flow]\nHook (first 3s): " + str(vid.get("hook_first_3s", "")) +
                "\n\nFull voiceover:\n" + vid.get("voiceover", "") +
                "\n\nThe 3 prompts follow, one message each. Generate them in order, join the clips in any editor (e.g. CapCut), add captions, then post.")
        for i, part in enumerate(parts, 1):
            tg.send(f"[FLOW PROMPT {i}/{len(parts)} | {part.get('time')}]\nSpoken line: {part.get('voiceover')}\n\n{part.get('flow_prompt')}")
    if draft["replies"]:
        tg.send("[REPLY DRAFTS]\n" + "\n\n".join(f"If: {r['if_they_say']}\n-> {r['reply']}" for r in draft["replies"]))
    tg.send(("Approve posting to LinkedIn and Bluesky? (Wednesday: Instagram is your manual reel.)" if ig_mode == "manual_reel" else "Approve posting to Instagram, LinkedIn and Bluesky?") + " It posts within seconds of your tap. Want your own image (e.g. from Adobe Express)? Send it to this chat as a photo first; add the caption 'ai' if it is AI-made.",
            buttons=[{"text": "Approve", "callback_data": f"approve:{draft['id']}"},
                     {"text": "Reject", "callback_data": f"reject:{draft['id']}"}])


if __name__ == "__main__":
    main()
