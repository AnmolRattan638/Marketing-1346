"""Advisory pre-publish virality forecast (ViralSim, vendored in /viralsim).

Four parts, all ADVISORY. Nothing here blocks a post, rewrites a caption, picks a hook or changes an experiment:
  1. run(): scores the final captions after fact-check and ad-review (Monte-Carlo reach, platform signals, backlash risk, Instagram levers,
     rule-based crowd agents and a follower-graph cascade) and A/Bs the 3 hooks. Saved on the draft as `virality`, one block in Telegram.
  2. backtest(): compares those predictions with the real reach in data/post_results.json and reports the hit rate. The Telegram block carries
     this track record, so the score is always shown next to how much it has earned. Writes data/virality_backtest.json.
  3. live_forecast(): Hawkes fit on the real like/reply timestamps of recent Bluesky posts (run by the Analytics sync). Needs 5+ events per post,
     so on a tiny account most posts say "too few events". Writes data/virality_live.json. Instagram and LinkedIn give no event timestamps.
  4. review_lines(): the weekly review section for 2 and 3.
The offline model is a coarse lexical heuristic (viralsim/README.md, "Read this before trusting a number"), and its simulated reach is in model
units, far above what this account really gets. Until backtest() shows a real signal, read the score as a rough hint and the levers as writing tips."""
import math
import statistics
import unicodedata

from . import config

VERSION = 2
RUNS = 500                      # Monte-Carlo runs per platform: about half a second each
AB_RUNS = 300                   # paired runs per hook comparison
MIN_BACKTEST = 8                # posts needed before the backtest says anything but "too early"
MIN_EVENTS = 5                  # Hawkes needs at least this many events
PLATFORM_MAP = {"instagram": "instagram", "linkedin": "linkedin", "bluesky": "generic"}
BSKY = "https://public.api.bsky.app/xrpc"
BACKTEST_FILE, LIVE_FILE = "virality_backtest.json", "virality_live.json"


def plain(text):
    """Unicode-bold letters back to plain ones and markdown stars dropped, so the heuristic reads words and not styled glyphs."""
    return " ".join(unicodedata.normalize("NFKC", str(text or "")).replace("**", "").split())


def _reach(posts, platform):
    """Mean reach (or impressions, views) per post from the real analytics, or None when there are no numbers yet."""
    vals = []
    for p in posts:
        if p.get("platform") != platform:
            continue
        m = p.get("metrics") or {}
        v = next((m[k] for k in ("reach", "impressions", "views") if isinstance(m.get(k), (int, float))), None)
        if v is not None:
            vals.append(float(v))
    return statistics.fmean(vals) if vals else None


def creator_for(platform, analytics):
    """The real size of the account, so the model is not run with its default of 1,000 followers."""
    from viralsim.creator import Creator
    acc = (analytics.get("accounts") or {}).get(platform) or {}
    followers = float(acc.get("followers") or 0)
    per_post = _reach(analytics.get("posts") or [], platform)
    freq = 30.0                                              # one post per day on every platform
    return Creator(followers=max(followers, 1.0), following=float(acc.get("following") or 50), posting_freq=freq,
                   monthly_reach=(per_post * freq) if per_post is not None else max(followers, 1.0) * 3,
                   account_age_days=60, niche="small-business marketing")


# ---------------------------------------------------------------- 1. the daily forecast
def _agents(a):
    """Trimmed crowd-agent result: how many react, which roles share, how big the agent cascade grows."""
    c = a.get("cascade") or {}
    return {"totals": a.get("totals"), "engagement_rate": round(a.get("engagement_rate") or 0, 4), "by_role": a.get("by_role"),
            "cascade_size": c.get("size"), "r_effective": c.get("r_effective"),
            "discourse_tension": (a.get("discourse_tension") or {}).get("discourse_tension_score")}


def _network(n):
    c = n.get("cascade") or {}
    return {"cascade_size": c.get("size"), "reach_fraction": c.get("reach_fraction"), "r_effective": c.get("r_effective"),
            "polarization": round(n.get("polarization_after") or 0, 3), "echo_chamber": round(n.get("echo_chamber_index") or 0, 3)}


