"""Offline test: the LinkedIn fix changes LinkedIn ONLY. Instagram and Bluesky keep their Unicode-bold/arrow format."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import captions, llm, run_daily
from src.agents import linkedin_edit

# ---- 1. formatting: Instagram + Bluesky unchanged, LinkedIn plain
raw = {"instagram": "**HOOK HERE**\n\n→ line one with **KEY** word\n\nDM **BOT**\n\n#a #b",
       "bluesky": "**BIG** idea, DM me",
       "linkedin": "**BLANK SCREEN STOPS POSTING CONSISTENCY**\n\n→ Script gives direction.\n\n• Another point with **KEYWORD** here.\n\nDM **SCRIPT** and tell me what you sell"}
out = captions.finalize_posts(raw)
assert out["instagram"] == captions.finalize(raw["instagram"]) and "→" in out["instagram"] and "\U0001D5DB" in out["instagram"]
assert out["bluesky"] == captions.finalize(raw["bluesky"]) and "\U0001D5D5" in out["bluesky"]
li = out["linkedin"]
assert not any(0x1D5D4 <= ord(c) <= 0x1D7FF for c in li), li       # no Unicode bold
assert "→" not in li and "•" not in li and "**" not in li, li
assert li.splitlines()[0] == "Blank screen stops posting consistency", li
assert "DM SCRIPT" in li, li                                         # DM keyword keeps its capitals
assert captions.finalize_posts({**raw, "linkedin": li})["linkedin"] == li      # idempotent
assert captions.finalize_linkedin("\U0001D5D7\U0001D5E0 \U0001D5D5\U0001D5E2\U0001D5E7 and \U0001D7EE points") == "DM BOT and 2 points"

# ---- 2. the LinkedIn editor only replaces the LinkedIn text, and only with something usable
bad = "BLANK SCREEN STOPS POSTING\n\n→ One script structure hooks value CTA in split screen example only.\n\nDM SCRIPT"
good = ("Most reels fail in the first three seconds because there is no clear opening line.\n\n"
        "A short script fixes that. Write the hook first, then one point, then one next step for the viewer.\n\n"
        "Owners who post without a script often run out of ideas by the second week, which is why the posting stops.\n\n"
        "Try it for one reel this week and see how much faster filming goes.\n\nDM SCRIPT and tell me what you sell.")
focus, brand = {"dm_keyword": "SCRIPT"}, {"facts_rules": ["no demo claims"]}
llm.factcheck_model = lambda p, s="", **k: json.dumps({"ok": False, "issues": ["garbled"], "revised": good})
r = linkedin_edit.run(bad, focus, brand)
assert r["post"] == good and r["changed"] and r["issues"] == ["garbled"]
for junk in ({"revised": {"linkedin": "x"}}, {"revised": "too short"}, {"ok": True}):
    llm.factcheck_model = lambda p, s="", _j=junk, **k: json.dumps(_j)
    assert linkedin_edit.run(bad, focus, brand)["post"] == bad, junk       # unusable answer -> original kept

# ---- 3. the pipeline step never touches the other platforms or the reply drafts
llm.factcheck_model = lambda p, s="", **k: json.dumps({"ok": False, "issues": [], "revised": good})
posts = {"instagram": "ig", "bluesky": "bs", "linkedin": bad, "replies": [1]}
res = run_daily.polish_linkedin(dict(posts), focus, brand)
assert res["linkedin"] == good and res["instagram"] == "ig" and res["bluesky"] == "bs" and res["replies"] == [1]
def boom(*a, **k): raise RuntimeError("model down")
llm.factcheck_model = boom
res = run_daily.polish_linkedin(dict(posts), focus, brand)
assert res["linkedin"] == bad, "editor failure must keep the original LinkedIn text"
print("linkedin test passed: Instagram/Bluesky format unchanged, LinkedIn plain + edited, failures keep the original")
