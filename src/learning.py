"""Learning loop. Deterministic code, no LLM, and it never edits prompts or code.

1. update_results: joins every published post to what was tested (problem, angle type, hook style, format, CTA) and freezes its
   numbers once the post is old enough to judge (48 hours; a 7-day reading is added later). Screenshots sent to the bot
   (data/manual_analytics.json) fill in what the platform APIs cannot see, e.g. LinkedIn posts published through Buffer.
2. score_all: scores each post against the account's OWN median for the same platform and format (leave-one-out), then diagnoses a
   weak post as distribution (few people saw it), hook (people left fast), value (they stayed but did not engage) or mixed.
3. refresh_bank: keeps a bank of audience problems with a status: untested, testing, promising, winner or dud.
4. next_experiment: change ONE variable at a time, mostly repeat what works, test a new problem about 1 post in 3.
The agents only ever receive its conclusions as guidance text; a human still approves every post."""
import json
import re
import statistics

from . import analytics, captions, config, ideas

ANGLE_TYPES = ["myth_bust", "mistake", "story", "how_to", "comparison", "checklist", "question"]
MIN_SNAP_H = 48         # a post younger than this is too fresh to judge
MIN_FINAL_H = 168       # a 7-day reading is stored as well, once the post is this old
MIN_PEERS = 3           # other posts needed on the same platform and format before a verdict means anything
MAX_PROBLEMS = 60
FOLLOWER_FLOOR = 100    # below this many followers a verdict is only a hint


# ---------------------------------------------------------------- storage
def _load(name, default):
    return config.load_json(config.DATA / name, default)


def _save(name, obj):
    config.save_json(config.DATA / name, obj)


def load_results():
    r = _load("post_results.json", {})
    r.setdefault("posts", {})
    return r


def load_bank():
    b = _load("problem_bank.json", {})
    b.setdefault("problems", [])
    return b


def save_bank(bank):
    _save("problem_bank.json", bank)


def load_manual():
    m = _load("manual_analytics.json", {})
    m.setdefault("entries", [])
    return m


def _all_drafts():
    out = []
    for f in sorted(config.DRAFTS.glob("*.json")):
        d = config.load_json(f, None)
        if isinstance(d, dict) and d.get("date"):
            out.append(d)
    return out


def _published():
    return {d["date"]: d for d in _all_drafts() if d.get("status") in ("published", "partial")}


def _publish_ok(d, platform):
    return bool(((d.get("results") or {}).get(platform) or {}).get("ok", True))


def cta_of(text):
    return "dm" if re.search(r"\bDM\b", captions.unstyle(text or "")) else "none"


def row_format(d, platform, reported):
    """The format the pipeline decided (LinkedIn alternates text-only and image); the platform's own label is only a fallback."""
    return (d.get("linkedin_format") if platform == "linkedin" else None) or reported


def _attrs(d, platform, fmt):
    exp = d.get("experiment") or {}
    return {"date": d["date"], "platform": platform, "service": d.get("service"), "problem_id": d.get("problem_id"),
            "angle_type": d.get("angle_type"), "hook_style": d.get("hook_style"), "format": fmt or "image",
            "cta": cta_of((d.get("posts") or {}).get(platform, "")), "mode": exp.get("mode"), "variable": exp.get("variable"),
            "image_style": (d.get("image") or {}).get("style_id"), "carousel_flavor": (d.get("carousel") or {}).get("flavor"),
            "slides": len((d.get("carousel") or {}).get("paths") or []) or 1}


