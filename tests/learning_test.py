"""Offline test of the learning loop: posts are joined to what was tested and frozen at 48h, scored against the account's own median,
weak posts are diagnosed (distribution / hook / value), the problem bank gets statuses, one variable changes per experiment,
the weekly review reports missing numbers, and a full daily run records the experiment on the draft."""
import datetime as dt, hashlib, json, pathlib, re, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import analytics, config, learning, llm, tg

ROOT = config.ROOT
UTC = dt.timezone.utc
tmp = pathlib.Path(tempfile.mkdtemp())
for n in ("drafts", "media"):
    (tmp / n).mkdir()
config.DATA, config.DRAFTS, config.MEDIA = tmp, tmp / "drafts", tmp / "media"


def draft(date, problem, angle="how_to", hook="question", exp=None):
    d = {"id": f"{date}-x", "date": date, "status": "published", "service": "lead_gen", "topic": f"t {date}", "problem_id": problem, "angle_type": angle,
         "hook_style": hook, "experiment": exp, "image": {"style_id": "network"},
         "posts": {"instagram": f"Instagram caption for {date} about lead hunting every morning", "linkedin": f"LinkedIn post for {date}: a plain sentence about finding clients",
                   "bluesky": f"Bluesky text for {date}"},
         "results": {p: {"ok": True} for p in ("instagram", "linkedin", "bluesky")}}
    config.save_json(config.DRAFTS / f"{date}.json", d)


def row(date, plat, reach, likes, skip=None):
    m = {k: None for k in analytics.METRICS}
    m.update(reach=reach, impressions=reach, likes=likes, comments=0, shares=0, saves=0, skip_rate=skip)
    return {"platform": plat, "id": f"{plat}-{date}", "url": "u", "published_at": f"{date}T09:00:00+00:00", "text": "x", "format": "image", "source": "zernio",
            "metrics": m, "matched": {"date": date, "service": "lead_gen", "hook_style": "question", "topic": "t"}}


PLAN = [("2026-10-01", 100, 5, .4), ("2026-10-02", 100, 5, .4), ("2026-10-03", 100, 5, .4), ("2026-10-04", 100, 5, .4),
        ("2026-10-05", 300, 15, .4), ("2026-10-06", 30, 2, .4), ("2026-10-07", 100, 0, .4), ("2026-10-08", 100, 5, .9), ("2026-10-11", 100, 5, .4)]
for date, *_ in PLAN:
    draft(date, "p-" + date[-2:])
rows = [row(d, "instagram", r, l, s) for d, r, l, s in PLAN]
accounts = {"instagram": {"followers": 9}, "linkedin": {"followers": 1}}
data = {"posts": rows, "accounts": accounts}
now_a = dt.datetime(2026, 10, 12, 6, tzinfo=UTC)

# ---- 1. join + freeze
res = learning.update_results(data, now_a)
assert sorted(k.split("|")[0] for k in res["posts"]) == [p[0] for p in PLAN[:8]], "the 10-11 post is only 21 hours old: not judged yet"
r1 = res["posts"]["2026-10-01|instagram"]
assert r1["image_style"] == "network" and r1["problem_id"] == "p-01" and r1["angle_type"] == "how_to" and r1["hook_style"] == "question" and r1["cta"] == "none" and r1["snap"]["48h"]["likes"] == 5
assert "7d" in res["posts"]["2026-10-04|instagram"]["snap"] and "7d" not in res["posts"]["2026-10-05|instagram"]["snap"]
before = (tmp / "post_results.json").read_text()
learning.update_results(data, now_a)
assert (tmp / "post_results.json").read_text() == before, "nothing changed: the file is not rewritten (no commit noise)"
rows[0]["metrics"]["likes"] = 9                                  # the post keeps collecting likes
res = learning.update_results(data, dt.datetime(2026, 10, 13, 6, tzinfo=UTC))
r1 = res["posts"]["2026-10-01|instagram"]
assert r1["snap"]["48h"]["likes"] == 5 and r1["latest"]["likes"] == 9, "the 48h reading stays frozen, latest moves"
assert res["posts"]["2026-10-05|instagram"]["snap"]["7d"]["likes"] == 15, "the 7d reading appears once the post is a week old"
rows[0]["metrics"]["likes"] = 5

