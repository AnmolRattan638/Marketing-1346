"""Offline tests for the advisory virality hint: real account size goes in, bold letters are normalised, output is stored-ready, agents + network + hook A/B,
the backtest against real reach, the Hawkes forecast from Bluesky timestamps (fake API), and nothing here can block a post."""
import datetime as dt, json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import config, llm, virality

tmp = pathlib.Path(tempfile.mkdtemp()); (tmp / "drafts").mkdir()
config.DATA, config.DRAFTS = tmp, tmp / "drafts"
NOW = dt.datetime(2026, 11, 1, 12, 0, tzinfo=dt.timezone.utc)
iso = lambda h: (NOW - dt.timedelta(hours=h)).isoformat().replace("+00:00", "Z")
URI = "at://did:plc:x/app.bsky.feed.post/abc"
(tmp / "analytics.json").write_text(json.dumps({
    "accounts": {"instagram": {"followers": 10}, "linkedin": {"followers": 2}, "bluesky": {"followers": 1, "following": 5}},
    "posts": [{"platform": "instagram", "metrics": {"reach": 4}}, {"platform": "instagram", "metrics": {"reach": 8}}, {"platform": "linkedin", "metrics": {"impressions": 50}},
              {"platform": "bluesky", "id": URI, "url": "https://bsky.app/x", "published_at": iso(30)}]}))

assert virality.plain("**𝗪𝗛𝗔𝗧𝗦𝗔𝗣𝗣** chats  𝘃𝘀 site") == "WHATSAPP chats vs site"
a = json.loads((tmp / "analytics.json").read_text())
ig, li, bs = (virality.creator_for(p, a) for p in ("instagram", "linkedin", "bluesky"))
assert ig.followers == 10 and ig.monthly_reach == 6 * 30 and li.monthly_reach == 50 * 30 and bs.followers == 1 and bs.following == 5
assert virality.creator_for("instagram", {}).followers == 1.0                      # no analytics yet: tiny account, never the model's default of 1,000

posts = {"instagram": "𝗪𝗛𝗔𝗧𝗦𝗔𝗣𝗣 𝗩𝗦 𝗪𝗘𝗕𝗦𝗜𝗧𝗘: which saves more time?\n\n→ Stop sending the same details to every customer.\n→ Clear info on one page.\n\nDM SITE for a quick look.\n\n#SmallBusinessIndia",
         "linkedin": "Sending your details on WhatsApp every day costs more time than you think. A single page answers the same questions for you.",
         "bluesky": "WhatsApp chats vs a one-page site: which saves more time? DM SITE."}
hooks = [{"style": "top3", "text": "Shop owners: 3 page details that stop customers from ghosting you"},
         {"style": "comparison", "text": "Website info vs WhatsApp replies: which saves you more hours?"},
         {"style": "myth", "text": "Myth: Google listing guarantees calls. Fact: No contact info = lost leads"}]
v = virality.run(posts, hooks, 1)
assert v["version"] == virality.VERSION and set(v["platforms"]) == set(config.PLATFORMS)
for name, d in v["platforms"].items():
    assert 0 <= d["score"] <= 100 and d["reach_p10"] <= d["reach_p50"] <= d["reach_p90"] and d["scorer"] == "heuristic", (name, d)
    assert d["agents"]["engagement_rate"] is not None and d["network"]["reach_fraction"] is not None, (name, d)       # crowd agents + cascade ran
assert v["platforms"]["instagram"]["levers"] and not v["platforms"]["linkedin"]["levers"]
ab = v["ab"]
assert ab["chosen"] == 1 and len(ab["vs_chosen"]) == 2 and ab["advisory"] and {x["hook"] for x in ab["vs_chosen"]} == {0, 2}, ab
assert all(0 <= x["p_beats_chosen"] <= 1 for x in ab["vs_chosen"]) and ab["better"] in (None, 0, 2)
assert virality.ab_hooks([hooks[0]], 0, ig) is None and virality.ab_hooks(hooks, 7, ig) is None and virality.ab_hooks([{"text": ""}, {"text": "x"}], 0, ig) is None
assert virality.run(posts, None)["ab"] is None                                       # no hooks given: forecast still works
json.dumps(v)                                                                        # stored on the draft, so it must be plain JSON