# ---------------------------------------------------------------- 1. join + freeze
def manual_rows(drafts, now):
    """Rows built from screenshots: only for posts a screenshot names (post_hint) and that exactly one published draft matches."""
    out = []
    for e in load_manual()["entries"]:
        plat = e.get("platform")
        cap = analytics._ts(e.get("captured_at")) or now
        for item in e.get("posts") or []:
            hint = analytics._norm(captions.unstyle(item.get("post_hint") or ""))[:30]
            if len(hint) < 12 or not item.get("metrics"):
                continue
            hit = [d for d in drafts.values() if _publish_ok(d, plat) and hint in analytics._norm((d.get("posts") or {}).get(plat, ""))[:240]]
            if not hit:
                continue
            d = max(hit, key=lambda x: x["date"])
            pub = f"{d['date']}T09:00:00+00:00"       # the exact minute is unknown; the date is what the screenshot proves
            age = (cap - analytics._ts(pub)).total_seconds() / 3600
            out.append({"platform": plat, "date": d["date"], "format": row_format(d, plat, "image"), "published_at": pub, "url": None, "source": "screenshot",
                        "metrics": {k: v for k, v in item["metrics"].items() if v is not None}, "age_h": age})
    return out


def update_results(data, now=None):
    """Merge the analytics rows (and screenshots) into data/post_results.json. Writes only when something real changed."""
    now = now or analytics.utcnow()
    res = load_results()
    before = json.dumps(res, sort_keys=True)
    drafts = _published()
    rows, api = [], {}
    for r in data.get("posts") or []:
        mt = r.get("matched")
        d = drafts.get(mt.get("date")) if mt else None
        if not d or not _publish_ok(d, r["platform"]):
            continue
        row = {"platform": r["platform"], "date": d["date"], "format": row_format(d, r["platform"], r.get("format")), "published_at": r.get("published_at"), "url": r.get("url"),
               "source": r.get("source"), "metrics": {k: v for k, v in (r.get("metrics") or {}).items() if v is not None},
               "age_h": analytics._age_h(r, now)}
        rows.append(row)
        api[(d["date"], r["platform"])] = row
    for m in manual_rows(drafts, now):
        k = (m["date"], m["platform"])
        if k in api:                                     # a screenshot only fills what the API did not report, never overwrites it
            for name, v in m["metrics"].items():
                if name not in api[k]["metrics"]:
                    api[k]["metrics"][name] = v
                    api[k]["filled"] = True
        else:
            rows.append(m)
    for row in rows:
        age = row["age_h"]
        if age is None or age < MIN_SNAP_H:
            continue
        key = f"{row['date']}|{row['platform']}"
        rec = res["posts"].setdefault(key, {**_attrs(drafts[row["date"]], row["platform"], row["format"]),
                                             "published_at": row["published_at"], "url": row["url"], "snap": {}})
        snap = rec["snap"]
        if "48h" not in snap:
            snap["48h"] = {"age_h": round(age, 1), "source": row["source"], **row["metrics"]}
        elif row["source"] == "screenshot" or row.get("filled"):     # e.g. retention numbers the API never gives
            for name, v in row["metrics"].items():
                snap["48h"].setdefault(name, v)
        if age >= MIN_FINAL_H and "7d" not in snap:
            snap["7d"] = {"age_h": round(age, 1), "source": row["source"], **row["metrics"]}
        rec["latest"] = dict(row["metrics"])
    if json.dumps(res, sort_keys=True) != before:
        res["updated_at"] = now.isoformat(timespec="seconds")
        _save("post_results.json", res)
    return res


# ---------------------------------------------------------------- 2. score + diagnose
def _med(xs, zeros=False):
    xs = [x for x in xs if x is not None and (zeros or x > 0)]
    return statistics.median(xs) if xs else None


def _rate(m):
    e, r = analytics.engagement(m), analytics.reach_of(m)
    return e / r if (e is not None and r) else None


def _ratio(x, base):
    if x is None or base is None:
        return None
    if base == 0:
        return 2.0 if x > 0 else 1.0
    return x / base


def _comps(snap, base):
    out = {"reach": _ratio(analytics.reach_of(snap), base.get("reach")), "engagement": _ratio(_rate(snap), base.get("rate"))}
    sk = snap.get("skip_rate")
    if sk is not None and base.get("skip"):
        out["retention"] = 4.0 if sk == 0 else base["skip"] / sk          # a LOWER skip rate is better
    return {k: round(min(max(v, 0.0), 4.0), 2) for k, v in out.items() if v is not None}


