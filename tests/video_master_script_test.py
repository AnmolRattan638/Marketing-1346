"""Offline test: the video agent follows the master script (beats in order, words verbatim, no research of its own)."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from agent import master_script as ms, plan as planmod
m = {"style": "myth-bust", "topic": "fast replies", "facts": [{"id": "f1", "claim": "c", "source": "a.com", "url": "https://a.com"}],
     "beats": [{"beat": "pain", "line": "Leads go cold at night", "screen": "Cold leads", "visual": "phone"},
               {"beat": "poke", "line": "Morning replies are too late", "screen": "Too late", "visual": "x"},
               {"beat": "fix", "line": "An instant first reply keeps them", "screen": "Reply fast", "visual": "chat"},
               {"beat": "cta", "line": "DM me BOT", "screen": "DM BOT", "visual": "logo"}]}
d = pathlib.Path(tempfile.mkdtemp())
(d / "draft.json").write_text(json.dumps({"service": "chatbot", "master_script": m}))
got = ms.load(str(d / "draft.json")); assert got["service"] == "chatbot" and got["beats"]
(d / "bare.json").write_text(json.dumps(m)); assert ms.load(str(d / "bare.json"))["topic"] == "fast replies"
(d / "none.json").write_text(json.dumps({"service": "x"})); assert ms.load(str(d / "none.json")) is None
assert ms.load(str(d / "missing.json")) is None
sc = lambda b, n="narration here": {"beat": b, "narration": n, "footage_query": "ai tech"}
ok = {"scenes": [sc("pain"), sc("poke"), sc("fix"), sc("fix"), sc("cta")]}
assert ms.problems(ok, m) == []
assert ms.problems({"scenes": [sc("poke"), sc("pain"), sc("fix"), sc("cta")]}, m)
assert ms.problems({"scenes": [sc("pain"), sc("fix"), sc("cta")]}, m)
out = ms.enforce_words(ok, m)
assert [s["narration"] for s in out["scenes"]] == ["Leads go cold at night", "Morning replies are too late", "An instant first reply keeps them", "DM me BOT"]
assert "Do NOT write or change any words" in ms.prompt_block(m)
# make_plan: planner invents words and an extra fix scene -> words replaced, order enforced
calls = []
planmod._call_groq = lambda msgs, cfg: calls.append(msgs) or json.dumps({"title": "Reply fast", "scenes": [sc("pain", "Invented line number one"), sc("poke", "Invented line two here"), sc("fix", "Invented fix line three"), sc("fix", "Another invented fix"), sc("cta", "Invented cta line")]})
cfg = json.load(open(pathlib.Path(__file__).resolve().parent.parent / "video-agent" / "config.json"))
plan = planmod.make_plan("fast replies", cfg, master=m)
assert [s["narration"] for s in plan["scenes"]][0] == "Leads go cold at night" and len(plan["scenes"]) == 4
assert "MASTER SCRIPT" in calls[0][1]["content"]
# invented claims are stripped, verified ones kept; emotion is carried to the scenes
m2 = dict(m, facts=[{"id": "f1", "claim": "53% of visits are abandoned", "figure": "53%", "source": "a.com"}], beats=[dict(b, emotion="warm" if b["beat"] == "cta" else None) for b in m["beats"]])
sc2 = lambda b, **k: dict(sc(b), **k)
p2 = {"scenes": [sc2("pain", fx=[{"type": "stat", "value": 73, "label": "x"}, {"type": "quote", "text": "q"}], graphic={"chips": ["2sec", "fast"]}),
                 sc2("poke", fx=[{"type": "stat", "value": 53}]), sc("fix"), sc("cta")]}
o = ms.enforce_words(p2, m2)["scenes"]
assert o[0]["fx"] == [] and o[0]["graphic"]["chips"] == ["fast"] and o[1]["fx"] == [{"type": "stat", "value": 53}], o
assert o[3]["emotion"] == "warm" and o[0]["emotion"] == "calm"
# no sources / too few facts -> the run fails loudly with a plain reason (never a generic video)
from src import web_research as wr
wr.evidence_for = lambda *a, **k: []
try: ms.make("chatbot for shops", {}); assert False
except RuntimeError as e: assert "no web sources" in str(e)
from src.agents import factsheet
wr.evidence_for = lambda *a, **k: [{"title": "t", "url": "u", "domain": "d", "snippet": "s"}]
factsheet.build = lambda *a, **k: {"ok": False, "facts": [1]}
try: ms.make("chatbot for shops", {}); assert False
except RuntimeError as e: assert "1 verified facts" in str(e)
assert "STEPS to show" in ms.prompt_block(dict(m, beats=[dict(b, steps=["a", "b"]) if b["beat"] == "fix" else b for b in m["beats"]]))
print("video master script ok")
