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

# device demos (phone chat / browser click) on the fix beat
assert scenarios.demo_target(voiced, 3) == 1          # the fix beat is next to the before/after scene, so the scene after the hook is used
beats2 = ["pain", "poke", "fix", "proof", "payoff", "cta"]
v2 = [(f"s{i}", {"beat": b}, 9.0, None, words) for i, b in enumerate(beats2)]
ba2 = scenarios.target_index(v2)
dm = scenarios.demo_target(v2, ba2)
assert v2[dm][1]["beat"] == "fix" and abs(dm - ba2) > 1, (dm, ba2)
assert scenarios.demo_kind("chatbot", "x") == "chat" and scenarios.demo_kind("website", "x") == "site"
g2 = {sid: {"layout": "title", "heading": "X", "times": {"heading": 0.3}} for sid, *_ in v2}
d2 = templates.apply(g2, v2, {"templates": {"enabled": True, "max_per_video": 3}}, "seed", "default", "chatbot")
assert g2[f"s{dm}"]["layout"] == "chat" and g2[f"s{dm}"]["chat"]["messages"][1]["from"] == "bot"
assert g2[f"s{ba2}"]["layout"] == "ba" and not any(abs(int(a["scene"][1:]) - int(b["scene"][1:])) == 1 for a in d2 for b in d2 if a is not b)
txt = " ".join(m["text"] for m in scenarios.CHAT["messages"]) + " " + " ".join(scenarios.SITE.values())
assert not re.search(r"\d{2,}|₹|Rs\.?\s?\d|%", txt), txt                  # no prices, percentages or invented figures
print("device demos ok")