def _judge(comps, followers):
    if not comps:
        return {"verdict": "no_metrics", "diagnosis": None, "composite": None}
    composite = round(statistics.mean(comps.values()), 2)
    r, e, t = comps.get("reach"), comps.get("engagement"), comps.get("retention")
    if composite >= 1.5:
        verdict, diag = "winner", "worked"
    elif r is not None and r < 0.5 and (e is None or e >= 0.8) and (t is None or t >= 0.8):
        verdict, diag = "weak", "distribution"           # few people saw it, but the ones who did were fine
    elif (r is None or r >= 0.8) and ((t is not None and t < 0.7) or (e is not None and e < 0.5)):
        verdict, diag = "weak", ("hook" if (t is not None and t < 0.7) else "value")
    elif composite < 0.6:
        verdict, diag = "weak", "mixed"
    else:
        verdict, diag = "average", "ok"
    return {"verdict": verdict, "diagnosis": diag, "composite": composite}


def score_all(results, accounts=None):
    """One item per (post, platform) with a 48h reading, scored against the other posts on the same platform and format."""
    recs = [dict(r, key=k) for k, r in results["posts"].items() if (r.get("snap") or {}).get("48h")]
    out = []
    for r in recs:
        peers = [p for p in recs if p["key"] != r["key"] and p["platform"] == r["platform"] and p["format"] == r["format"]]
        item = {k: r.get(k) for k in ("date", "platform", "service", "problem_id", "angle_type", "hook_style", "format", "cta", "mode", "variable", "image_style", "carousel_flavor", "slides")}
        item["key"], item["peers"] = r["key"], len(peers)
        fol = ((accounts or {}).get(r["platform"]) or {}).get("followers")
        item["confidence"] = "low" if (len(peers) < 5 or (fol is not None and fol < FOLLOWER_FLOOR)) else "ok"
        if len(peers) < MIN_PEERS:
            item.update(verdict="not_enough_data", diagnosis=None, composite=None, components={})
        else:
            s = r["snap"]["48h"]
            base = {"reach": _med([analytics.reach_of(p["snap"]["48h"]) for p in peers]),
                    "rate": _med([_rate(p["snap"]["48h"]) for p in peers], zeros=True),
                    "skip": _med([p["snap"]["48h"].get("skip_rate") for p in peers])}
            comps = _comps(s, base)
            item.update(_judge(comps, fol), components=comps)
        out.append(item)
    return sorted(out, key=lambda x: (x["date"], x["platform"]))


def per_post(scored):
    by = {}
    for s in scored:
        by.setdefault(s["date"], []).append(s)
    out = []
    for date, items in sorted(by.items()):
        comps = [i["composite"] for i in items if i.get("composite") is not None]
        first = items[0]
        out.append({"date": date, "service": first["service"], "problem_id": first["problem_id"], "angle_type": first["angle_type"],
                    "hook_style": first["hook_style"], "variable": first["variable"], "mode": first["mode"], "image_style": first.get("image_style"), "carousel_flavor": first.get("carousel_flavor"),
                    "composite": round(statistics.mean(comps), 2) if comps else None,
                    "diagnoses": [i["diagnosis"] for i in items if i.get("diagnosis")], "platforms": {i["platform"]: i for i in items}})
    return out


# ---------------------------------------------------------------- 3. problem bank
def _words(t):
    return set(re.findall(r"[a-z0-9]+", (t or "").lower()))


def _slug(t):
    return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")[:40] or "problem"


def problem_texts(bank, service):
    return [p["problem"] for p in bank["problems"] if p.get("service") in (service, "any")]


def needs_research(bank, service):
    fresh = [p for p in bank["problems"] if p.get("service") in (service, "any") and p.get("status") in ("untested", "testing")]
    return len(fresh) < 2


