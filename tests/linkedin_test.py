"""Offline test: the LinkedIn fix changes LinkedIn ONLY. Instagram and Bluesky keep their Unicode-bold/arrow format."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import captions

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
print("linkedin test passed: Instagram/Bluesky format unchanged, LinkedIn plain text")
