"""Weekly learning review: updates the results table and the problem bank from the latest analytics and screenshots, writes
data/learning_notes.md, and sends you a short Telegram summary (what was tested, what the data says, what is planned next, and which
numbers are missing). It changes data files only. It never edits prompts, rules or code, and every post still needs your approval."""
import datetime as dt

from . import analytics, config, learning, tg

VERB = {"winner": "worked", "average": "average", "weak": "weak", "not_enough_data": "too early", "no_metrics": "no numbers"}
SHORT = {"instagram": "IG", "linkedin": "LI", "bluesky": "BS"}
WHERE = {"instagram": "Instagram: Insights", "linkedin": "LinkedIn: View analytics", "bluesky": "Bluesky"}


def _x(item):
    if item.get("composite") is None:
        return VERB.get(item["verdict"], item["verdict"])
    return f"{item['composite']}x {VERB.get(item['verdict'], '')}" + (f" ({item['diagnosis']})" if item["verdict"] == "weak" else "")


def data_gaps(drafts, results, now):
    """Published posts old enough to judge that have no numbers (e.g. LinkedIn through Buffer), and reels without retention."""
    gaps = []
    for date, d in sorted(drafts.items()):
        t = analytics._ts(f"{date}T09:00:00+00:00")
        if (now - t).total_seconds() / 3600 < 72:
            continue
        for plat in config.PLATFORMS:
            if not learning._publish_ok(d, plat) or plat not in (d.get("results") or {}):
                continue
            rec = results["posts"].get(f"{date}|{plat}")
            text = (d.get("posts") or {}).get(plat, "")
            hint = " ".join(learning.captions.unstyle(text).split()[:8])
            if not rec:
                gaps.append(f"{plat.title()} {date} \"{hint}\": no numbers. Screenshot: {WHERE[plat]}, caption \"stats {plat}\".")
            elif plat == "instagram" and d.get("instagram_mode") == "manual_reel" and not {"skip_rate", "avg_watch_s"} & set(rec["snap"].get("48h", {})):
                gaps.append(f"Instagram reel {date} \"{hint}\": no retention numbers. Screenshot its Insights (skip rate, watch time), caption \"stats instagram\".")
    return gaps[-6:]


def build(now=None):
    now = now or analytics.utcnow()
    data = analytics.load()
    res = learning.update_results(data, now)
    scored = learning.score_all(res, data.get("accounts"))
    bank = learning.refresh_bank(learning.load_bank(), scored)
    learning.save_bank(bank)
    posts = learning.per_post(scored)
    week = [p for p in posts if (now - analytics._ts(f"{p['date']}T09:00:00+00:00")).days <= 9]
    brand, history = config.services(), config.history()
    lines = [f"Weekly learning review - {now.date().isoformat()}",
             f"Posts with numbers: {len(posts)}. Judged against a baseline: {sum(1 for p in posts if p['composite'] is not None)} (a verdict needs 3 comparable posts on the same platform). "
             + ("Your accounts are small, so treat every result as a hint, not proof." if posts and learning.digest_text(scored, bank, data.get("accounts")).count("low confidence") else "")]
    if week:
        lines.append("\nTHIS WEEK (1.0x = the account's median)")
        for p in week:
            prob = next((b["problem"][:45] for b in bank["problems"] if b["id"] == p["problem_id"]), "free topic")
            lines.append(f"- {p['date']} {p['service']} | {prob} | angle {p['angle_type'] or '-'} | hook {p['hook_style'] or '-'} | " +
                         " ; ".join(f"{SHORT.get(k, k)} {_x(v)}" for k, v in p["platforms"].items()))
    else:
        lines.append("\nNo post is old enough with numbers yet (a post needs 48 hours). Nothing to learn from this week.")
    for field, name in (("hook_style", "Hook styles"), ("angle_type", "Angle types"), ("service", "Services")):
        ls = learning.lessons(posts, field)
        if ls:
            lines.append(f"{name}: " + ", ".join(f"{k} {v}x (n={n})" for k, v, n in ls[:5]))
    counts = {s: sum(1 for b in bank["problems"] if b["status"] == s) for s in ("winner", "promising", "testing", "untested", "dud")}
    lines.append("\nPROBLEM BANK: " + (", ".join(f"{n} {s}" for s, n in counts.items() if n) or "empty (the next daily run researches the first problems)"))
    for status in ("winner", "promising", "dud"):
        for b in [b for b in bank["problems"] if b["status"] == status][:3]:
            lines.append(f"- {status}: {b['problem'][:70]} (mean {b['mean']}x over {b['tests']})")
    plan = []
    for s in brand.get("services", []):
        exp = learning.next_experiment(s["id"], bank, scored, learning.service_post_count(history, s["id"]), learning.recent_problem_ids())
        if exp:
            plan.append(f"- {s['id']}: {learning.label(exp)}")
    if plan:
        lines.append("\nNEXT EXPERIMENTS (planned; they may change when new numbers arrive)\n" + "\n".join(plan[:6]))
    gaps = data_gaps(learning._published(), res, now)
    if gaps:
        lines.append("\nMISSING NUMBERS (send the screenshot to this chat)\n" + "\n".join(f"- {g}" for g in gaps))
    text = "\n".join(lines)
    notes = text + "\n\nALL SCORED POSTS\n" + "\n".join(
        f"{s['date']} {s['platform']:9} {s['service']} problem={s['problem_id']} angle={s['angle_type']} hook={s['hook_style']} fmt={s['format']} cta={s['cta']} "
        f"mode={s['mode']} var={s['variable']} -> {s['verdict']} {s['composite']} {s['diagnosis']} comps={s['components']} peers={s['peers']} conf={s['confidence']}"
        for s in scored) + "\n"
    (config.DATA / "learning_notes.md").write_text(notes, encoding="utf-8")
    return text[:3800]


def main():
    text = build()
    print(text)
    tg.send(text)


if __name__ == "__main__":
    main()