def add_problems(bank, service, items, today):
    """Add researched problems, skipping near-duplicates (word overlap >= 60%) and keeping the bank small."""
    added = 0
    for it in items or []:
        text = str(it.get("problem") or "").strip()
        if len(text) < 8 or len(bank["problems"]) >= MAX_PROBLEMS:
            continue
        w = _words(text)
        if any(w and len(w & _words(p["problem"])) / max(len(w | _words(p["problem"])), 1) >= 0.6 for p in bank["problems"] if p.get("service") == service):
            continue
        ids = {p["id"] for p in bank["problems"]}
        pid, n = _slug(text), 2
        base = pid
        while pid in ids:
            pid, n = f"{base}-{n}", n + 1
        row = {"id": pid, "service": service, "problem": text[:200], "added": today, "status": "untested", "tests": 0, "mean": None,
               "source": "model research (a hypothesis until a post tests it)"}
        for k in ("frustration", "desired_outcome", "audience_phrase", "common_mistake", "objection", "emotional_reason"):
            row[k] = str(it.get(k) or "")[:200]
        bank["problems"].append(row)
        added += 1
    return added


def valid_problem_id(pid):
    return pid if pid and any(p["id"] == pid for p in load_bank()["problems"]) else None


def refresh_bank(bank, scored):
    posts = per_post(scored)
    for p in bank["problems"]:
        mine = [x for x in posts if x["problem_id"] == p["id"] and x["composite"] is not None]
        n = len(mine)
        p["tests"] = n
        if not n:
            p["status"], p["mean"] = "untested", None
            continue
        m = round(statistics.mean(x["composite"] for x in mine), 2)
        p["mean"] = m
        content_weak = sum(1 for x in mine if any(d in ("hook", "value", "mixed") for d in x["diagnoses"]))
        if n >= 2 and m >= 1.2:
            p["status"] = "winner"
        elif n == 1 and m >= 1.5:
            p["status"] = "promising"
        elif n >= 2 and m < 0.7 and content_weak / n >= 0.5:      # not a dud when the real issue was that nobody saw the posts
            p["status"] = "dud"
        else:
            p["status"] = "testing"
    return bank


def lessons(posts, field):
    by = {}
    for x in posts:
        if x.get(field) and x["composite"] is not None:
            by.setdefault(x[field], []).append(x["composite"])
    return sorted(((k, round(statistics.mean(v), 2), len(v)) for k, v in by.items()), key=lambda t: -t[1])


# ---------------------------------------------------------------- 4. next experiment
def service_post_count(history, service_id):
    return sum(1 for h in history if h.get("service") == service_id and h.get("status") in ("published", "partial"))


def recent_problem_ids(limit=3):
    return [d.get("problem_id") for d in _all_drafts()[-limit:] if d.get("problem_id")]


def _hook_styles():
    return [h["style"] for h in ideas.bank()["hook_library"] if h.get("style")] or ["question", "mistake-callout", "specific-observation", "myth-bust"]


def _least_tried(options, tried):
    return sorted(options, key=lambda o: sum(1 for t in tried if (t or "").lower() == o.lower()))[0]


def next_experiment(service_id, bank, scored, n_service_posts, avoid=()):
    pool = [p for p in bank["problems"] if p.get("service") in (service_id, "any")]
    order = {"untested": 0, "testing": 1}
    fresh = [p for p in pool if p["status"] in order]
    proven = [p for p in pool if p["status"] in ("winner", "promising")]
    explore = sorted([p for p in fresh if p["id"] not in avoid] or fresh, key=lambda p: (order[p["status"]], p["tests"], p["added"]))
    exploit = sorted([p for p in proven if p["id"] not in avoid] or proven, key=lambda p: (-(p.get("mean") or 0), p["tests"]))
    if explore and (not exploit or n_service_posts % 3 == 2):
        mode, p = "explore", explore[0]
    elif exploit:
        mode, p = "exploit", exploit[0]
    else:
        return None
    posts = per_post(scored)
    mine = [x for x in posts if x["problem_id"] == p["id"] and x["composite"] is not None]
    best = max(mine, key=lambda x: x["composite"]) if mine else None
    exp = {"mode": mode, "problem_id": p["id"], "problem": {k: p.get(k) for k in ("problem", "frustration", "desired_outcome", "audience_phrase", "objection", "common_mistake")},
           "angle_type": None, "hook_style": None, "avoid_angle_types": [], "avoid_hook_styles": []}
    if mode == "explore":
        style = lessons(posts, "hook_style")
        exp.update(variable="problem", hook_style=style[0][0] if style else None,
                   reason="a problem not tested yet; hook style kept at the best known one so the problem is the only change")
    elif len(mine) % 2 == 0:                          # alternate which variable changes so each gets tested
        tried = [x["angle_type"] for x in mine]
        exp.update(variable="angle_type", angle_type=_least_tried(ANGLE_TYPES, tried), avoid_angle_types=sorted({t for t in tried if t}),
                   hook_style=best["hook_style"] if best else None,
                   reason="same problem that worked, a new angle type")
    else:
        tried = [x["hook_style"] for x in mine]
        exp.update(variable="hook_style", hook_style=_least_tried(_hook_styles(), tried), avoid_hook_styles=sorted({t for t in tried if t}),
                   angle_type=best["angle_type"] if best else None,
                   reason="same problem that worked, a new hook style")
    return exp


