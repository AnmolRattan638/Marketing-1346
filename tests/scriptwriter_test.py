"""Offline test: fact sheet verification + master scriptwriter rules. LLM mocked."""
import pathlib, sys
from unittest import mock
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import llm
from src.agents import factsheet as fs, scriptwriter as sw

items = [{"title": "Reply study", "url": "https://a.com/1", "domain": "a.com", "date": "2026-09-01", "snippet": "Firms replying within 5 minutes win 21 times more leads."},
         {"title": "Site speed", "url": "https://b.com/2", "domain": "b.com", "date": "2026-08-01", "snippet": "53% of visits are abandoned if a page takes over 3 seconds."},
         {"title": "Bots", "url": "https://c.com/3", "domain": "c.com", "date": None, "snippet": "Chatbots answer routine questions around the clock."},
         {"title": "Ad", "url": "https://d.com/4", "domain": "d.com", "date": None, "snippet": "Buy now."}]
raw = {"facts": [
    {"claim": "Firms replying within 5 minutes win 21 times more leads", "figure": "21x", "source": 1, "verdict": "verified"},
    {"claim": "53% of visits are abandoned when pages load slowly", "figure": "53%", "source": 2, "verdict": "verified"},
    {"claim": "Chatbots answer routine questions around the clock", "figure": None, "source": 3, "verdict": "verified"},
    {"claim": "90% of owners lose sales at night time", "figure": "90%", "source": 3, "verdict": "verified"},    # number not in source
    {"claim": "Something weak and unclear about stuff here", "source": 2, "verdict": "weak"},
    {"claim": "Fact pointing at a missing source number", "source": 9, "verdict": "verified"}]}
sheet = fs.build("fast replies", items, ask=lambda p, s="", **k: __import__("json").dumps(raw))
assert sheet["ok"] and len(sheet["facts"]) == 3 and sheet["dropped"] == 3, sheet
assert [f["id"] for f in sheet["facts"]] == ["f1", "f2", "f3"]
raw["facts"] = raw["facts"][:2]
assert not fs.build("t", items, ask=lambda p, s="", **k: __import__("json").dumps(raw))["ok"]       # <3 verified -> skip topic
assert not fs.build("t", [])["ok"]

# style rotation: least recently used, never yesterday's
hist = [{"script_style": s["id"]} for s in sw.STYLES[:-1]]
assert sw.pick_style(hist)["id"] == sw.STYLES[-1]["id"]
assert sw.pick_style([])["id"] in sw.BY_ID
assert sw.pick_style(hist + [{"script_style": sw.STYLES[-1]["id"]}])["id"] == sw.STYLES[0]["id"]

style = sw.BY_ID["myth-bust"]
good = {"hooks": ["Reply late and customers leave", "Why do leads go cold?", "21 times more leads, one habit", "Customer messages at 11pm", "Websites do not sell"],
        "beats": [{"beat": "pain", "line": "Your enquiries go cold while you sleep", "screen": "Leads go cold", "visual": "phone", "facts": []},
                  {"beat": "poke", "line": "Replying tomorrow morning does not fix it", "screen": "Too late", "visual": "x", "facts": []},
                  {"beat": "fix", "line": "An instant first reply keeps the customer talking", "screen": "Reply fast", "visual": "chat", "facts": ["f3"]},
                  {"beat": "payoff", "line": "a.com found 21 times more leads within five minutes", "screen": "21x leads", "visual": "stat", "facts": ["f1"]},
                  {"beat": "cta", "line": "DM me the word BOT", "screen": "DM BOT", "visual": "logo", "facts": []}],
        "cta": "DM me the word BOT", "linkedin_english": "Fast replies win leads."}
script = sw.run(sheet, {"name": "Chatbot"}, style, ask=lambda p, s="", **k: __import__("json").dumps(good), voice="v")
assert script["style"] == "myth-bust" and script["hook"] and script["hooks"] and script["beats"][0]["line"] == script["hook"]

import copy, json
bad = copy.deepcopy(good); bad["beats"][3]["line"] = "a.com found 40 times more leads within five minutes"
assert any("not backed" in p for p in sw.problems({"beats": bad["beats"]}, sheet, style))
bad = copy.deepcopy(good); bad["beats"][3]["facts"] = []
assert any("payoff needs" in p for p in sw.problems({"beats": bad["beats"]}, sheet, style))
bad = copy.deepcopy(good); bad["beats"][2]["facts"] = ["f9"]
assert any("not on the sheet" in p for p in sw.problems({"beats": bad["beats"]}, sheet, style))
bad = copy.deepcopy(good); bad["beats"][0]["line"] = "Hello friends welcome to my channel today"
assert any("greeting" in p for p in sw.problems({"beats": bad["beats"]}, sheet, style))
bad = copy.deepcopy(good); bad["beats"] = bad["beats"][:3]
assert any("beats must be" in p for p in sw.problems({"beats": bad["beats"]}, sheet, style))
try:
    sw.run(sheet, {"name": "x"}, style, ask=lambda p, s="", **k: json.dumps({"hooks": [], "beats": bad["beats"]}), voice="v"); assert False
except ValueError:
    pass
# retry feeds back the reasons and recovers
seq = [json.dumps({"hooks": [], "beats": bad["beats"]}), json.dumps(good)]
assert sw.run(sheet, {"name": "x"}, style, ask=lambda p, s="", **k: seq.pop(0), voice="v")["beats"]
print("scriptwriter ok")
