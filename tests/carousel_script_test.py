"""Offline test: the carousel follows the master script; verified figures allowed, other numbers still banned."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import llm
from src.agents import carousel as car
facts = [{"id": "f1", "claim": "Firms replying within 5 minutes win 21 times more leads", "figure": "21x", "source": "a.com"},
         {"id": "f2", "claim": "53% of visits are abandoned when pages load slowly", "figure": "53%", "source": "b.com"}]
master = {"style": "myth-bust", "hook": "Your leads go cold at night", "facts": facts,
          "beats": [{"beat": "pain", "line": "Your leads go cold at night", "facts": []}, {"beat": "payoff", "line": "a.com found 21 times more leads", "facts": ["f1"]}]}
focus = {"id": "chatbot", "name": "Chatbot", "pitch": "p", "dm_keyword": "BOT"}
sl = lambda *r: [{"role": a, "headline": b, "body": c} for a, b, c in r]
good = sl(("hook", "Your leads go cold at night", ""), ("problem", "Replies come too late", "Owners sleep, leads leave."), ("solution", "Reply in minutes", "a.com found 53% fewer drop-offs? no"), ("solution", "Let a bot greet first", "Then you take over."), ("cta", "x", "Message me"))
good[2]["body"] = "a.com found 21x more leads with fast replies."
assert car.validate(car.normalize(good, focus), focus, {}, None, master) == []
assert car.validate(car.normalize(good, focus), focus, {}, None), "without a sheet the multiplier must stay banned"
bad = json.loads(json.dumps(good)); bad[2]["body"] = "Gets you 40x more leads."
assert any("not allowed" in p for p in car.validate(car.normalize(bad, focus), focus, {}, None, master))
assert "MASTER SCRIPT" in car.script_block(master)
seen = {}
def fake(p, s="", **k):
    if "Write a swipe" in p: seen["p"] = p
    return json.dumps({"slides": good} if "Write a swipe" in p else {"ok": True, "issues": []})
llm.gemini = fake; llm.factcheck_model = fake
out, why = car.build({"topic": "t", "hooks": [{"text": "x"}]}, focus, {"facts_rules": []}, "", "2026-11-13", master=master)
assert out and out["flavor"] == "script:myth-bust" and out["checked"] and "MASTER SCRIPT" in seen["p"], (out, why)
print("carousel script ok")
