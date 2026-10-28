"""Daily draft run: strategist (incl. Instagram state check) -> research -> analysis -> writer -> fact-check -> ad-check -> image/video -> Telegram."""
import datetime as dt
import os, secrets
import sys, traceback
import requests
from . import analytics, captions, carousel, config, diagrams, formats, ideas, learning, llm, tg
from .agents import analysis, carousel as carousel_agent, factcheck, fit as fit_agent, image, linkedin_edit, problems as problems_agent, research, strategist, video, writer

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
    """Images reach Instagram/LinkedIn through raw.githubusercontent.com and the approval wait burns ~150 runner-hours a month,
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


def polish_linkedin(posts, focus, brand):
    """LinkedIn only: readability edit (plain, clear English). Instagram, Bluesky and the reply drafts are never touched."""
    res = stage("linkedin_edit", lambda: linkedin_edit.run(posts.get("linkedin", ""), focus, brand), fallback={})
    if res.get("post"):
        posts["linkedin"] = res["post"]
    return posts


def ensure_fit(plan, topics, focus, brand, guidance, history):
    """A post must sell the service in focus. If the topic or hook reads like another service, re-run the analysis once with a correction, then
    fall back to the curated idea for this service; if it still drifts, say so in Telegram instead of letting it through silently."""
    def fits(p):
        return (stage("service_fit", lambda: fit_agent.check(p, focus, brand), fallback={}) or {"fits": True})
    v = fits(plan)
    if v.get("fits", True):
        return plan
    other = next((s["name"] for s in brand["services"] if s["id"] == v.get("picked")), v.get("picked"))
    note = (f"SERVICE FIT: your last topic ('{plan['topic']}') reads like an ad for {other}, not for {focus['name']}. Choose a topic and hook where "
            f"{focus['name']} itself is the answer, and do not describe {other}'s way of solving it.")
    plan2 = stage("analysis.fit", lambda: analysis.run(topics, focus, guidance + "\n\n" + note, history), fallback=plan)
    if plan2 is not plan and fits(plan2).get("fits", True):
        return plan2
    pool = ideas.for_service(focus["id"], ideas.used_ids(history), limit=1)
    if pool:
        i = pool[0]
        only = [{"topic": i["topic"], "angle": i["angle"], "why_it_matters": "", "idea_id": i["id"]}]
        plan3 = stage("analysis.idea", lambda: analysis.run(only, focus, guidance + "\n\n" + note, history), fallback=plan2)
        if plan3 is not plan2 and fits(plan3).get("fits", True):
            return plan3
    WARNINGS.append(f"service fit: this post may read like {other} instead of {focus['name']}. Check the headline before approving.")
    return plan2


def send_explainer(focus):
    """Service explainer diagram as a separate Telegram image: not the thumbnail and never posted automatically (use it as a 2nd slide, a comment
    image or a story). It is drawn from the config and the date, so it goes to a temp file and nothing is stored in the repo."""
    import pathlib, tempfile
    with tempfile.TemporaryDirectory() as td:
        info = diagrams.render_for(focus, today, pathlib.Path(td) / f"{today}-explainer.jpg")
        tg.send_photo(info["path"], f"[SERVICE EXPLAINER] Not the thumbnail and never posted automatically. Use it as a 2nd slide, a comment image or a story. Layout: {info['layout']}.")
    return {"layout": info["layout"], "palette": info["palette"]}


def plan_experiment(focus, learned, brand, guidance, history):
    """Learning loop: top up the problem bank when it runs low, then pick today's experiment (None = no directive today)."""
    bank = learned["bank"]
    if learning.needs_research(bank, focus["id"]):
        try:
            items = problems_agent.run(brand, focus, learning.problem_texts(bank, focus["id"]), guidance)
            if learning.add_problems(bank, focus["id"], items, today):
                learning.save_bank(bank)
        except Exception as e:
            WARNINGS.append(f"problem research: {str(e)[:120]}")
    return learning.next_experiment(focus["id"], bank, learned["scored"], learning.service_post_count(history, focus["id"]), learning.recent_problem_ids())


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
    learned = stage("learning", learning.snapshot, fallback={"scored": [], "bank": {"problems": []}, "accounts": {}, "digest": ""})
    if learned["digest"]:
        live_digest = f"{live_digest}\n\n{learned['digest']}" if live_digest else learned["digest"]
    exp = None
    car, car_data = None, None
    focus = pick_focus(brand, history)
    ig_mode = "manual_reel" if dt.date.today().weekday() in brand.get("instagram", {}).get("manual_reel_weekdays", [2]) else "auto_image"
    try:
        li_fmt = formats.linkedin_format(today)        # alternate text-only and image posts on LinkedIn
    except Exception:
        li_fmt = "image"

    try:
        state = stage("strategist.guide",
                      lambda: strategist.guide(history, metrics, focus, today, brand, live_digest),
                      fallback={"stage": "unknown", "summary": "", "instructions": {}, "manual_tips": [],
                                "guidance": "No guidance today. Teach first, never sound like an ad."})
        guidance = state.get("guidance") or "Teach first, never sound like an ad."
        (config.DATA / "strategy.md").write_text(guidance, encoding="utf-8")
        config.save_json(config.DATA / "account_state.json", {"date": today, **state, "weak_signals": live_signals})

        exp = stage("learning.experiment", lambda: plan_experiment(focus, learned, brand, guidance, history), fallback={}) or None
        if exp:
            guidance = guidance + "\n\n" + learning.directive_text(exp)

        def g(agent):
            note = (state.get("instructions") or {}).get(agent)
            return guidance + (f"\n\nSTRATEGIST BRIEF (current Instagram state: {state.get('stage')}): {note}" if note else "")

        used = [h.get("topic") for h in history]
        topics = stage("research", lambda: research.run(brand, focus, used, g('research'), today, ideas.ideas_text(ideas.for_service(focus['id'], ideas.used_ids(history)))),
                       fallback=[{"topic": f"A practical tip about {focus['name']} for local businesses",
                                  "angle": focus["pitch"], "why_it_matters": "fallback topic"}])
        plan = stage("analysis", lambda: analysis.run(topics, focus, g('analysis'), history))
        plan = ensure_fit(plan, topics, focus, brand, g('analysis'), history)
        if config.CAROUSEL:
            # hook -> problem -> solution -> CTA, told in one of the rotating tastes; the carousel's hook becomes the post's hook, so captions and the first slide agree
            car, why = stage("carousel", lambda: carousel_agent.build(plan, focus, brand, g('writer'), today), fallback=(None, "the carousel step failed"))
            if car:
                plan["hooks"][plan.get("chosen_hook", 0)]["text"] = car["slides"][0]["headline"]
                if not car.get("checked"):
                    WARNINGS.append("carousel: the fact-check was unavailable, so read every slide before approving.")
            else:
                WARNINGS.append(f"carousel skipped (single image instead): {why}")
        posts = stage("writer", lambda: writer.run(plan, focus, brand, voice, g('writer'), ig_mode=ig_mode, linkedin_format=li_fmt))
        posts = polish_linkedin(posts, focus, brand)
        fc = stage("factcheck", lambda: factcheck.run(posts, focus, brand), fallback={"ok": None, "issues": ["fact-check unavailable"], "revised": {}})
        for k, v in (fc.get("revised") or {}).items():
            if k in posts and v:
                posts[k] = v[:300] if k == "bluesky" else v
        rv = stage("strategist.review", lambda: strategist.review(posts), fallback={"ad_score": None, "notes": ""})
        if (rv.get("ad_score") or 0) >= 7:
            posts = stage("writer.rewrite", lambda: writer.run(plan, focus, brand, voice, g('writer'), rv.get("notes", ""), ig_mode=ig_mode, linkedin_format=li_fmt), fallback=posts)
            posts = polish_linkedin(posts, focus, brand)
            fc2 = stage("factcheck.2", lambda: factcheck.run(posts, focus, brand), fallback={"ok": None, "issues": [], "revised": {}})
            for k, v in (fc2.get("revised") or {}).items():
                if k in posts and v:
                    posts[k] = v[:300] if k == "bluesky" else v
            fc = fc2
        posts = captions.finalize_posts(posts, focus_id=focus.get("id"))             # LAST: markers -> real bold, layout tidy, Bluesky <= 300 (fact-check may have rewritten the text)
        img = stage("image", lambda: image.run(plan, focus, today, g('image')), fallback={"prompt": None, "path": None})
        if img.get("engine") == "text_card" or not img.get("path"):
            WARNINGS.append(("image: AI engines failed, used a plain text card. " if img.get("path") else "image: no image at all. ") + " | ".join(dict.fromkeys(img.get("errors", [])))[:400])
        if car and img.get("path"):
            fact = next((x for x in carousel_agent.facts_for(focus["id"]) if x.get("id") == car.get("fact_id")), None) if car.get("fact_id") else None
            car_data = stage("carousel.render", lambda: carousel.render(car, focus, today, img["path"], img.get("style_id"), fact), fallback={}) or None
            if not car_data:
                WARNINGS.append("carousel: the slides could not be drawn, so this goes out as a single image.")
        elif car:
            WARNINGS.append("carousel: there is no hook image, so this goes out without a carousel.")
        vid = stage("video", lambda: video.run(plan, focus, posts, g('video')), fallback={}) if ig_mode == "manual_reel" else {}
    except Exception as e:
        tg.send(f"Marketing pipeline failed on {today}: {e}\nNothing was posted. Check the Actions log.")
        raise

    pid = learning.valid_problem_id(plan.get("problem_id"))
    followed = bool(exp) and pid == exp["problem_id"]
    if exp and not followed:
        WARNINGS.append("learning loop: the analysis step did not follow today's experiment problem, so this post is not counted as a test of it.")
    exp_line = f"Experiment: {learning.label(exp)}\n" if followed else ""
    draft = {"id": f"{today}-{secrets.token_hex(3)}", "date": today, "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "status": "pending", "service": focus["id"], "topic": plan["topic"], "idea_id": ideas.valid_id(plan.get("idea_id")),
             "problem_id": pid if followed else None, "angle_type": plan.get("angle_type") if plan.get("angle_type") in learning.ANGLE_TYPES else None,
             "experiment": {k: exp.get(k) for k in ("mode", "variable", "problem_id", "angle_type", "hook_style")} if followed else None,
             "hooks": plan["hooks"], "chosen_hook": plan.get("chosen_hook", 0),
             "hook_style": plan["hooks"][plan.get("chosen_hook", 0)].get("style"),
             "posts": {k: posts[k] for k in config.PLATFORMS}, "replies": posts.get("replies", []),
             "image": img, "carousel": car_data, "instagram_mode": ig_mode, "linkedin_format": li_fmt, "video": vid, "factcheck": fc, "ad_score": rv.get("ad_score"),
             "llm": {"answered": list(dict.fromkeys(llm.LOG)), "failures": llm.FAILURES[:20]}}
    config.save_json(path, draft)

    tg.send(("WARNINGS (a step failed and a fallback was used):\n- " + "\n- ".join(WARNINGS) + "\n\n" if WARNINGS else "") +
            f"Draft for {today}\nService: {focus['name']}\nTopic: {plan['topic']}\n{exp_line}"
            f"Instagram today: {'MANUAL reel (post it yourself)' if ig_mode == 'manual_reel' else 'auto-posted image + caption'}\nLinkedIn today: {'TEXT ONLY (no image)' if li_fmt == 'text' else 'with the image'}\nFact-check: {'OK' if fc.get('ok') else fc.get('issues')}\nAd-score: {rv.get('ad_score')} (lower is better)\n\n"
            f"Account check ({state.get('stage')}): {state.get('summary')}" +
            (("\nLive weak spots: " + "; ".join(f"[{s['platform']}] {s['detail']}" for s in live_signals[:2])) if live_signals else "") +
            "\n\nModels that answered: " + (" | ".join(dict.fromkeys(llm.LOG))[:700] or "n/a") +
            ("\nManual tips:\n- " + "\n- ".join(map(str, state.get("manual_tips") or [])) if state.get("manual_tips") else ""))
    if car_data:
        names = {t["id"]: t["name"] for t in carousel_agent.flavors()}
        tg.send_media_group([config.ROOT / x for x in car_data["paths"]],
                            f"[CAROUSEL, {len(car_data['paths'])} slides | taste: {names.get(car_data['flavor'], car_data['flavor'])}] Order: hook, problem, solution, CTA. "
                            f"Instagram and LinkedIn get every slide; Bluesky gets 4 (slides {', '.join(str(i + 1) for i in car_data['bluesky'])}). "
                            f"Hook image prompt: {(img.get('prompt') or '')[:420]}")
    elif img.get("path"):
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
    if not (car_data and "diagram" in car_data["roles"]):          # a carousel with the diagram slide already shows it
        stage("explainer", lambda: send_explainer(focus), fallback={})
    tg.send(("Approve posting to LinkedIn and Bluesky? (Wednesday: Instagram is your manual reel.)" if ig_mode == "manual_reel" else "Approve posting to Instagram, LinkedIn and Bluesky?") + " It posts within seconds of your tap. Want your own image (e.g. from Adobe Express)? Send it to this chat as a photo first; add the caption 'ai' if it is AI-made.",
            buttons=[{"text": "Approve", "callback_data": f"approve:{draft['id']}"},
                     {"text": "Reject", "callback_data": f"reject:{draft['id']}"}])


if __name__ == "__main__":
    main()
