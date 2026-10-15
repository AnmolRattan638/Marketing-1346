"""Offline test: lead-gen posts speak to EVERY freelancer/agency, not to web developers. Other services are untouched."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import captions as C, llm
from src.agents import writer

ROOT = pathlib.Path(__file__).resolve().parent.parent
brand = json.load(open(ROOT / "config/services.json"))
ideas = json.load(open(ROOT / "config/ideas.json"))

# ---- 1. config: seller-neutral pitch + the audience rule every agent receives
lg = next(s for s in brand["services"] if s["id"] == "lead_gen")
assert "ANY freelancer or agency" in lg["pitch"] and "web developer" not in lg["pitch"].lower()
rule = next(r for r in brand["facts_rules"] if r.startswith("LEAD GEN AUDIENCE"))
assert "web developer" in rule and "#WebDeveloper" in rule and "Do not invent" in rule
where = next(i for i in ideas["ideas"] if i["id"] == "leads-where")
assert "no website" not in where["angle"].lower() and "every freelancer and agency" in where["angle"]

# ---- 2. the writer gets the audience block for lead_gen ONLY
plan = {"hooks": [{"text": "Hook text"}], "chosen_hook": 0, "topic": "t", "angle": "a", "key_points": []}
seen = []
llm.gemini = lambda prompt, system="", **k: seen.append(prompt) or json.dumps({"instagram": "**H** ok", "linkedin": "L", "bluesky": "B", "replies": []})
writer.run(plan, {"id": "lead_gen", "name": "Lead generation", "dm_keyword": "LEADS"}, brand, "VOICE", "g")
assert "LEAD GEN AUDIENCE" in seen[0] and "ANY freelancer" in seen[0] and "never #WebDeveloper" in seen[0], seen[0][-1500:]
seen.clear()
writer.run(plan, {"id": "chatbot", "name": "Chatbot", "dm_keyword": "BOT"}, brand, "VOICE", "g")
assert "LEAD GEN AUDIENCE (this post only" not in seen[0]

# ---- 3. hashtag safety net: the exact tags from the caption you reported
caption = "**HOOK**\n\n→ line\n\nDM **LEADS** and tell me what you sell.\n\n#FreelanceIndia #AgencyLife #SmallBusinessIndia #WebDeveloper"
fixed = C.widen_lead_hashtags(caption)
tags = fixed.splitlines()[-1].split()
low = [t.lower() for t in tags]
assert "#webdeveloper" not in low and "#agencylife" not in low and 4 <= len(tags) <= 5, tags
assert "#freelanceindia" in low and "#smallbusinessindia" in low and "#leadgeneration" in low, tags
assert fixed.startswith("**HOOK**") and "DM **LEADS**" in fixed                     # body untouched
assert C.widen_lead_hashtags(fixed) == fixed                                         # idempotent
assert C.widen_lead_hashtags("Body only")[-60:].count("#") >= 4                      # no tags at all -> broad tags added
# only for lead_gen: any other focus keeps its hashtags exactly as written
other = C.finalize_posts({"instagram": caption}, focus_id="chatbot")["instagram"]
assert "#WebDeveloper" in other and other == C.finalize_posts({"instagram": caption})["instagram"]
lead = C.finalize_posts({"instagram": caption, "linkedin": "L", "bluesky": "B"}, focus_id="lead_gen")
assert "#WebDeveloper" not in lead["instagram"] and lead["linkedin"] == "L" and lead["bluesky"] == "B"
print("lead gen reach test passed: any freelancer/agency, writer block only for lead_gen, narrow hashtags removed, other services unchanged")
