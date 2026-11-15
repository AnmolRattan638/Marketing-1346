"""Planner mistakes become concrete feedback, are counted for later runs, and reach the next prompt."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import lessons, plan

lessons.STATE = pathlib.Path(tempfile.mkdtemp()) / "planner_lessons.json"
key, text, rule = lessons.explain("scenes/3/graphic/heading: '53% businesses karti hain ye galati' is too long")
assert "scene 4" in text and "35 characters" in text and "limit is 30" in text and rule.endswith("30 characters")
assert lessons.explain("scenes/5/fx/0/type: 'pop' is not one of ['stat', 'glitch']")[1].startswith("scene 6: `fx type` was \"pop\"")
lessons.record(["scenes/3/graphic/heading: 'abcdefghijklmnopqrstuvwxyz12345' is too long"] * 2)
assert lessons.load()["heading:too-long"]["count"] == 2 and "sound effects" in lessons.prompt_block().lower()

# the retry message names the concrete mistake, the final error lists it, and a third try is allowed
from agent.common import load_config
cfg = load_config()
bad = {"title": "t t t", "scenes": [{"narration": "abcdefgh", "graphic": {"layout": "step", "heading": "x" * 40}}]}
sent = []
def fake(messages, c):
    sent.append(messages[-1]["content"]); return json.dumps(bad)
orig = plan._call_groq; plan._call_groq = fake
try:
    plan.make_plan("topic", cfg)
    # tidy_plan trims a 40-char heading, so this plan is valid; force a real rejection instead
except Exception as e:
    print("raised:", e)
plan._call_groq = orig
sent.clear()
bad2 = {"title": "t t t", "scenes": [{"narration": "abcdefgh", "graphic": {"layout": "nope"}}]}
plan._call_groq = lambda m, c: (sent.append(m[-1]["content"]), json.dumps(bad2))[1]
try:
    plan.make_plan("topic", cfg); assert False
except RuntimeError as e:
    assert "rejected 3 times" in str(e) and "layout" in str(e), str(e)
assert sum("concrete mistakes" in x for x in sent) == 2 and sum(1 for x in sent) >= 3
plan._call_groq = orig
print("video lessons ok")
