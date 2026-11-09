"""LinkedIn is the long explainer (300-380 words, grounded in the service facts); a short draft triggers a fix pass; Bluesky stays one plain post."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import captions, config, llm
from src.agents import writer, linkedin_edit

brand = config.load_json(config.ROOT / "config/services.json", {})
focus = next(s for s in brand["services"] if s["id"] == "chatbot")
plan = {"hooks": [{"text": "Hook"}], "chosen_hook": 0, "topic": "t", "angle": "a", "key_points": []}
long_li = "A clear opening sentence about repeated questions.\n\n" + "\n\n".join(["This paragraph explains one practical part of the service in plain words."] * 28)
short_li = "Short post. " * 20

# 1) the prompt demands 300-380 words, the seven-part structure, and carries the real service facts
seen = []
llm.gemini = lambda p, s="", **k: seen.append(p) or json.dumps({"instagram": "**H** ok", "linkedin": long_li, "bluesky": "A plain thought.", "replies": []})
out = writer.run(plan, focus, brand, "VOICE", "g")
p = seen[0]
assert "300-380 words" in p and "HOW IT WORKS" in p and "HOW IT HELPS" in p and "AN HONEST LIMIT" in p and "Never mention a price on LinkedIn" in p
assert "SERVICE FACTS" in p and "Smart AI Bot" in p and "Basic FAQ Bot" in p and "pays only after approving" in p
assert "CAPITAL WORD" not in p and "cannot carry the long explanation" in p
assert len(seen) == 1, "a good first draft needs no fix pass"

# 2) a LinkedIn draft under 300 words gets a fix pass; a better second draft wins, and the loop is bounded
assert "minimum is 300" in captions.over_limit({"linkedin": short_li})
seen.clear()
replies = [short_li, long_li]
llm.gemini = lambda p, s="", **k: seen.append(p) or json.dumps({"instagram": "**H** ok", "linkedin": replies[min(len(seen) - 1, 1)], "bluesky": "x", "replies": []})
out = writer.run(plan, focus, brand, "VOICE", "g")
assert len(seen) == 2 and "only 20" in seen[1] or "minimum is 300" in seen[1]
assert captions.words(out["linkedin"]) >= 300
seen.clear()
llm.gemini = lambda p, s="", **k: seen.append(p) or json.dumps({"instagram": "**H** ok", "linkedin": short_li, "bluesky": "x", "replies": []})
writer.run(plan, focus, brand, "VOICE", "g")
assert len(seen) <= 3, "never loops"

# 3) the LinkedIn editor keeps a long post, and refuses to turn it into a short one
llm.factcheck_model = lambda p, s="", **k: json.dumps({"ok": True, "issues": [], "revised": long_li + " One more clear sentence."})
assert captions.words(linkedin_edit.run(long_li, focus, brand)["post"]) >= 300
llm.factcheck_model = lambda p, s="", **k: json.dumps({"ok": False, "issues": ["x"], "revised": short_li})
assert linkedin_edit.run(long_li, focus, brand)["post"] == long_li, "an edit that shrinks the post below 300 words is ignored"

# 4) finalisation keeps the long post intact and Bluesky within its 300-character limit
fin = captions.finalize_posts({"instagram": "**H**", "linkedin": long_li, "bluesky": "w" * 400})
assert captions.words(fin["linkedin"]) >= 300 and len(fin["bluesky"]) <= 300
print("linkedin long-form test passed: 300-380 words, grounded service facts, fix pass, editor keeps length, Bluesky single plain post")
