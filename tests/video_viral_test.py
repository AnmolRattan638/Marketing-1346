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
assert g["layout"] == "punch" and g["heading"] == "Raat 11 baje reply kaun" and viral.stop_check(plan) == [], viral.stop_check(plan)
weak = {"scenes": [{"narration": "Aaj hum baat karenge ek bahut zaroori topic ke baare mein jo sab ke liye important hai aur sabko jaanna chahiye hamesha", "graphic": {"layout": "step", "heading": "x"}}]}
assert len(viral.stop_check(weak)) >= 3
r = viral.forecast(plan, master)
assert "stop" in r and "Predictor check" in viral.report(r)
assert "Predictor unavailable" in viral.report({"virality": None, "stop": []})
print("video viral ok")
