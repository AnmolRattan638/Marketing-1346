"""Offline tests for the idea bank (hook library, reel rules, post ideas adapted from vidIQ's public guidance): the bank obeys the
brand rules, used ideas are skipped, the prompts carry the new material, and a full daily run records which idea was used."""
import json, os, pathlib, re, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ.update(BUFFER_API_KEY="x", ZERNIO_API_KEY="y")
from src import config, ideas, llm, tg

# ------------------------------------------------------------------ the bank itself
b = ideas.bank()
svc_ids = {s["id"] for s in config.services()["services"]}
styles = {h["style"] for h in b["hook_library"]}
ids = [i["id"] for i in b["ideas"]]
assert len(ids) == len(set(ids)) >= 12 and len(b["hook_library"]) >= 8 and len(b["reel_rules"]) >= 5
assert svc_ids <= {i["service"] for i in b["ideas"]}, "every service has at least one idea"
BANNED = re.compile(r"\b(demo|sample|mock-?up|prototype|guarantee[sd]?|eliminat\w*|kills?|never lose|testimonial|free audit|discount|refund|100%)\b", re.I)
for i in b["ideas"]:
    assert {"id", "service", "format", "hook_style", "hook", "topic", "angle", "source"} <= set(i), i["id"]
    assert i["service"] in svc_ids | {"any"} and i["format"] in ("reel", "image", "any") and i["hook_style"] in styles, i["id"]
    assert len(i["hook"].split()) <= 12, f"hook too long ({len(i['hook'].split())} words): {i['hook']}"
    assert not BANNED.search(" ".join(str(v) for v in i.values()) ), f"idea breaks a brand rule: {i['id']}"
    assert "vidiq" in i["source"].lower()
assert not BANNED.search(json.dumps(b["hook_library"]) + json.dumps(b["reel_rules"]).replace("demo", "")), "library/rules text"

# ------------------------------------------------------------------ selection
pool = ideas.for_service("chatbot", set(), limit=10)
assert pool and all(i["service"] in ("chatbot", "any") for i in pool)
first = pool[0]["id"]
assert first not in [i["id"] for i in ideas.for_service("chatbot", {first})], "a used idea is skipped"
assert len(ideas.for_service("chatbot", set(), limit=2)) == 2
assert ideas.valid_id("bot-unanswered") == "bot-unanswered" and ideas.valid_id("made-up") is None and ideas.valid_id(None) is None
txt = ideas.ideas_text(pool)
assert "id=" + first in txt and "hook:" in txt and "comparison: X vs Y" in ideas.hooks_text() and "FIRST" not in ideas.rules_text()
assert "1 second" in ideas.rules_text() and "on mute" in ideas.rules_text()

# ------------------------------------------------------------------ history carries idea_id (so a used idea stays used)
tmp = pathlib.Path(tempfile.mkdtemp())
for n in ("drafts", "media"):
    (tmp / n).mkdir()
config.DATA, config.DRAFTS, config.MEDIA = tmp, tmp / "drafts", tmp / "media"
config.save_json(config.DRAFTS / "2026-10-01.json", {"date": "2026-10-01", "service": "chatbot", "topic": "old", "status": "rejected", "idea_id": "bot-repeat-questions"})
assert ideas.used_ids(config.history()) == {"bot-repeat-questions"}

# ------------------------------------------------------------------ a full daily run: offered, chosen, recorded, then not offered again
seen = {}
def plan(idea_id):
    return {"idea_id": idea_id, "topic": "t", "angle": "a", "key_points": ["x"], "hooks": [{"style": "comparison", "text": "Hook?"}], "chosen_hook": 0,
            "image_idea": "i", "ok": True, "issues": [], "revised": {}, "ad_score": 3, "notes": ""}
state = {"idea": "bot-unanswered"}
def groq(p, s="", **k):
    if "Hook library" in p:
        seen["analysis"] = p
        return json.dumps(plan(state["idea"]))
    return json.dumps(plan(state["idea"])) if "JSON" in p else "guidance"
def gemma(p, s="", **k):
    if "Propose 5 post topics" in p:
        seen["research"] = p
        return json.dumps({"topics": [{"topic": "t", "angle": "a", "why_it_matters": "w", "idea_id": state["idea"]}]})
    if "REEL RULES" in p:
        seen["reel"] = p
    return json.dumps({"topics": [{"topic": "t", "angle": "a", "why_it_matters": "w"}], "voiceover": "v", "shots": ["s"], "flow_prompt": "f"}) if "JSON" in p else "img prompt"
llm.groq, llm.gemma = groq, gemma
llm.gemini = lambda p, s="", **k: json.dumps({"instagram": "ig", "linkedin": "li", "bluesky": "bs", "replies": []})
tg.send = lambda text, buttons=None: None
tg.send_photo = lambda *a, **k: None
tg.chat_id = lambda: "1"
import src.agents.image as image_mod
image_mod.run = lambda plan, focus, date, guidance="": {"prompt": "p", "path": None}
from src import run_daily
run_daily.pick_focus = lambda brand, history: next(s for s in brand["services"] if s["id"] == "chatbot")
run_daily.main()
draft = config.load_json(config.DRAFTS / f"{run_daily.today}.json", None)
assert draft["idea_id"] == "bot-unanswered", draft.get("idea_id")
r = seen["research"]
assert "IDEA BANK" in r and "id=bot-unanswered" in r and "id=bot-repeat-questions" not in r, "an idea used by an earlier draft is not offered again"
assert "idea_id" in r and "no demos or samples" in r
a = seen["analysis"]
assert "comparison: X vs Y" in a and "idea_id" in a and "ONE specific promise" in a

yesterday = {**draft, "date": "2026-10-14", "status": "published"}        # next day: today's draft becomes yesterday's, its idea stays used
(config.DRAFTS / f"{run_daily.today}.json").unlink()
config.save_json(config.DRAFTS / "2026-10-14.json", yesterday)
seen.clear(); state["idea"] = "made-up-id"
run_daily.main()
assert "id=bot-unanswered" not in seen["research"], "yesterday's idea is not offered again"
assert config.load_json(config.DRAFTS / f"{run_daily.today}.json", None)["idea_id"] is None, "an id the model invented is not recorded"

# ------------------------------------------------------------------ reel prompt: 1-second hook, stacked first frame, loop ending
from src.agents import video
vp = {"topic": "t", "hooks": [{"text": "Hook?"}], "chosen_hook": 0}
video.run(vp, {"name": "Chatbot"}, {})
rp = seen["reel"]
assert "FIRST SECOND" in rp and "3-7 words" in rp and "hands back to the opening" in rp and "REEL RULES" in rp and "within 3 seconds" not in rp
# research without an idea pool must not mention the bank
from src.agents import research
seen.clear()
research.run({"positioning": "p"}, {"name": "x"}, [], "g", "2026-10-15")
assert "IDEA BANK" not in seen["research"]
print("ideas test passed: brand-safe bank, selection, used ideas skipped, prompts, end-to-end idea_id, reel rules")