# ---- 2. screenshots: fill what the API cannot see, never overwrite what it reported
config.save_json(tmp / "manual_analytics.json", {"entries": [
    {"captured_at": "2026-10-12T05:00:00+00:00", "platform": "linkedin", "screen": "post", "account": {},
     "posts": [{"post_hint": "LinkedIn post for 2026-10-03: a plain sentence about finding", "metrics": {"impressions": 40, "likes": 2}}]},
    {"captured_at": "2026-10-12T05:05:00+00:00", "platform": "instagram", "screen": "retention", "account": {},
     "posts": [{"post_hint": "𝗜𝗻𝘀𝘁𝗮𝗴𝗿𝗮𝗺 caption for 2026-10-02 about lead hunting", "metrics": {"skip_rate": 0.1, "avg_watch_s": 6.5}},
               {"post_hint": "a post that was never published by this pipeline", "metrics": {"likes": 99}}]}]})
res = learning.update_results(data, now_a)
li = res["posts"]["2026-10-03|linkedin"]
assert li["snap"]["48h"]["impressions"] == 40 and li["snap"]["48h"]["source"] == "screenshot", "a Buffer-published LinkedIn post gets numbers from a screenshot"
ig = res["posts"]["2026-10-02|instagram"]["snap"]["48h"]
assert ig["skip_rate"] == 0.4 and ig["avg_watch_s"] == 6.5, "API value kept, missing retention number filled from the screenshot"
assert len(res["posts"]) == 9, "an unmatched screenshot row is ignored"

# ---- 3. scoring against the account's own median + diagnosis
scored = learning.score_all(res, accounts)
by = {(s["date"], s["platform"]): s for s in scored}
w = by[("2026-10-05", "instagram")]
assert w["verdict"] == "winner" and w["composite"] >= 1.5, w
assert by[("2026-10-06", "instagram")]["diagnosis"] == "distribution" and by[("2026-10-06", "instagram")]["verdict"] == "weak"
assert by[("2026-10-07", "instagram")]["diagnosis"] == "value"
assert by[("2026-10-08", "instagram")]["diagnosis"] == "hook", by[("2026-10-08", "instagram")]
avg = by[("2026-10-02", "instagram")]
assert avg["verdict"] == "average" and avg["confidence"] == "low", avg
assert by[("2026-10-03", "linkedin")]["verdict"] == "not_enough_data" and by[("2026-10-03", "linkedin")]["composite"] is None, "one LinkedIn post has no baseline to be judged against"

# ---- 4. the problem bank: statuses
def sc(date, pid, comp, diag, angle="story", hook="question"):
    return {"date": date, "platform": "instagram", "service": "lead_gen", "problem_id": pid, "angle_type": angle, "hook_style": hook, "variable": None, "mode": None,
            "composite": comp, "diagnosis": diag, "verdict": "x", "components": {}, "peers": 5, "confidence": "ok", "format": "image", "cta": "dm", "key": date}


def prob(pid, text):
    return {"id": pid, "service": "lead_gen", "problem": text, "added": "2026-10-01", "status": "untested", "tests": 0, "mean": None,
            "frustration": "f", "desired_outcome": "o", "audience_phrase": "ap", "objection": "ob", "common_mistake": "cm"}


bank = {"problems": [prob("win", "Winner problem text here"), prob("prom", "Promising problem text"), prob("dud", "Dud problem text here"),
                     prob("dist", "Nobody saw it problem"), prob("one", "Mixed single test"), prob("new", "Brand new problem text")]}
S = [sc("2026-10-01", "win", 1.6, "worked", "how_to", "question"), sc("2026-10-02", "win", 1.3, "ok", "story", "top3"), sc("2026-10-03", "prom", 1.8, "worked", "story", "question"),
     sc("2026-10-04", "dud", 0.5, "hook"), sc("2026-10-05", "dud", 0.6, "value"), sc("2026-10-06", "dist", 0.4, "distribution"), sc("2026-10-07", "dist", 0.5, "distribution"),
     sc("2026-10-08", "one", 1.0, "ok")]
learning.refresh_bank(bank, S)
st = {p["id"]: p["status"] for p in bank["problems"]}
assert st == {"win": "winner", "prom": "promising", "dud": "dud", "dist": "testing", "one": "testing", "new": "untested"}, st
assert {p["id"]: p["tests"] for p in bank["problems"]}["win"] == 2 and bank["problems"][0]["mean"] == 1.45

