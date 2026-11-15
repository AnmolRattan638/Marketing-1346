"""Re-edit: plan validation with concrete mistakes, retry feedback, cut re-timing, word snapping, props."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import reedit as r

good = {"summary": "x", "cuts": [{"from": 2, "to": 4}], "zooms": [{"from": 10, "to": 13, "scale": 1.3, "x": 0.5, "y": 0.5}],
        "procedures": [{"from": 5, "to": 12, "title": "3-step setup", "position": "top", "steps": [{"text": "One", "at": 5.5}, {"text": "Two", "at": 7}, {"text": "Three", "at": 8.5}]}],
        "fx": [{"type": "title", "at": 13.5, "seconds": 1.5, "text": "Match"}]}
assert r.problems(good, 20) == []

bad = json.loads(json.dumps(good))
bad["procedures"][0]["steps"] = bad["procedures"][0]["steps"][:1]
bad["procedures"][0]["title"] = "x" * 40
bad["fx"][0].update(type="pop", at=9)
bad["zooms"][0]["scale"] = 3
p = " | ".join(r.problems(bad, 20))
assert "has 1 steps" in p and "title is 40 characters" in p and 'type "pop" does not exist' in p and "scale between" in p, p
over = json.loads(json.dumps(good)); over["fx"][0].update(at=8, seconds=2)
assert any("on screen together" in x for x in r.problems(over, 20))
assert any("more than 40%" in x for x in r.problems({"cuts": [{"from": 0, "to": 12}]}, 20))

# the planner is told the exact mistakes and gets another try
seen = []
def ask(messages, cfg):
    seen.append(messages[-1]["content"]); return json.dumps(bad if len(seen) == 1 else good)
assert r.make_plan("explain the steps", [], 20, {}, ask=ask) == good and "has 1 steps" in seen[1]
try:
    r.make_plan("x", [], 20, {}, ask=lambda m, c: json.dumps(bad)); assert False
except RuntimeError as e:
    assert "rejected 3 times" in str(e)

# cuts re-time everything after them; times inside a cut vanish
segs = r.kept_segments(good["cuts"], 20)
assert segs == [(0, 2), (4, 20)] and r.remap(1, segs) == 1 and r.remap(5, segs) == 3 and r.remap(3, segs) is None
words = [{"text": "pehle", "start": 5.6, "end": 5.9}, {"text": "phir", "start": 7.1, "end": 7.4}]
assert r.snap(5.5, words) == 5.6 and r.snap(6.3, words) == 6.3
props = r.build_props(good, words, segs, 20)
assert abs(props["seconds"] - 18) < 1e-6 and abs(props["procedures"][0]["steps"][0]["at"] - 3.6) < 1e-6
assert abs(props["fx"][0]["atSecond"] - 11.5) < 1e-6 and abs(props["zooms"][0]["from"] - 8) < 1e-6
print("video reedit ok")
