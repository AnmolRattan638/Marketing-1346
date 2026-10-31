"""Offline tests for the advisory virality hint: real account size goes in, bold letters are normalised, output is stored-ready, nothing can block a post."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import config, virality

tmp = pathlib.Path(tempfile.mkdtemp())
config.DATA = tmp
(tmp / "analytics.json").write_text(json.dumps({
    "accounts": {"instagram": {"followers": 10}, "linkedin": {"followers": 2}, "bluesky": {"followers": 1, "following": 5}},
    "posts": [{"platform": "instagram", "metrics": {"reach": 4}}, {"platform": "instagram", "metrics": {"reach": 8}}, {"platform": "linkedin", "metrics": {"impressions": 50}}]}))

assert virality.plain("**𝗪𝗛𝗔𝗧𝗦𝗔𝗣𝗣** chats  𝘃𝘀 site") == "WHATSAPP chats vs site", virality.plain("**𝗪𝗛𝗔𝗧𝗦𝗔𝗣𝗣** chats  𝘃𝘀 site")

a = json.loads((tmp / "analytics.json").read_text())
ig, li, bs = (virality.creator_for(p, a) for p in ("instagram", "linkedin", "bluesky"))
assert ig.followers == 10 and ig.monthly_reach == 6 * 30, (ig.followers, ig.monthly_reach)          # mean reach 6 per post x 30 posts a month
assert li.monthly_reach == 50 * 30 and bs.followers == 1 and bs.following == 5
assert virality.creator_for("instagram", {}).followers == 1.0                                         # no analytics yet: tiny account, never the model's default of 1,000

posts = {"instagram": "𝗪𝗛𝗔𝗧𝗦𝗔𝗣𝗣 𝗩𝗦 𝗪𝗘𝗕𝗦𝗜𝗧𝗘: which saves more time?\n\n→ Stop sending the same details to every customer.\n→ Clear info on one page.\n\nDM SITE for a quick look.\n\n#SmallBusinessIndia",
         "linkedin": "Sending your details on WhatsApp every day costs more time than you think. A single page answers the same questions for you.",
         "bluesky": "WhatsApp chats vs a one-page site: which saves more time? DM SITE."}
v = virality.run(posts)
assert v["version"] == virality.VERSION and set(v["platforms"]) == set(config.PLATFORMS), v["platforms"].keys()
for name, d in v["platforms"].items():
    assert 0 <= d["score"] <= 100 and d["reach_p10"] <= d["reach_p50"] <= d["reach_p90"] and d["scorer"] == "heuristic", (name, d)
assert v["platforms"]["instagram"]["levers"] and "levers" in v["platforms"]["linkedin"] and not v["platforms"]["linkedin"]["levers"]
json.dumps(v)                                                                                       # stored on the draft, so it must be plain JSON
line = virality.telegram_line(v)
assert line.startswith("Virality hint") and "advisory" in line and "instagram" in line, line
assert virality.telegram_line({}) == "" and virality.telegram_line(None) == ""

assert virality.run({"instagram": "", "linkedin": "", "bluesky": ""})["platforms"] == {}              # nothing to score is not an error

print("virality test passed: real account size, bold normalised, per-platform output, JSON-safe, Telegram line, empty input")
