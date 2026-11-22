"""Offline test: fact sheet verification + master scriptwriter rules. LLM mocked."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.agents import factsheet as fs, scriptwriter as sw
import tempfile
from src import scriptlessons as SL
SL.STATE = pathlib.Path(tempfile.mkdtemp()) / "script_lessons.json"      # tests never touch the real memory file

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

style = {**sw.BY_ID["myth-bust"], "beats": [b for b in sw.BY_ID["myth-bust"]["beats"] if b != "rehook"]}      # the legacy 5-beat shape; the rehook shape is tested in structure_test.py
good = {"hooks": ["Raat 11 baje clinic mein patient ka message aaya, jawab nahi gaya", "Aapke clinic ke leads raat ko kahan jaate hain?", "21 guna zyada leads, bas ek aadat se", "Customer ne raat ko WhatsApp kiya", "Website se sale nahi hoti"],
        "beats": [{"beat": "pain", "line": "Raat 11 baje clinic mein patient ne WhatsApp kiya, jawab nahi mila", "screen": "Raat ka message", "visual": "phone", "facts": []},
                  {"beat": "poke", "line": "Subah reply se kuch nahi hota, kyunki customer ko jawab turant chahiye, warna woh dusre business ke paas chala jaata hai", "screen": "Subah tak der", "visual": "x", "facts": []},
                  {"beat": "fix", "line": "Pehle bot greet kare, kyunki pehla jawab trust banata hai. Phir sawaal puche aur call book kare.", "screen": "3 steps", "visual": "chat", "facts": ["f3"], "steps": ["Greet karo", "Ek sawaal pucho", "Call book karo"]},
                  {"beat": "payoff", "line": "a.com ke mutabiq paanch minute mein reply karne wali firms ko 21 guna zyada leads milti hain. Matlab speed matter karti hai.", "screen": "21x leads", "visual": "stat", "facts": ["f1"]},
                  {"beat": "cta", "line": "Agar raat ko messages chhoot jaate hain, toh comment mein BOT likho. Main 3-step setup bhejunga.", "screen": "Comment BOT", "visual": "logo"}],
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
bad = copy.deepcopy(good); bad["beats"][1]["line"] = "Yeh sab ek badi samasya hai aajkal sabke liye, aur isliye hum sabko isse bahut dhyan se dekhna chahiye, matlab har cheez ko"
assert has(bad["beats"], "too abstract")
bad = copy.deepcopy(good); bad["beats"][2]["steps"] = ["ek"]
assert has(bad["beats"], "2-3 concrete steps")
bad = copy.deepcopy(good); bad["beats"][4]["line"] = "Comment LEARN aur seekho"
assert has(bad["beats"], "keyword BOT") and has(bad["beats"], "what the viewer gets")
bad = copy.deepcopy(good); bad["beats"][4]["line"] = "Comment BOT aur dekho"
assert has(bad["beats"], "what the viewer gets")
assert not sw.problems({"beats": copy.deepcopy(good["beats"])}, sheet2, style)
assert all(b["emotion"] in sw.EMOTIONS for b in script["beats"]) and script["beats"][0]["emotion"] == "empathetic" and script["beats"][3]["emotion"] == "excited"
# descriptive-script rules: statistic must not become a promise; bare slogans are rejected; the meaning check feeds back
bad = copy.deepcopy(good); bad["beats"][3]["line"] = "a.com ke mutabiq 21 guna zyada leads ab aapko pakka milengi, kyunki reply jaldi jaata hai aur isliye customer rukta hai"
assert has(bad["beats"], "promise")
bad = copy.deepcopy(good); bad["beats"][1]["line"] = "Subah reply dene se customer chala jaata hai"
assert has(bad["beats"], "want 10-26")
bad = copy.deepcopy(good)
for b in bad["beats"][1:4]: b["line"] = b["line"].replace("kyunki", "").replace("Matlab", "").replace("taaki", "").replace("Phir", "Ab").replace("matlab", "").replace("warna", "")
assert has(bad["beats"], "helping words") or has(bad["beats"], "bare statements")
seq = [json.dumps(good), json.dumps(good)]
calls = []
def ask2(p, s="", **k):
    calls.append(p)
    return json.dumps({"issues": ["payoff: says calls stop, fact says they are repeats"]}) if "editor checking spoken lines" in p and len(calls) == 2 else (json.dumps({"issues": []}) if "editor checking spoken lines" in p else seq.pop(0))
assert sw.run(sheet, {"name": "x", "dm_keyword": "BOT"}, style, ask=ask2, voice="v")["beats"] and sum("editor checking spoken lines" in c for c in calls) == 2

# the meaning check is told what the service does, so "customer ko wait nahi karna padega" is not flagged as an unsupported promise
seen = []
def ask3(p, s="", **k):
    seen.append(p)
    return json.dumps({"issues": []})
sw.fidelity({"beats": [{"beat": "recap", "line": "Customer ko wait nahi karna padega.", "facts": []}]}, {"facts": []}, ask3, {"name": "Chatbot", "pitch": "answers customer messages instantly, 24/7"})
assert "answers customer messages instantly" in seen[0] and "SERVICE CAPABILITIES" in seen[0] and "does not have to wait" in seen[0]

# every service lists what it really does (config/services.json), used by the writer and the meaning check; no figures or results in them
import json as _json, re as _re
_svcs = _json.load(open(pathlib.Path(__file__).resolve().parent.parent / "config" / "services.json"))["services"]
for _s in _svcs:
    assert len(_s.get("capabilities") or []) >= 3, _s["id"]
    assert not any(_re.search(r"\d|%|guarantee|more sales|increase", c, _re.I) for c in _s["capabilities"] if not _re.search(r"24 hours|24x7|30 to 60", c)), _s["id"]
    assert all(c in sw.capabilities(_s) for c in _s["capabilities"])
assert "instantly at any hour" in sw.capabilities(next(s for s in _svcs if s["id"] == "chatbot"))

# regression (2026-11-16): the model dropped the last beat (cta) and spoke "24" (24x7) that no fact cites
focus_bot = {"name": "Chatbot", "pitch": "answers customer messages", "capabilities": ["it works around the clock (24x7), nights and holidays included"]}
b24 = copy.deepcopy(good["beats"])
b24[1]["line"] = b24[1]["line"] + " Chatbot 24x7 jawab deta hai."
assert any("not backed" in p for p in sw.problems({"beats": copy.deepcopy(b24)}, sheet2, style))                # still rejected without the capability
assert not any("not backed" in p for p in sw.problems({"beats": copy.deepcopy(b24)}, sheet2, style, focus_bot))   # backed by the listed capability
short = {"beats": copy.deepcopy(good["beats"][:-1]), "cta": ""}
asked = []
def ask_cta(p, s="", **k):
    asked.append(p)
    return json.dumps({"beats": [{"beat": "cta", "line": good["beats"][-1]["line"], "screen": "BOT", "visual": "x", "emotion": "warm", "facts": []}], "cta": good["beats"][-1]["line"]})
fixed = sw.repair_missing(short, style, ask_cta, {"name": "Chatbot"}, {"keyword": "BOT"})
assert [b["beat"] for b in fixed["beats"]] == style["beats"] and len(asked) == 1 and "ONLY the missing" in asked[0]
assert sw.repair_missing({"beats": copy.deepcopy(good["beats"][:2])}, style, ask_cta, {"name": "x"}, {}) ["beats"][:2] and len(asked) == 1   # 4 missing beats: not repaired, normal retry
print("scriptwriter ok")


# ------------------------------------------------------------------ concrete feedback: only the failing beat is rewritten; lessons are remembered; the run never stops
bad = copy.deepcopy(good); bad["beats"][3]["line"] = "a.com ke mutabiq 40 guna zyada leads mile, matlab speed hi sabse sasta sales tool hai"
fixed = copy.deepcopy(good["beats"][3])
calls = []
def ask(p, s="", **k):
    calls.append(p)
    if "Rewrite ONLY the beat" in p:
        assert "['payoff']" in p and "not backed by a cited fact" in p and "MISTAKES YOU HAVE MADE BEFORE" in p
        return json.dumps({"beats": [fixed]})
    if "editor" in p or "strict marketing editor" in s or "issues" in p:
        return json.dumps({"issues": []})
    return json.dumps({"hooks": [], "beats": bad["beats"]})
out = sw.run(sheet, {"name": "Chatbot", "dm_keyword": "BOT"}, style, ask=ask, voice="v")
assert out["beats"][3]["line"] == fixed["line"], "the failing beat was rewritten"
assert [b["line"] for i, b in enumerate(out["beats"][:-1]) if i != 3] == [b["line"] for i, b in enumerate(bad["beats"][:-1]) if i != 3], "every other beat is untouched"
assert out["beats"][-1]["line"].startswith(bad["beats"][-1]["line"].rstrip(". ")), "the cta only gains the carousel pointer"
assert sum("Rewrite ONLY the beat" in c for c in calls) == 1 and sum("Write ONE script" in c for c in calls) == 1, "one draft + one targeted repair, no full regeneration"
blk = SL.prompt_block()
assert "Every digit must come from a cited fact" in blk and "rejected 1x before" in blk and "Never stop early" in blk
per, glob = sw.by_beat(["fix: needs 2-3 concrete steps", "meaning: payoff: too much", "hook is too long; 16 words max", "beats must be exactly ['a'], got []", "script is off-service: x"], [{"beat": n} for n in style["beats"]])
assert per == {"fix": ["needs 2-3 concrete steps"], "payoff": ["too much"], "pain": ["hook is too long; 16 words max"]} and len(glob) == 2, (per, glob)
assert "fallback=False" in (pathlib.Path(__file__).resolve().parent.parent / "src/run_daily.py").read_text(), "a script failure is a warning, not a stopped run"
print("targeted repair + lessons + non-fatal ok")

# ---- length budget: ~30 s reel, never cut by machine, never thin
w = lambda n: " ".join(["shabd"] * n)
long_ = [{"beat": "pain", "line": w(12)}, {"beat": "poke", "line": w(22)}, {"beat": "fix", "line": w(22)}, {"beat": "payoff", "line": w(22)}, {"beat": "recap", "line": w(18)}, {"beat": "cta", "line": w(20)}]
bp = sw.budget_problems(long_)
assert bp and all("tighten" in x and "grammatically complete" in x for x in bp) and not any(x.startswith(("pain", "cta")) for x in bp), bp
per, glob = sw.by_beat(bp, long_)
assert per and not glob, "over-length feedback is per beat, so only the long beats are rewritten"
assert sw.budget_problems([{"beat": "pain", "line": w(10)}, {"beat": "poke", "line": w(15)}, {"beat": "cta", "line": w(10)}])[0].startswith("poke: script is only 35 words")
assert sw.budget_problems([{"beat": "pain", "line": w(12)}, {"beat": "poke", "line": w(18)}, {"beat": "fix", "line": w(20)}, {"beat": "payoff", "line": w(18)}, {"beat": "cta", "line": w(16)}]) == []
assert sw.TOTAL_WORDS[1] <= 100 and "FIRST 8 SECONDS" in open(sw.__file__).read()
print("length budget ok")

# ---- the on-screen `steps` never fails a day: built from the fix line's own clauses when the model leaves them out
s1 = {"beats": [{"beat": "fix", "line": "Pehle bot greet kare, kyunki pehla jawab trust banata hai. Phir sawaal puche aur call book kare.", "steps": []}]}
sw.normalize_steps(s1)
st = s1["beats"][0]["steps"]
assert 2 <= len(st) <= 3 and all(len(x.split()) <= 7 for x in st) and all(x.split()[0] in s1["beats"][0]["line"] for x in st), st
s2 = {"beats": [{"beat": "fix", "line": "x y z w v u t s r q", "steps": ["a b"]}]}
sw.normalize_steps(s2)
assert s2["beats"][0]["steps"] == ["a b"], "nothing to derive from: left as is for the model to fix"
bad = copy.deepcopy(good); bad["beats"][2]["steps"] = []
assert not [p for p in sw.problems(sw.normalize_steps({"beats": bad["beats"]}), sheet, style) if "steps" in p]
print("steps normalization ok")


# ------------------------------------------------------------------ pronunciation gate + concrete lessons
# A word the voice would say wrong is rejected like any other mistake, ONLY that beat is rewritten, and the concrete mistake is remembered and shown to the writer next time.
SL.STATE = pathlib.Path(tempfile.mkdtemp()) / "pron_lessons.json"
focus_p = {"name": "Chatbot", "dm_keyword": "BOT"}
bad_p = copy.deepcopy(good)
bad_p["beats"][2]["line"] = "Pehle bot greet kare, kyunki pehla jawab trust banata hai. Phir sawaal puche aur SERP 2BHK kare."
reasons = [r for r in sw.problems({"beats": copy.deepcopy(bad_p["beats"])}, sheet, style, focus_p) if "pronunciation" in r]
assert len(reasons) == 2 and all(r.startswith("fix: pronunciation:") for r in reasons) and "SERP" in reasons[0] and "2BHK" in reasons[1], reasons
assert "SERP 2BHK" in reasons[0], "the reason shows where the word was heard"
assert not [r for r in sw.problems({"beats": copy.deepcopy(good["beats"])}, sheet, style, focus_p) if "pronunciation" in r], "the DM keyword BOT, 24x7-style words and UPI are fine"
cta_ok = copy.deepcopy(good["beats"]); cta_ok[-1]["line"] = "Agar raat ko messages chhoot jaate hain, toh comment mein BOT likho. UPI aur 24x7 setup bhejunga."
assert not [r for r in sw.problems({"beats": cta_ok}, sheet, style, focus_p) if "pronunciation" in r]
per, glob = sw.by_beat(reasons, [{"beat": n} for n in style["beats"]])
assert list(per) == ["fix"] and not glob, "routed to the fix beat only"
fixed_fix = copy.deepcopy(good["beats"][2])
calls_p = []
def ask_p(p, s="", **k):
    calls_p.append(p)
    if "Rewrite ONLY the beat" in p:
        assert "['fix']" in p and "SERP" in p and "pronunciation" in p, p[:300]
        return json.dumps({"beats": [fixed_fix]})
    if "editor" in p or "strict marketing editor" in s or "issues" in p:
        return json.dumps({"issues": []})
    return json.dumps({"hooks": [], "beats": bad_p["beats"]})
out_p = sw.run(sheet, focus_p, style, ask=ask_p, voice="v")
assert out_p["beats"][2]["line"] == fixed_fix["line"], "the failing beat was rewritten"
tease = " Poora breakdown aaj ke carousel mein hai."
assert [b["line"].replace(tease, "") for i, b in enumerate(out_p["beats"]) if i != 2] == [b["line"] for i, b in enumerate(bad_p["beats"]) if i != 2], "every other beat untouched (bar the carousel pointer)"
lessons = SL.load()
assert lessons["pronounce-caps"]["count"] == 1 and "SERP" in lessons["pronounce-caps"]["recent"][-1]["mistake"] and lessons["pronounce-caps"]["recent"][-1]["on"], lessons
assert "2BHK" in lessons["pronounce-glued"]["recent"][-1]["mistake"], lessons
blk = SL.prompt_block()
assert "LAST TIME you wrote this and it was rejected" in blk and "SERP" in blk and "Never write an unknown ALL-CAPS word" in blk and "no ALL-CAPS word except the DM keyword" in blk, blk
SL.record(reasons); SL.record(reasons)
assert SL.load()["pronounce-caps"]["count"] == 1, "the same reason shown again in the same run is counted once"
SL.record([f'fix: pronunciation: "XQ{i}" (heard in: "...a XQ{i} b...") is written in capitals but has no spelling' for i in range(5)])
assert len(SL.load()["pronounce-caps"]["recent"]) == 3, "only the latest concrete mistakes are kept"
SL.STATE.write_text(json.dumps({"old": {"count": 2, "rule": "An old rule from before concrete lessons"}}), encoding="utf-8")
assert "An old rule from before concrete lessons (rejected 2x before)" in SL.prompt_block() and "LAST TIME" not in SL.prompt_block(), "old lesson files still work"
print("pronunciation gate + concrete lessons ok")

# the gate fails OPEN: if the voice rules file is missing, scripts are not blocked and the day goes on
from src import pronounce as _pr
_saved = (_pr._SPEECH, _pr._mod)
_pr._SPEECH, _pr._mod = pathlib.Path("/nonexistent/speech_text.py"), None
assert _pr.problems({"beats": [{"beat": "fix", "line": "Ye SERP dekho"}]}) == []
_pr._SPEECH, _pr._mod = _saved
assert _pr.problems({"beats": [{"beat": "fix", "line": "Ye SERP dekho"}]}), "and it checks again once the file is back"
print("pronunciation gate fails open ok")
