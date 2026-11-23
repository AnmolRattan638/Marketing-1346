"""Offline: retention structure. Every style holds the answer back with a rehook, the hook names the viewer's business, open loops are counted; the downstream pieces know the new beat."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "video-agent"))
from datetime import date
from src import verticals as V
from src.agents import scriptwriter as sw

# 1. every style: hook ... poke -> rehook -> fix
for s in sw.STYLES:
    b = s["beats"]
    assert "rehook" in b and b.index("rehook") == b.index("fix") - 1 and b[0] == "pain" and b[-1] == "cta", s["id"]
    assert "rehook" in s["how"]

# 2. verticals: rotation, detection
seen = {V.pick("x", date(2026, 11, d))["id"] for d in range(1, 13)}
assert len(seen) == 12, seen
assert V.pick("x", date(2026, 11, 22), 0)["id"] != V.pick("x", date(2026, 11, 22), 1)["id"], "the second reel names a different business type"
assert V.of("Raat 11 baje clinic ka phone kaun uthata hai?") == "clinic" and V.of("Kya aapki salon ki booking miss hoti hai?") == "salon" and V.of("Business owners ye karte hain") == "" and V.of("Shopify app") == ""
assert "CONTEXT FIRST" in V.block("x", date(2026, 11, 22))

# 3. structure problems
def beats(hook, poke, rehook):
    return [{"beat": "pain", "line": hook}, {"beat": "poke", "line": poke}, {"beat": "rehook", "line": rehook}, {"beat": "fix", "line": "x"}, {"beat": "cta", "line": "x"}]
good = beats("Raat ko clinic ka phone kaun uthata hai?", "Subah reply se kuch nahi hota, patient kisi aur clinic chala jaata hai…", "Par asli wajah ye nahi hai, ye teesra step hai?")
assert sw.structure_problems(good) == [], sw.structure_problems(good)
assert any("context:" in p for p in sw.structure_problems(beats("Raat ko business ka phone kaun uthata hai?", "poke?", "Par asli wajah kya hai?")))
assert any("loops:" in p and p.startswith("rehook") for p in sw.structure_problems(beats("Clinic ka phone raat ko band rehta hai.", "Patient chala jaata hai.", "Ab fix ye hai ki bot lagao.")))
assert any(p.startswith("rehook: loops: no figures") for p in sw.structure_problems(beats("Clinic ka phone raat ko band?", "Patient chala jaata hai…", "Par 90 log ye karte hain?")))
assert any("at least two" in p for p in sw.structure_problems(beats("Clinic ka phone raat ko band hai.", "Patient chala jaata hai.", "Par asli wajah kya hai?")))
assert sw.open_loops(good) == 3
assert all(sw.is_soft(p) for p in sw.structure_problems(beats("Raat ko business ka phone band hai.", "poke", "Ye hai fix.")))

# 4. the rehook has its own word budget and the new beat is known downstream
assert sw.REHOOK_WORDS == (8, 40) and sw.DEFAULT_EMOTION["rehook"] == "curious"
from agent import schema, sarvam, reel_text
assert "rehook" in schema.BEATS and schema.BEATS.index("rehook") == schema.BEATS.index("poke") + 1
assert "rehook" in sarvam.PAUSE_AFTER and "rehook" in reel_text.BEAT_NAMES
plan = {"scenes": [{"beat": b} for b in ("pain", "poke", "rehook", "fix", "cta")]}
assert not [p for p in schema._beat_problems(plan) if "order" in p]
print("structure test passed")

# ---- Part 2: labels that travel with the draft into the learning loop
from src import structure, learning
m = {"style": "myth-bust", "hook_formula": "nobody", "beats": good}
d = structure.describe(m)
assert d["structure"] == "retention-v2" and d["vertical"] == "clinic" and d["rehook"] and d["context_first"] and d["open_loops"] == 3 and d["hook_formula"] == "nobody", d
assert structure.describe({"beats": [{"beat": "pain", "line": "Business ka phone band hai."}, {"beat": "fix", "line": "x"}]})["structure"] == "classic"
assert structure.describe({"beats": beats("Business ka phone band?", "p", "q")})["structure"] == "rehook-only"
assert structure.describe({}) == {} and structure.describe(None) == {}
attrs = learning._attrs({"date": "2026-11-22", "structure": d}, "instagram", "reel")
assert attrs["structure"] == "retention-v2" and attrs["vertical"] == "clinic" and attrs["hook_formula"] == "nobody"
assert learning._attrs({"date": "2026-11-22"}, "instagram", "reel")["structure"] is None, "old drafts without labels still work"
rows = [{"structure": s, "composite": c} for s, c in (("retention-v2", 1.4), ("retention-v2", 1.2), ("classic", 0.9), ("classic", 1.0), (None, 5.0))]
assert learning.lessons(rows, "structure") == [("retention-v2", 1.3, 2), ("classic", 0.95, 2)]
print("structure labels ok")

# ---- Part 3: the reel's CTA points to the day's carousel (the comment stays the one ask)
os.environ.pop("REEL_SLOT", None)
cta = lambda t: {"beats": [{"beat": "pain", "line": "x"}, {"beat": "cta", "line": t}]}
s = cta("Comment BOT likho, main aapko setup ke steps DM kar dunga")
assert sw.tease_carousel(s) and s["beats"][-1]["line"].endswith("Poora breakdown aaj ke carousel mein hai.") and s["carousel_tease"] and "." in s["beats"][-1]["line"][:-1]
assert len(s["beats"][-1]["line"].split()) <= sw.CTA_WORDS[1]
assert s["beats"][-1]["line"].lower().count("comment") == 1, "still one ask"
s = cta("Comment BOT likho. Poora breakdown carousel mein hai."); assert sw.tease_carousel(s) and s["beats"][-1]["line"].count("carousel") == 1
long = cta("Comment BOT likho aur main aapko pura setup step by step DM mein bhej dunga taaki aap aaj hi shuru kar sako aur customer na khoye, aur saath mein ye bhi bataunga ki aapke business ke liye kaun sa plan theek rahega, kitna time lagega aur kya kya chahiye hoga"); assert not sw.tease_carousel(long) and "carousel_tease" not in long
os.environ["REEL_SLOT"] = "2"; s = cta("Comment BOT likho"); assert not sw.tease_carousel(s) and "carousel_tease" not in s; del os.environ["REEL_SLOT"]
from agent import reel_text
plan = {"scenes": [{"beat": "pain", "narration": "Clinic ka phone raat ko band?"}, {"beat": "fix", "narration": "Bot lagao."}, {"beat": "cta", "narration": "Comment BOT likho."}]}
mm = {"service": "chatbot", "marketing": {"keyword": "BOT", "gets": "a setup checklist"}, "carousel_tease": True,
      "beats": [{"beat": "pain", "line": "Clinic ka phone raat ko band?"}, {"beat": "fix", "line": "Bot lagao."}, {"beat": "cta", "line": "Comment BOT likho."}]}
assert "carousel post mein hai" in reel_text.caption_text(plan, mm, "chatbot") and "carousel post" not in reel_text.caption_text(plan, {**mm, "carousel_tease": False}, "chatbot")
print("carousel tease ok")

# ---- Part 4a: reel 2 as part 2 of reel 1
import tempfile
from pathlib import Path
from src import config, run_reel2
assert "restaurant" in V.block("x", date(2026, 11, 22), 1, force="restaurant") and "clinic" in V.block("x", date(2026, 11, 22), 1, force="clinic")
blk = sw.series_block({"hook": "Clinic ka phone raat ko kaun uthata hai?", "rehook": "Par asli wajah ye nahi hai?", "steps": ["Bot lagao"], "facts_used": ["43%"]})
assert "PART 2" in blk and "Do NOT repeat reel 1" in blk and "43%" in blk and sw.series_block(None) == ""
tmp = Path(tempfile.mkdtemp()); (tmp / "master").mkdir()
old = config.DATA; config.DATA = tmp
brand = {"services": [{"id": "chatbot", "name": "AI chatbot"}, {"id": "website", "name": "Website"}]}
facts = [{"claim": f"fact {i}", "figure": f"{i}0%"} for i in range(4)]
m1 = {"style": "myth-bust", "topic": "night leads", "service": "chatbot", "facts": facts, "beats": [
    {"beat": "pain", "line": "Clinic ka phone raat ko kaun uthata hai?"}, {"beat": "poke", "line": "Patient chala jaata hai"}, {"beat": "rehook", "line": "Par asli wajah ye nahi hai?"},
    {"beat": "fix", "line": "10% log bot lagate hain"}, {"beat": "cta", "line": "Comment BOT"}]}
config.save_json(tmp / "master" / "2026-11-22.json", {"master_script": m1, "service": "chatbot"})
got = run_reel2.series_from("2026-11-22", brand)
assert got["focus"]["id"] == "chatbot" and got["sheet"]["ok"] and len(got["sheet"]["facts"]) == 4 and got["series"]["vertical"] == "clinic" and got["series"]["rehook"].startswith("Par asli") and got["series"]["facts_used"] == ["10%"], got
os.environ["REEL2_LOOP"] = "0"; assert run_reel2.series_from("2026-11-22", brand) is None; del os.environ["REEL2_LOOP"]
assert run_reel2.series_from("2026-11-23", brand) is None, "no reel 1 script: the old separate reel 2"
config.save_json(tmp / "master" / "2026-11-24.json", {"master_script": {**m1, "facts": facts[:2]}, "service": "chatbot"}); assert run_reel2.series_from("2026-11-24", brand) is None, "too few facts"
config.DATA = old
from agent import reel_text
note = reel_text.message({"scenes": []}, {"series": {"part": 2}, "beats": []}, "x")
assert note.startswith("PART 2 of today's series"), note
assert structure.describe({**m, "series": {"part": 2}})["series"] is True and structure.describe(m)["series"] is False
print("series loop ok")

# ---- Part 4b: proof cards are real mock types end to end
from agent import graphics, schema
for typ, items in (("chat", ["Kya raat ko booking ho sakti hai?", "...", "you: Subah reply milega"]), ("maps", ["Your Clinic", "Dental clinic", "Closed now"]), ("gauge", ["Mobile speed", "Slow", "slow"])):
    assert typ in graphics.MOCKS and typ in json.dumps(schema.PLAN_SCHEMA), typ
    props = graphics.resolve_graphic({"graphic": {"layout": "step", "step": "STEP 1", "heading": "Raat ka message", "mock": {"type": typ, "items": items}}}, [], 5.0)
    assert props and props["mock"]["type"] == typ and len(props["mock"]["items"]) == 3, typ
tsx = open(os.path.join(ROOT, "video-agent/template/src/graphics/mocks/ProofCards.tsx")).read()
assert "EXAMPLE" in tsx and "#" not in tsx.replace("//", "").split("import")[-1].split("THEME")[0][:0], "labelled as an example"
import re
assert not re.search(r"#[0-9a-fA-F]{3,6}\b", tsx), "brand palette only, no hardcoded hex"
print("proof cards ok")
