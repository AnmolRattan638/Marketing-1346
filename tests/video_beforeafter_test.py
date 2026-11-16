import re
import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "video-agent")]
from agent import scenarios, templates

s = scenarios.spec()
assert len(s["beforeItems"]) == 3 and len(s["afterItems"]) == 3
assert "website" in s["beforeTitle"].lower() and "chatbot" in s["afterTitle"].lower()
for x in s["beforeItems"] + s["afterItems"]:
    assert "," not in x and not re.search(r"\d", x), x             # no invented figures
words = [{"text": "kya", "start": 0.5, "end": 0.8}]
beats = ["pain", "poke", "fix", "payoff", "cta"]
voiced = [(f"s{i}", {"beat": b}, 9.0, None, words) for i, b in enumerate(beats)]
assert scenarios.target_index(voiced) == 3
graphics = {sid: {"layout": "title", "heading": "X", "times": {"heading": 0.3}} for sid, *_ in voiced}
done = templates.apply(graphics, voiced, {"templates": {"enabled": True, "max_per_video": 3}}, "seed", "default", "website")
g = graphics["s3"]
assert g["layout"] == "ba" and g["ba"]["afterTitle"] == "Website + chatbot", g
assert any(d["template"] == "before-after" for d in done)
print("before/after ok")
