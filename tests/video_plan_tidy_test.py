"""Offline test: a model that writes "footage_query": "" on a graphic scene must not fail the planner (that crashed a run)."""
import copy, json, os, pathlib, sys
from unittest import mock
ROOT = pathlib.Path(__file__).resolve().parent.parent / "video-agent"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from agent import plan
from agent.common import load_config
from agent.schema import validate_plan

base = plan.sample_plan()
bad = copy.deepcopy(base)
sc = bad["scenes"]
sc[3]["graphic"] = {"layout": "punch", "heading": "Stop guessing"}
sc[3]["footage_query"] = ""                                   # the exact failure: scenes/4/footage_query: '' is too short
sc[2]["footage_query"] = "  hi "                              # too short after trimming
sc[1]["broll"] = ["", "x", "hands typing on laptop " + "very long " * 10, "customer reading phone"]
sc[0]["hero_clip"] = ""
sc[0]["fx"] = []
sc[1]["sfx"] = None
sc[1]["footage_query"] = "shop counter " + "word " * 30       # over 80 characters

assert any("too short" in p for p in validate_plan(copy.deepcopy(bad))), "the raw plan really fails validation"
fixed = plan.tidy_plan(copy.deepcopy(bad))
assert validate_plan(fixed) == [], validate_plan(fixed)
f = fixed["scenes"]
assert "footage_query" not in f[3] and f[3]["graphic"]["layout"] == "punch"
assert "footage_query" not in f[2] and "hero_clip" not in f[0] and "fx" not in f[0] and "sfx" not in f[1]
assert f[1]["broll"][0].startswith("hands typing") and len(f[1]["broll"][0]) <= 60 and f[1]["broll"][1] == "customer reading phone" and len(f[1]["broll"]) == 2
assert 3 <= len(f[1]["footage_query"]) <= 80 and f[1]["footage_query"].startswith("shop counter")

# real problems are still reported, not hidden
broken = copy.deepcopy(base)
broken["scenes"][0]["narration"] = "hi"
assert any("narration" in p for p in validate_plan(plan.tidy_plan(broken)))
broken = copy.deepcopy(base)
broken["scenes"][0]["graphic"] = {"layout": "nonsense"}
assert any("graphic" in p for p in validate_plan(plan.tidy_plan(broken)))
assert plan.tidy_plan([1, 2]) == [1, 2] and plan.tidy_plan({"title": "x"}) == {"title": "x"}

# make_plan: the first answer is accepted (before the fix this took two attempts and failed twice)
calls = []
def fake_groq(messages, cfg):
    calls.append(1)
    return json.dumps(bad)
with mock.patch.object(plan, "_call_groq", fake_groq):
    got = plan.make_plan("topic", load_config())
assert len(calls) == 1 and validate_plan(got) == []
print("video plan tidy test: ok")

# script framework beats: blank beat is dropped, order is enforced, plans without beats are untouched
from agent.schema import validate_plan as _vp
framed = plan.sample_plan()
assert [s["beat"] for s in framed["scenes"]] == ["pain", "poke", "fix", "cta"] and _vp(framed) == []
framed["scenes"][1]["beat"] = ""
assert _vp(plan.tidy_plan(framed)) == []
framed = plan.sample_plan(); framed["scenes"][0]["beat"], framed["scenes"][2]["beat"] = "fix", "pain"
assert any("pain" in p for p in _vp(framed)) and any("out of order" in p for p in _vp(framed))
framed = plan.sample_plan(); framed["scenes"][2]["beat"] = "poke"
assert any("more than once" in p for p in _vp(framed))
for s_ in framed["scenes"]: s_.pop("beat")
assert _vp(framed) == []
# the planner prompt carries the framework and none of the rules is cut off
sysmsg = plan.build_system_prompt(load_config())
assert "Pain, Poke, Fix, Payoff, Recap, CTA" in sysmsg and "truncated" not in sysmsg and "TESTIMONIALS" in sysmsg and "Topic first" in sysmsg
print("script framework test: ok")