def ab_hooks(hooks, chosen, creator):
    """Paired Monte-Carlo A/B of the chosen hook against each alternative. Advisory: the learning loop picks the hook style on purpose
    (one variable per test), so this never changes the choice. -> None when there is nothing to compare."""
    from viralsim.ab import ab_simulated
    from viralsim.dimensions import HeuristicScorer
    from viralsim.pipeline import default_pool
    from viralsim.sim.wave import SimConfig
    texts = [plain((h or {}).get("text")) for h in hooks or []]
    if len(texts) < 2 or not 0 <= chosen < len(texts) or not all(texts):
        return None
    sc, pool, cfg = HeuristicScorer(), default_pool(), SimConfig(runs=AB_RUNS)
    cs = [sc.score(t) for t in texts]
    for c in cs:
        c.platform = "instagram"
    vs = []
    for i in range(len(texts)):
        if i == chosen:
            continue
        r = ab_simulated(pool, cs[chosen], cs[i], creator, None, cfg)
        base = r["mean_reach"]["A"] or 1.0
        vs.append({"hook": i, "style": (hooks[i] or {}).get("style"), "p_beats_chosen": round(r["p_b_beats_a"], 2),
                   "lift_pct": round(100 * r["mean_lift_b_vs_a"] / base, 1), "decisive": r["decisive"]})
    best = max(vs, key=lambda v: v["p_beats_chosen"])
    return {"chosen": chosen, "vs_chosen": vs, "better": best["hook"] if best["p_beats_chosen"] > 0.5 else None, "advisory": True}


def run(posts, hooks=None, chosen=0):
    """-> {"version", "platforms": {name: {...}}, "ab": {...} or None, "note"}. Raises on a real failure so the caller's stage() can report it."""
    from viralsim.pipeline import analyze
    analytics = config.load_json(config.DATA / "analytics.json", {}) or {}
    out = {}
    for name in config.PLATFORMS:
        text = plain(posts.get(name))
        if not text:
            continue
        r = analyze(text, creator=creator_for(name, analytics), platform=PLATFORM_MAP.get(name, "generic"), runs=RUNS, with_agents=True,
                    with_network=True, with_levers=(name == "instagram"), has_image=(name != "linkedin"))
        f = r["forecast"]
        levers = (r.get("suggestions") or {}).get("counterfactual") or []
        edits = (r.get("suggestions") or {}).get("text_edits") or []
        out[name] = {"score": r["viral_score"], "breakout_probability": round(f["viral_probability"], 3),
                     "reach_p10": f["reach_p10"], "reach_p50": f["reach_p50"], "reach_p90": f["reach_p90"],
                     "risk": r["risk"]["level"], "risk_issues": [str(i)[:120] for i in r["risk"]["issues"][:3]],
                     "agents": _agents(r.get("agents") or {}), "network": _network(r.get("network") or {}),
                     "levers": [{"title": x["title"], "lift_pct": x["lift_pct"]} for x in levers[:3]],
                     "edits": [{"title": x["title"], "impact": x.get("impact")} for x in edits[:3]],
                     "scorer": r["scorer"]}
    ab = None
    try:                                                       # the A/B is a bonus: its failure must not lose the forecast above
        ab = ab_hooks(hooks, chosen, creator_for("instagram", analytics))
    except Exception as e:
        print(f"[virality] hook A/B failed: {e}")
    return {"version": VERSION, "platforms": out, "ab": ab,
            "note": "advisory only; heuristic scorer; simulated reach is in model units, not a forecast for this account"}


# ---------------------------------------------------------------- 2. the backtest against real reach
def _actual(latest):
    """Real reach for a post, or None. Bluesky only reports engagement, which is a different thing, so it is not compared."""
    return next((float(latest[k]) for k in ("reach", "views", "impressions") if isinstance(latest.get(k), (int, float))), None)


def _spearman(x, y):
    from scipy.stats import spearmanr
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None, None
    rho, p = spearmanr(x, y)
    return (None, None) if math.isnan(rho) else (float(rho), float(p))