# ---- 5. next experiment: one variable at a time, mostly exploit, explore about 1 in 3
e = learning.next_experiment("lead_gen", bank, S, 0)
assert e["mode"] == "exploit" and e["problem_id"] == "prom" and e["variable"] == "hook_style", e
assert e["hook_style"] != "question" and "question" in e["avoid_hook_styles"] and e["angle_type"] == "story", "same problem, new hook style, angle kept"
e = learning.next_experiment("lead_gen", bank, S, 2)
assert e["mode"] == "explore" and e["problem_id"] == "new" and e["variable"] == "problem" and e["hook_style"] == "top3", "every third post tests a new problem with the best known hook style (top3 1.3x beats question 0.9x)"
e = learning.next_experiment("lead_gen", bank, S, 0, avoid=("prom",))
assert e["problem_id"] == "win" and e["variable"] == "angle_type" and e["angle_type"] not in ("how_to", "story"), e
e = learning.next_experiment("lead_gen", bank, S, 0, avoid=("prom", "win"))
assert e["problem_id"] in ("prom", "win"), "avoiding recent problems never leaves the pipeline without an experiment"
only_new = {"problems": [prob("new", "Brand new problem text")]}
assert learning.next_experiment("lead_gen", only_new, [], 0)["mode"] == "explore"
assert learning.next_experiment("lead_gen", {"problems": []}, [], 0) is None
assert learning.next_experiment("lead_gen", {"problems": [dict(prob("d", "x" * 10), status="dud")]}, [], 0) is None
assert learning.next_experiment("website", bank, S, 0) is None, "problems belong to a service"
txt = learning.directive_text(learning.next_experiment("lead_gen", bank, S, 0))
assert "EXPERIMENT" in txt and "id=prom" in txt and "Change ONLY this variable" in txt and "hook_style" in txt and "problem_id" in txt and "no invented statistics" in txt

# ---- 6. bank upkeep
b = {"problems": []}
n = learning.add_problems(b, "lead_gen", [{"problem": "Finding clients takes hours every single morning"}, {"problem": "every single morning finding clients takes hours"},
                                          {"problem": "Prospects never reply to cold messages"}, {"problem": "x"}, {"problem": "Prospects never reply to cold messages!"}], "2026-10-15")
assert n == 2 and [p["status"] for p in b["problems"]] == ["untested", "untested"] and len({p["id"] for p in b["problems"]}) == 2, "near-duplicates skipped"
assert learning.needs_research(b, "lead_gen") is False and learning.needs_research(b, "website") is True and learning.needs_research({"problems": b["problems"][:1]}, "lead_gen") is True
old = learning.MAX_PROBLEMS
learning.MAX_PROBLEMS = 2
assert learning.add_problems(b, "lead_gen", [{"problem": "A completely different third problem"}], "2026-10-15") == 0
learning.MAX_PROBLEMS = old

# ---- 7. the digest the strategist reads
d = learning.digest_text(scored, bank, accounts)
assert "Image styles: network" in d and d.startswith("LEARNING LOOP") and "low confidence" in d and "Hook styles" in d and len(d) <= 1100, d
assert learning.digest_text([], bank, accounts) == ""

# ---- 8. weekly review: summary, notes file, missing numbers, no prompt or rule is touched
from src import weekly_review
config.save_json(tmp / "analytics.json", {"posts": rows, "accounts": accounts})
guard = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in ("config/voice.md", "config/services.json", "config/ideas.json")}
config.save_json(tmp / "problem_bank.json", bank)
text = weekly_review.build(dt.datetime(2026, 10, 13, 6, tzinfo=UTC))
assert len(text) <= 3800 and "Weekly learning review" in text and "THIS WEEK" in text and "PROBLEM BANK" in text and "NEXT EXPERIMENTS" in text, text
assert "MISSING NUMBERS" in text and 'caption "stats linkedin"' in text, "published LinkedIn posts without numbers are listed with what to send"
assert "distribution" in text and "worked" in text
notes = (tmp / "learning_notes.md").read_text()
assert "ALL SCORED POSTS" in notes and "2026-10-06 instagram" in notes
assert {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in guard} == guard, "the weekly review never edits prompts, rules or ideas"