# ---- backtest: stored predictions are used, old drafts are scored from their caption, Bluesky (no reach number) is skipped
def draft(date, status="published"):
    (tmp / "drafts" / f"{date}.json").write_text(json.dumps({"date": date, "status": status, "posts": posts}))
res = {}
for i in range(1, 10):
    date = f"2026-10-{i:02d}"; draft(date)
    res[f"{date}|instagram"] = {"latest": {"reach": 4 * i, "likes": 1}}
    res[f"{date}|bluesky"] = {"latest": {"likes": 0, "comments": 0, "shares": 0}}
draft("2026-10-20", "rejected"); res["2026-10-20|instagram"] = {"latest": {"reach": 999}}
(tmp / "post_results.json").write_text(json.dumps({"posts": res}))
bt = virality.backtest(runs=100)
assert set(bt) == {"instagram"} and bt["instagram"]["n"] == 9, bt                     # rejected draft and no-reach Bluesky not counted
assert bt["instagram"]["verdict"].startswith("no spread") and bt["instagram"]["reach_ratio"] > 0, bt                      # same caption nine times: the scores cannot differ
assert json.loads((tmp / "post_results.json").read_text()) and json.loads((tmp / "virality_backtest.json").read_text())["platforms"]["instagram"]["n"] == 9
for f in list((tmp / "drafts").glob("*.json"))[3:]:
    f.unlink()
assert virality.backtest(runs=100)["instagram"]["verdict"] == "too early"             # fewer than 8 posts: no verdict
assert virality.backtest(runs=100, write=False) and virality._spearman([1, 1, 1], [1, 2, 3]) == (None, None)
rho, p = virality._spearman([1, 2, 3, 4, 5], [2, 4, 5, 8, 9]); assert abs(rho - 1.0) < 1e-9
line = virality.track_line({"instagram": {"n": 11, "spearman": 0.36, "p_value": 0.27, "verdict": "no signal"}})
assert "n=11" in line and "no signal" in line and "Do not act" in line and virality.track_line({}) == ""

# ---- Hawkes live forecast from a fake Bluesky API
class R:
    def __init__(s, j, code=200): s.j, s.status_code = j, code
    def json(s): return s.j
likes = [{"createdAt": iso(30 - h)} for h in (0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 3.0, 6.0)]
replies = [{"post": {"record": {"createdAt": iso(30 - 0.4)}}}]
def get(url, params=None, timeout=0):
    return R({"likes": likes, "cursor": None}) if url.endswith("getLikes") else R({"thread": {"replies": replies}})