def backtest(runs=300, write=True):
    """Predicted vs real reach for every published post with a number. Stored predictions are used; older drafts are scored now from their
    saved caption (the model never sees the results, so this is a fair out-of-sample test). -> {platform: {...}}."""
    from viralsim.pipeline import analyze
    analytics = config.load_json(config.DATA / "analytics.json", {}) or {}
    results = (config.load_json(config.DATA / "post_results.json", {}) or {}).get("posts", {})
    rows = {p: [] for p in config.PLATFORMS}
    for f in sorted(config.DRAFTS.glob("*.json")):
        d = config.load_json(f, None)
        if not isinstance(d, dict) or d.get("status") != "published":
            continue
        for p in config.PLATFORMS:
            rec = results.get(f"{d.get('date')}|{p}")
            actual = _actual((rec or {}).get("latest") or {})
            if actual is None or not (d.get("posts") or {}).get(p):
                continue
            pred = ((d.get("virality") or {}).get("platforms") or {}).get(p)
            if not pred:
                r = analyze(plain(d["posts"][p]), creator=creator_for(p, analytics), platform=PLATFORM_MAP.get(p, "generic"), runs=runs,
                            with_agents=False, with_network=False, with_levers=False)
                pred = {"score": r["viral_score"], "reach_p50": r["forecast"]["reach_p50"]}
            rows[p].append((pred["score"], pred["reach_p50"], actual))
    out = {}
    for p, rs in rows.items():
        if not rs:
            continue
        sc, pr, ac = [r[0] for r in rs], [r[1] for r in rs], [r[2] for r in rs]
        rho, pv = _spearman(sc, ac)
        spread = max(sc) - min(sc)
        if len(rs) < MIN_BACKTEST:
            verdict = "too early"
        elif spread < 3:
            verdict = "no spread (the scores barely differ between posts)"
        elif rho is not None and rho >= 0.3 and pv is not None and pv < 0.1:
            verdict = "some signal"
        else:
            verdict = "no signal"
        out[p] = {"n": len(rs), "spearman": None if rho is None else round(rho, 2), "p_value": None if pv is None else round(pv, 2),
                  "score_spread": round(spread, 1), "median_actual_reach": statistics.median(ac), "median_predicted_reach": statistics.median(pr),
                  "reach_ratio": round(statistics.median(ac) / statistics.median(pr), 3) if statistics.median(pr) else None, "verdict": verdict}
    if write:
        config.save_json(config.DATA / BACKTEST_FILE, {"platforms": out, "note": "rank correlation of the score with real reach; needs 8+ posts and p<0.1 to count"})
    return out


def track_line(bt):
    """One line: how much the score has earned so far ('' when there is no data)."""
    parts = []
    for p, b in (bt or {}).items():
        corr = f"rank corr {b['spearman']} (p={b['p_value']})" if b.get("spearman") is not None else "no rank corr"
        parts.append(f"{p} n={b['n']}, {corr}: {b['verdict']}")
    return ("Track record vs real reach: " + "; ".join(parts) + ". Do not act on the score until this says 'some signal'.\n") if parts else ""


# ---------------------------------------------------------------- 3. Hawkes forecast from real engagement times (Bluesky)
def bsky_events(uri, get):
    """ISO timestamps of the likes and replies of one Bluesky post (reposts carry no timestamps, so they are not counted)."""
    times, cursor = [], None
    for _ in range(3):
        params = {"uri": uri, "limit": 100, **({"cursor": cursor} if cursor else {})}
        r = get(f"{BSKY}/app.bsky.feed.getLikes", params=params, timeout=30)
        if r.status_code >= 400:
            break
        j = r.json()
        times += [x.get("createdAt") or x.get("indexedAt") for x in j.get("likes", [])]
        cursor = j.get("cursor")
        if not cursor:
            break
    r = get(f"{BSKY}/app.bsky.feed.getPostThread", params={"uri": uri, "depth": 1, "parentHeight": 0}, timeout=30)
    if r.status_code < 400:
        for rep in ((r.json().get("thread") or {}).get("replies") or []):
            times.append(((rep.get("post") or {}).get("record") or {}).get("createdAt"))
    return [t for t in times if t]


