import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "video-agent")]
from agent import viral

master = {"beats": [{"beat": "pain", "screen": "Raat 11 baje reply kaun dega kya"}], "hooks": []}
plan = {"scenes": [{"beat": "pain", "narration": "Raat 11 baje customer ne WhatsApp kiya, aur reply subah gaya.", "graphic": {"layout": "title"}}]}
assert viral.stop_check(plan)                                  # no heading yet
viral.stop_fix(plan, master)
g = plan["scenes"][0]["graphic"]
assert g["layout"] == "hook" and g["heading"] == "Raat 11 baje reply kaun" and viral.stop_check(plan) == [], viral.stop_check(plan)
weak = {"scenes": [{"narration": "Aaj hum baat karenge ek bahut zaroori topic ke baare mein jo sab ke liye important hai aur sabko jaanna chahiye hamesha", "graphic": {"layout": "step", "heading": "x"}}]}
assert len(viral.stop_check(weak)) >= 3
r = viral.forecast(plan, master)
assert "stop" in r and "ViralSim check" in viral.report(r)
assert "ViralSim check" in viral.report({"virality": None, "stop": []})
print("video viral ok")

# the hook is hardcoded: scene 1 is always the breaking-phone layout, with an impact sound on every spoken word
from agent import graphics
sc = {"narration": "Raat 11 baje customer ne WhatsApp kiya", "graphic": {"layout": "title", "heading": "Raat 11 baje reply?"}}
plan2 = viral.stop_fix({"scenes": [sc, {"narration": "x"}]}, {"beats": [{"screen": "Raat 11 baje reply"}]})
assert plan2["scenes"][0]["graphic"]["layout"] == "hook"
w = [{"text": t, "start": 0.1 + 0.35 * i, "end": 0.4 + 0.35 * i} for i, t in enumerate(sc["narration"].split())]
props = graphics.resolve_graphic(plan2["scenes"][0], w, 4.0)
assert props["layout"] == "hook" and props["hook"]["notifs"] and all("," not in n.split(":")[0] for n in props["hook"]["notifs"])
imp = [c for c in props["sfx"] if c["type"] == "impact"]
assert len(imp) == len(w) and props["sfx"][0]["type"] == "whoosh"
print("hook layout ok")
