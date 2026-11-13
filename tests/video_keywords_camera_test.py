"""Offline test: stock stays AI/tech, camera moves resolve and the quote underline follows the spoken words."""
import os, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent / "video-agent"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from agent.stockquery import tech_queries, relevant, has_tech
from agent.camera_plan import plan_camera
from agent.fx_plan import plan_fx
from agent.schema import validate_plan
from agent import plan as planmod

# stock: every search carries a tech anchor, off-topic results are rejected, silent results are accepted
for q in ("girl taking a photo", "coffee shop", "", "ai agents typing on laptop"):
    qs = tech_queries(q)
    assert all(has_tech(x) for x in qs), (q, qs)
    assert len(qs) >= 2 and len(set(qs)) == len(qs)
assert tech_queries("ai agents typing on laptop")[0] == "ai agents typing on laptop"
assert not relevant("woman-holding-camera-on-street") and not relevant("cafe, coffee, latte")
assert relevant("robot-hand-typing-on-keyboard") and relevant("neural network, ai") and relevant("")

# camera: directed moves land on their words; automatic moves restart at every cut
ws = [{"text": w, "start": 0.3 + i * 0.4, "end": 0.6 + i * 0.4} for i, w in enumerate("where pine forests meet the river testimonials begin here".split())]
cam = plan_camera({"camera": [{"move": "zoom_in", "focus": "top"}, {"move": "pan_down", "at_word": "testimonials", "seconds": 1.5}, {"move": "pan_down", "at_word": "nowhere"}]}, ws, 5.0, None, 0, {})
assert [m["move"] for m in cam] == ["zoom_in", "pan_down"] and abs(cam[1]["atSecond"] - ws[6]["start"]) < 1e-6 and cam[0]["focus"][1] < 0.4
auto = plan_camera({}, ws, 6.0, [{"seconds": 3}, {"seconds": 3}], 0, {})
assert [m["move"] for m in auto if m["move"] == "reset"] == ["reset"] and next(m for m in auto if m["move"] == "reset")["atSecond"] == 3.0
assert plan_camera({}, ws, 6.0, None, 0, {"camera": {"enabled": False}}) == []

# quote: each quote word is timed on the narration word, and a quote the narrator did not say is dropped
fx = plan_fx({"fx": [{"type": "quote", "text": "pine forests meet the river", "label": "Guest"}]}, ws, 7.0, {})
assert len(fx) == 1 and fx[0]["type"] == "quote" and len(fx[0]["wordTimes"]) == 5
assert abs(fx[0]["atSecond"] + fx[0]["wordTimes"][0] - ws[1]["start"]) < 0.01 and abs(fx[0]["atSecond"] + fx[0]["wordTimes"][4] - ws[5]["start"]) < 0.01
assert plan_fx({"fx": [{"type": "quote", "text": "something never said at all"}]}, ws, 7.0, {}) == []

# the planner schema accepts both
p = planmod.sample_plan()
p["scenes"][0]["camera"] = [{"move": "zoom_in", "focus": "top"}, {"move": "pan_down", "at_word": "river", "seconds": 1.5}]
p["scenes"][0]["fx"] = [{"type": "quote", "text": "pine forests meet the river", "label": "Guest", "at_word": "pine"}]
assert validate_plan(p) == [], validate_plan(p)
print("video keywords/camera/quote test passed")