def live_forecast(get=None, now=None, max_age_days=14, write=True):
    """Hawkes self-excitation fit on each recent Bluesky post's own engagement times -> expected further engagements. Never raises."""
    import numpy as np
    import requests
    from viralsim.sim.hawkes import fit_hawkes, forecast_remaining
    from . import analytics as an
    get, now = get or requests.get, now or an.utcnow()
    data = config.load_json(config.DATA / "analytics.json", {}) or {}
    out = {}
    for p in data.get("posts") or []:
        if p.get("platform") != "bluesky" or not p.get("id") or not p.get("published_at"):
            continue
        try:
            t0 = an._ts(p["published_at"])
            age_h = (now - t0).total_seconds() / 3600
            if age_h < 1 or age_h > max_age_days * 24:
                continue
            hrs = sorted(max(0.0, (an._ts(t) - t0).total_seconds() / 3600) for t in bsky_events(p["id"], get))
            rec = {"url": p.get("url"), "age_h": round(age_h, 1), "events": len(hrs), "unit": "likes + replies"}
            if len(hrs) < MIN_EVENTS:
                rec["status"] = "too few events"
            else:
                par = fit_hawkes(np.array(hrs), age_h)
                rec.update(status="ok", branching_ratio=round(par.branching_ratio, 3), expected_more=round(forecast_remaining(hrs, age_h, par), 1))
            out[p["id"]] = rec
        except Exception as e:                                   # one bad post must not stop the others
            out[p["id"]] = {"status": f"failed: {str(e)[:80]}"}
    if write:
        config.save_json(config.DATA / LIVE_FILE, {"updated_at": now.isoformat(timespec="seconds"), "posts": out,
                                                  "note": "Bluesky only (the only platform with public engagement timestamps); counts likes + replies, not reach"})
    return out


# ---------------------------------------------------------------- 4. Telegram and weekly review text
def telegram_line(v, bt=None):
    """The block for the daily draft message ('' when there is nothing)."""
    pl = (v or {}).get("platforms") or {}
    if not pl:
        return ""
    ig = pl.get("instagram") or {}
    out = "Virality hint (0-100, coarse, advisory): " + ", ".join(f"{n} {d['score']:.0f}" for n, d in pl.items()) + "\n"
    ab = v.get("ab")
    if ab:
        best = next((x for x in ab["vs_chosen"] if x["hook"] == ab["better"]), None)
        out += ("Hook A/B: " + (f"hook {best['hook'] + 1} ({best['style']}) simulates better than the chosen one (p={best['p_beats_chosen']}, lift {best['lift_pct']}%, "
                               f"{'decisive' if best['decisive'] else 'not decisive'}); the experiment keeps the chosen hook" if best
                               else "the chosen hook is at least as good as the other two in simulation") + "\n")
    a, n = ig.get("agents") or {}, ig.get("network") or {}
    if a.get("engagement_rate") is not None and n.get("reach_fraction") is not None:
        out += f"Crowd sim (Instagram): {a['engagement_rate'] * 100:.1f}% of viewers react, cascade R={n.get('r_effective')}, polarisation {n.get('polarization')}\n"
    risk = [f"{k}: {d['risk']}" for k, d in pl.items() if d.get("risk") not in (None, "none")]
    hints = "; ".join(x["title"] for x in (ig.get("levers") or [])[:2] + (ig.get("edits") or [])[:1])
    return out + (f"Backlash risk: {'; '.join(risk)}\n" if risk else "") + (f"Could lift Instagram: {hints}\n" if hints else "") + track_line(bt)


def review_lines():
    """Weekly review section: backtest verdicts and the Hawkes forecasts of recent Bluesky posts."""
    lines = []
    bt = backtest()
    t = track_line(bt).strip()
    lines.append(t or "No published posts with a reach number yet, so the score cannot be checked.")
    for p, b in bt.items():
        lines.append(f"- {p}: median real reach {b['median_actual_reach']:g} vs predicted {b['median_predicted_reach']:g} (real/predicted = {b['reach_ratio']}), score spread {b['score_spread']}")
    live = (config.load_json(config.DATA / LIVE_FILE, {}) or {}).get("posts", {})
    ok = [v for v in live.values() if v.get("status") == "ok"]
    if ok:
        lines.append("Bluesky growth forecast (Hawkes, likes + replies): " + "; ".join(f"{v['events']} so far, ~{v['expected_more']} more (branching {v['branching_ratio']})" for v in ok[:4]))
    elif live:
        lines.append(f"Bluesky growth forecast: {len(live)} recent posts, none with the {MIN_EVENTS}+ engagements the fit needs.")
    return lines
