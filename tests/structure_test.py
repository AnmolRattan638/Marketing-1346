"""Offline: retention structure. Every style holds the answer back with a rehook, the hook names the viewer's business, open loops are counted; the downstream pieces know the new beat."""
import os, sys
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
assert sw.REHOOK_WORDS == (6, 16) and sw.DEFAULT_EMOTION["rehook"] == "curious"
from agent import schema, sarvam, reel_text
assert "rehook" in schema.BEATS and schema.BEATS.index("rehook") == schema.BEATS.index("poke") + 1
assert "rehook" in sarvam.PAUSE_AFTER and "rehook" in reel_text.BEAT_NAMES
plan = {"scenes": [{"beat": b} for b in ("pain", "poke", "rehook", "fix", "cta")]}
assert not [p for p in schema._beat_problems(plan) if "order" in p]
print("structure test passed")