def label(exp):
    return f"{exp['mode']} (changing only: {exp['variable']}) | problem: {exp['problem']['problem']}"


def directive_text(exp):
    p = exp["problem"]
    lines = ["EXPERIMENT (learning loop; follow it exactly):",
             f"- Mode: {exp['mode']} ({exp['reason']}).",
             f"- Audience problem id={exp['problem_id']}: {p.get('problem')}",
             f"  Frustration: {p.get('frustration')} | They would say: \"{p.get('audience_phrase')}\" | Objection: {p.get('objection')} | Wants: {p.get('desired_outcome')}",
             f"- Change ONLY this variable compared with earlier posts: {exp['variable']}."]
    if exp.get("angle_type"):
        lines.append(f"  Angle type to use: {exp['angle_type']}" + (f" (already used on this problem: {', '.join(exp['avoid_angle_types'])})" if exp["avoid_angle_types"] else "") + ".")
    if exp.get("hook_style"):
        lines.append(f"  Hook style to use: {exp['hook_style']}" + (f" (already used on this problem: {', '.join(exp['avoid_hook_styles'])})" if exp["avoid_hook_styles"] else "") + ".")
    lines += ["- The topic you pick MUST address this problem. Return problem_id and angle_type in your JSON.",
              "- All brand rules still apply: universal audience, no invented statistics, clients or demos."]
    return "\n".join(lines)


# ---------------------------------------------------------------- what the agents and you get to read
def digest_text(scored, bank, accounts=None, limit=1100):
    posts = [x for x in per_post(scored) if x["composite"] is not None]
    if not posts:
        return ""
    fol = [(a or {}).get("followers") for a in (accounts or {}).values() if (a or {}).get("followers") is not None]
    small = bool(fol) and max(fol) < FOLLOWER_FLOOR
    parts = [f"LEARNING LOOP (the account's own results; 1.0 = its median){' - low confidence: under 100 followers, treat as hints' if small else ''}",
             f"Scored posts: {len(posts)}."]
    for field, name in (("hook_style", "Hook styles"), ("angle_type", "Angle types"), ("image_style", "Image styles"), ("carousel_flavor", "Carousel tastes"), ("service", "Services")):
        ls = lessons(posts, field)
        if ls:
            parts.append(f"{name}: " + ", ".join(f"{k} {v}x (n={n})" for k, v, n in ls[:5]))
    for status in ("winner", "promising", "dud"):
        names = [p["problem"][:60] for p in bank["problems"] if p["status"] == status]
        if names:
            parts.append(f"Problems {status}: " + "; ".join(names[:3]))
    last = posts[-1]
    parts.append(f"Latest scored post {last['date']}: {last['composite']}x" + (f", diagnosis: {'/'.join(dict.fromkeys(last['diagnoses']))}" if last["diagnoses"] else ""))
    return "\n".join(parts)[:limit]


def snapshot():
    data = analytics.load()
    scored = score_all(load_results(), data.get("accounts"))
    bank = refresh_bank(load_bank(), scored)
    return {"scored": scored, "bank": bank, "accounts": data.get("accounts") or {}, "digest": digest_text(scored, bank, data.get("accounts"))}