# ---- 9. a full daily run: research tops up the bank, the experiment reaches the analysis prompt, the draft records it
for f in list(tmp.glob("*.json")) + list(config.DRAFTS.glob("*.json")):
    f.unlink()
seen, sent, mode, events = {}, [], {"echo": True}, []
PROBLEMS = {"problems": [{"problem": t, "frustration": "f", "desired_outcome": "o", "audience_phrase": "ap", "common_mistake": "cm", "objection": "ob", "emotional_reason": "er"}
                         for t in ("Customers message at night and nobody replies", "Leads go cold because follow up takes days", "Nobody knows what to post every week")]}


def plan_json(p):
    m = re.search(r"EXPERIMENT.*?id=(\S+):", p, re.S)
    pid = (m.group(1) if mode["echo"] else "made-up-id") if m else None
    return {"idea_id": None, "problem_id": pid, "angle_type": "story", "topic": "t", "angle": "a", "key_points": ["x"], "hooks": [{"style": "question", "text": "Hook?"}],
            "chosen_hook": 0, "image_idea": "i", "ok": True, "issues": [], "revised": {}, "ad_score": 3, "notes": ""}


def groq(p, s="", **k):
    if "Hook library" in p:
        seen["analysis"] = p
        return json.dumps(plan_json(p))
    return json.dumps(plan_json(p)) if "JSON" in p else "guidance"


def gemma(p, s="", **k):
    if "List 6 DIFFERENT" in p:
        seen["problems"] = p
        return json.dumps(PROBLEMS)
    if "Propose 5 post topics" in p:
        seen["research"] = p
        return json.dumps({"topics": [{"topic": "t", "angle": "a", "why_it_matters": "w"}]})
    return json.dumps({"topics": [{"topic": "t", "angle": "a", "why_it_matters": "w"}], "voiceover": "v", "shots": ["s"], "flow_prompt": "f"}) if "JSON" in p else "img prompt"


llm.groq, llm.gemma = groq, gemma
llm.gemini = lambda p, s="", **k: json.dumps({"instagram": "ig", "linkedin": "li", "bluesky": "bs", "replies": []})
tg.send = lambda text, buttons=None: (sent.append(text), events.append(("text", text)))
tg.send_photo = lambda path, caption="": events.append(("photo", caption))
tg.chat_id = lambda: "1"
import src.agents.image as image_mod
image_mod.run = lambda plan, focus, date, guidance="": {"prompt": "p", "path": None}
from src import run_daily
run_daily.pick_focus = lambda brand, history: next(s for s in brand["services"] if s["id"] == "lead_gen")
run_daily.main()
dpath = config.DRAFTS / f"{run_daily.today}.json"
dr = config.load_json(dpath, None)
bank = config.load_json(tmp / "problem_bank.json", {})
assert len(bank["problems"]) == 3 and "audience: " not in seen["problems"] and "ANY freelancer" in seen["problems"], "the bank was researched once and saved"
exp = dr["experiment"]
assert exp["mode"] == "explore" and exp["variable"] == "problem" and dr["problem_id"] == exp["problem_id"] and dr["problem_id"] in {p["id"] for p in bank["problems"]}, dr
assert dr["angle_type"] == "story" and "EXPERIMENT" in seen["analysis"] and "Change ONLY" in seen["analysis"] and "EXPERIMENT" in seen["research"]
assert any("Experiment: explore (changing only: problem)" in t for t in sent), "the Telegram draft says what is being tested"
assert events[-1][0] == "text" and "Approve" in events[-1][1] and events[-2][0] == "photo" and events[-2][1].startswith("[SERVICE EXPLAINER]"), "the explainer image comes right before the Approve message"
dpath.unlink()                                                   # a second run does not research again, and a post that ignores the experiment is not counted
sent.clear(); seen.clear(); mode["echo"] = False
run_daily.main()
dr = config.load_json(dpath, None)
assert "problems" not in seen and dr["problem_id"] is None and dr["experiment"] is None, "not counted as a test"
assert any("did not follow today's experiment" in t for t in sent)
print("learning test passed: join + freeze, screenshots, scoring, diagnosis, bank, one-variable experiments, weekly review, end-to-end daily run")
