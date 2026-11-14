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
good = {"hooks": ["Raat 11 baje customer ka message aaya, jawab nahi gaya", "Aapke leads raat ko kahan jaate hain?", "21 guna zyada leads, bas ek aadat se", "Customer ne raat ko WhatsApp kiya", "Website se sale nahi hoti"],
        "beats": [{"beat": "pain", "line": "Raat 11 baje customer ne WhatsApp kiya, jawab nahi mila", "screen": "Raat ka message", "visual": "phone", "facts": []},
                  {"beat": "poke", "line": "Subah reply dene se woh dusri dukaan chala jaata hai", "screen": "Subah tak der", "visual": "x", "facts": []},
                  {"beat": "fix", "line": "Pehle bot ko greet karna sikhao, phir ek sawaal, phir booking", "screen": "3 steps", "visual": "chat", "facts": ["f3"], "steps": ["Greet karo", "Ek sawaal pucho", "Call book karo"]},
                  {"beat": "payoff", "line": "a.com ke mutabiq paanch minute mein reply se 21 guna leads", "screen": "21x leads", "visual": "stat", "facts": ["f1"]},
                  {"beat": "cta", "line": "Comment BOT, main aapko 3-step setup bhejunga", "screen": "Comment BOT", "visual": "logo"}],
        "cta": "Comment BOT, main aapko 3-step setup bhejunga", "linkedin_english": "Fast replies win leads."}
script = sw.run(sheet, {"name": "Chatbot", "dm_keyword": "BOT"}, style, ask=lambda p, s="", **k: __import__("json").dumps(good), voice="v")
assert script["style"] == "myth-bust" and script["hook"] and script["hooks"] and script["beats"][0]["line"] == script["hook"]

import copy, json
bad = copy.deepcopy(good); bad["beats"][3]["line"] = "a.com ke mutabiq 40 guna zyada leads mile"
assert any("not backed" in p for p in sw.problems({"beats": bad["beats"]}, sheet, style))
bad = copy.deepcopy(good); bad["beats"][3]["facts"] = []
assert any("payoff needs" in p for p in sw.problems({"beats": bad["beats"]}, sheet, style))
bad = copy.deepcopy(good); bad["beats"][2]["facts"] = ["f9"]
assert any("not on the sheet" in p for p in sw.problems({"beats": bad["beats"]}, sheet, style))
bad = copy.deepcopy(good); bad["beats"][0]["line"] = "Hello friends welcome to my channel aaj"
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
# new quality rules
sheet2 = {**sheet, "keyword": "BOT"}
def has(beats, text): return any(text in p for p in sw.problems({"beats": beats}, sheet2, style))
bad = copy.deepcopy(good); bad["beats"][0]["line"] = "The myth: bots cannot ever replace a human at all"
assert has(bad["beats"], "generic") and has(bad["beats"], "not Hinglish")
bad = copy.deepcopy(good); bad["beats"][1]["line"] = "Yeh sab ek badi samasya hai aajkal sabke liye"
assert has(bad["beats"], "too abstract")
bad = copy.deepcopy(good); bad["beats"][2]["steps"] = ["ek"]
assert has(bad["beats"], "2-3 concrete steps")
bad = copy.deepcopy(good); bad["beats"][4]["line"] = "Comment LEARN aur seekho"
assert has(bad["beats"], "keyword BOT") and has(bad["beats"], "what the viewer gets")
bad = copy.deepcopy(good); bad["beats"][4]["line"] = "Comment BOT aur dekho"
assert has(bad["beats"], "what the viewer gets")
assert not sw.problems({"beats": copy.deepcopy(good["beats"])}, sheet2, style)
assert all(b["emotion"] in sw.EMOTIONS for b in script["beats"]) and script["beats"][0]["emotion"] == "empathetic" and script["beats"][3]["emotion"] == "excited"
print("scriptwriter ok")
