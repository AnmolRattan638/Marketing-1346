"""Advisory pre-publish virality forecast (ViralSim, vendored in /viralsim).

It scores the final captions after fact-check and ad-review, stores the result on the draft and shows a short line in the Telegram message.
It NEVER blocks a post, rewrites a caption or chooses between drafts: the offline model is a coarse lexical heuristic (see viralsim/README.md,
"Read this before trusting a number"), and on this account the absolute reach it simulates is far above what 10 followers really get.
The numbers are saved next to the draft so they can later be compared with the real reach in data/analytics.json; until that comparison
exists, read the score as a rough ordering of drafts and the levers as writing hints, not as a prediction.
"""
import statistics
import unicodedata

from . import config

VERSION = 1
RUNS = 500                      # Monte-Carlo runs per platform: about half a second each, plenty for a coarse hint
PLATFORM_MAP = {"instagram": "instagram", "linkedin": "linkedin", "bluesky": "generic"}


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


def run(posts):
    """-> {"version", "scorer", "platforms": {name: {...}}, "note"}; raises on a real failure so the caller's stage() can report it."""
    from viralsim.pipeline import analyze
    analytics = config.load_json(config.DATA / "analytics.json", {}) or {}
    out = {}
    for name in config.PLATFORMS:
        text = plain(posts.get(name))
        if not text:
            continue
        r = analyze(text, creator=creator_for(name, analytics), platform=PLATFORM_MAP.get(name, "generic"), runs=RUNS, with_agents=False,
                    with_network=False, with_levers=(name == "instagram"), has_image=(name != "linkedin"))
        f = r["forecast"]
        levers = (r.get("suggestions") or {}).get("counterfactual") or []
        edits = (r.get("suggestions") or {}).get("text_edits") or []
        out[name] = {"score": r["viral_score"], "breakout_probability": round(f["viral_probability"], 3),
                     "reach_p10": f["reach_p10"], "reach_p50": f["reach_p50"], "reach_p90": f["reach_p90"],
                     "risk": r["risk"]["level"], "risk_issues": [str(i)[:120] for i in r["risk"]["issues"][:3]],
                     "levers": [{"title": x["title"], "lift_pct": x["lift_pct"]} for x in levers[:3]],
                     "edits": [{"title": x["title"], "impact": x.get("impact")} for x in edits[:3]],
                     "scorer": r["scorer"]}
    return {"version": VERSION, "platforms": out,
            "note": "advisory only; heuristic scorer; simulated reach is in model units, not a forecast for this account"}


def telegram_line(v):
    """One short block for the draft message ('' when there is nothing)."""
    pl = (v or {}).get("platforms") or {}
    if not pl:
        return ""
    scores = ", ".join(f"{n} {d['score']:.0f}" for n, d in pl.items())
    ig = pl.get("instagram") or {}
    hints = "; ".join(x["title"] for x in (ig.get("levers") or [])[:2] + (ig.get("edits") or [])[:1])
    risk = [f"{n}: {d['risk']}" for n, d in pl.items() if d.get("risk") not in (None, "none", "low")]
    return (f"Virality hint (0-100, coarse, advisory): {scores}" + (f"\nBacklash risk: {'; '.join(risk)}" if risk else "") +
            (f"\nCould lift Instagram: {hints}" if hints else "") + "\n")