live = virality.live_forecast(get=get, now=NOW)
rec = live[URI]
assert rec["status"] == "ok" and rec["events"] == 10 and 0 < rec["branching_ratio"] < 1 and rec["expected_more"] >= 0, rec
assert json.loads((tmp / "virality_live.json").read_text())["posts"][URI]["events"] == 10
few = virality.live_forecast(get=lambda url, params=None, timeout=0: R({"likes": likes[:2]}) if url.endswith("getLikes") else R({}, 404), now=NOW)
assert few[URI]["status"] == "too few events" and few[URI]["events"] == 2, few
boom = virality.live_forecast(get=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network down")), now=NOW)
assert boom[URI]["status"].startswith("failed")                                       # a dead API must not raise
assert virality.live_forecast(get=get, now=NOW + dt.timedelta(days=30)) == {}          # older than 14 days: skipped

# ---- Telegram block + weekly review text
bt = {"instagram": {"n": 11, "spearman": 0.36, "p_value": 0.27, "verdict": "no signal"}}
line = virality.telegram_line(v, bt)
assert line.startswith("Virality hint") and "advisory" in line and "Hook A/B" in line and "Crowd sim" in line and "Track record" in line, line
assert len(line) < 1200, len(line)
assert virality.telegram_line({}) == "" and virality.telegram_line(None) == ""
assert virality.run({"instagram": "", "linkedin": "", "bluesky": ""})["platforms"] == {}
rl = "\n".join(virality.review_lines())
assert "Track record" in rl or "too early" in rl or "No published" in rl, rl

# ---- Groq client: only scoring + backlash audit, budget, two-failure breaker, honest labels, never raises anything but ValueError
import os
calls = []
llm._groq = lambda prompt, system="", model=None, temperature=0.6: calls.append(system) or json.dumps({"dims": {d: 7 for d in ("humor", "curiosity", "educational", "novelty", "controversy", "emotional_intensity", "relatability", "practical_value")}, "topics": ["business"], "entities": [], "issues": []})
g = virality.GroqClient(budget=3)
def refused(fn):
    try: fn()
    except ValueError: return True
    return False
assert refused(lambda: g.complete("You act as a user", "x")) and not calls and g.left == 3            # crowd-agent calls are refused without spending anything
assert g.complete("You are a calibrated content-analysis engine.", "x") and g.complete("You are a cultural sensitivity analyst.", "x") and g.log == ["score", "risk"]
assert g.complete("You are a calibrated content-analysis engine.", "x") and refused(lambda: g.complete("You are a calibrated content-analysis engine.", "x")), "budget of 3 holds"
def dead(*a, **k): raise RuntimeError("groq 503")
llm._groq = dead
g2 = virality.GroqClient()
assert all(refused(lambda: g2.complete("You are a calibrated content-analysis engine.", "x")) for _ in range(3)) and g2.fails == 2 and g2.left == 14, "breaker stops calling after two failures"
v2 = virality.run(posts, hooks, 1, llm=g2)
assert {d["scorer"] for d in v2["platforms"].values()} == {"heuristic"}, "a client that never answered must not be reported as an LLM score"
llm._groq = lambda prompt, system="", model=None, temperature=0.6: json.dumps({"dims": {d: 7 for d in ("humor", "curiosity", "educational", "novelty", "controversy", "emotional_intensity", "relatability", "practical_value")}, "topics": ["business"], "entities": [], "issues": []})
g3 = virality.GroqClient()
v3 = virality.run(posts, hooks, 1, llm=g3)
assert {d["scorer"] for d in v3["platforms"].values()} == {"llm"} and g3.calls == 6 and g3.left == 10, (g3.calls, g3.left)   # 3 platforms x (rubric + backlash audit), agents untouched
os.environ.pop("GROQ_API_KEY", None); assert virality.make_llm() is None
os.environ["GROQ_API_KEY"] = "k"; assert isinstance(virality.make_llm(), virality.GroqClient)
config.VIRALITY_LLM = False; assert virality.make_llm() is None; config.VIRALITY_LLM = True
os.environ.pop("GROQ_API_KEY")

# ---- the report the strategist reads, and the Telegram wording of the one rewrite
dg = virality.digest(v3, {"instagram": {"n": 11, "spearman": 0.36, "p_value": 0.27, "verdict": "no signal"}})
assert dg.startswith("VIRALITY REPORT") and "instagram: score" in dg and "weakest dimensions" in dg and "hook A/B" in dg and "no signal" in dg and "own judgement" in dg, dg
assert "has not been checked" in virality.digest(v3, {}) and virality.digest({}, {}) == ""
s = virality.review_summary({"rewrote": True, "reasons": ["it read like an ad"], "changes": ["instagram: sharper first line"]}, {"platforms": {"instagram": {"score": 10.2}}}, {"platforms": {"instagram": {"score": 12.6}}})
assert s["before"] == {"instagram": 10.2} and s["after"] == {"instagram": 12.6}
t = virality.telegram_line(v3, None, s)
assert "Rewritten ONCE" in t and "instagram 10.2 -> 12.6" in t and "sharper first line" in t, t
assert "No rewrite: the strategist saw nothing" in virality.telegram_line(v3, None, {"rewrote": False, "reasons": [], "changes": [], "before": {}, "after": {}})
assert "came back unchanged" in virality.telegram_line(v3, None, {"rewrote": False, "reasons": ["it read like an ad"], "changes": [], "before": {}, "after": {}})
assert "Rewritten" not in virality.telegram_line(v3, None, None) and "No rewrite" not in virality.telegram_line(v3, None, None)

print("virality test passed: real account size, bold normalised, agents + cascade, hook A/B, backtest verdicts, Hawkes (fit, too few events, dead API), Telegram block, review text")
