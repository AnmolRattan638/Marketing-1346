"""Offline test: the reel agent writes each 10-second clip as a beat sheet AND a Flow paste prompt in the owner's cinematic style, checks them, retries once, then falls back."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ.pop("GROQ_API_KEY", None)
from src import llm
from src.agents import video

W = "a Space Silver MacBook Pro on a Nordic oak desk lit by a warm 3200K lamp, brushed aluminium and glass reflections, dust motes drifting in the golden light"
def beat(a, b):
    return {"start": a, "end": b, "title": "The Cold Open", "visual": f"Close on {W}; a fingertip hovers over the trackpad while the cold blue screen glow washes across the oak grain and the lamp stays dim", "feel": "Ek ajeeb si bechaini, jaise kuch galat hai", "camera": "A slow micro-dolly push-in on a 100mm macro lens at f/2.0", "audio": "A tense silence, then a single heavy key click"}
def good_clip():
    return {"beats": [beat(i, i + 1) for i in range(10)],
            "flow_beats": [{"start": a, "end": b, "text": "A slow micro-dolly push-in on the laptop; a fingertip deletes one stiff sentence while the warm tungsten lamp light spills across brushed aluminium and glass reflections with volumetric dust motes in the beam, while the screen glow shifts from a cold harsh blue to a calm warm gold across the oak grain and the whole frame settles into a quiet, relieved stillness."} for a, b in ((0, 3), (3, 6), (6, 8), (8, 10))],
            "audio": "Tense silence for one second, then one heavy key click, rhythmic ASMR keystrokes, a decisive delete thud, a warm lo-fi synth pad and a lingering vinyl tail.", "delivery": "Intimate, grounded, conversational"}
PLAN = {"hook_first_3s": "h", "concept": "A stiff sentence is deleted", "parts": [{"time": t, "voiceover": f"Line {i} for the reel.", "story": f"Story {i}"} for i, t in enumerate(video.TIMES, 1)]}
calls = []
mode = {"clip": "good"}
def pw(p, s="", **k):
    calls.append(p)
    if "Plan a 30-second" in p:
        return json.dumps(PLAN)
    if mode["clip"] == "good":
        return json.dumps(good_clip())
    return json.dumps({"beats": [], "flow_beats": []})
llm.prompt_writer = pw
plan = {"topic": "t", "hooks": [{"text": "Hook?"}], "chosen_hook": 0}
focus = {"id": "reel_scripts", "name": "Reel scripts", "dm_keyword": "SCRIPT"}

r = video.run(plan, focus, {}, "", {"facts_rules": ["Never claim results"]})
assert len(r["parts"]) == 3 and len(calls) == 4, len(calls)
p1, p2, p3 = r["parts"]
assert "Never claim results" in calls[0] and "ARRI Alexa Mini LF" in p1["flow_prompt"] and "AR Designs" in p1["flow_prompt"]
assert p1["flow_prompt"].startswith("A deeply relatable") and p2["flow_prompt"].startswith("Continuing the") and p3["flow_prompt"].startswith("The final act of a")
assert "[00:00-00:03 / Story 0-3s]" in p1["flow_prompt"] and "[00:00-00:03 / Story 10-13s]" in p2["flow_prompt"] and "Story 28-30s" in p3["flow_prompt"]
assert 'voiceover: "Line 1 for the reel."' in p1["flow_prompt"] and "Audio & Voiceover Sync:" in p1["flow_prompt"]
assert p1["beat_sheet"].startswith("[00:00 - 00:01] Frame 1-60: The Cold Open") and "[00:19 - 00:20] Frame 541-600" in p2["beat_sheet"]
assert "Story Feel:" in p1["beat_sheet"] and "Camera & Lens:" in p1["beat_sheet"] and "Audio Cue:" in p1["beat_sheet"]
assert "previous clip ended" in calls[2] and "opening clip" in calls[1] and "final clip" in calls[3]
assert any("DM keyword" in w for w in r["warnings"]) is True, "last line does not say REEL"

# a clip that fails the checks is retried once with the exact problems, then replaced by a plain valid clip with a warning
calls.clear(); mode["clip"] = "bad"
r = video.run(plan, focus, {}, "")
assert len(calls) == 1 + 3 * 2, len(calls)
assert "THESE PROBLEMS" in calls[2] and "needs 6-10 beats" in calls[2]
assert len(r["parts"]) == 3 and all("ARRI Alexa Mini LF" in p["flow_prompt"] and p["beat_sheet"] == "" for p in r["parts"])
assert sum("plain fallback clip" in w for w in r["warnings"]) == 3

# validation details: gaps, Devanagari, thin text
c = good_clip(); c["beats"][3]["start"] = 5
assert any("must start at 3s" in x for x in video.check_clip(c)[1])
c = good_clip(); c["audio"] = "शांत " + c["audio"]
assert any("Devanagari" in x for x in video.check_clip(c)[1])
c = good_clip(); c["flow_beats"][0]["text"] = "too short"
assert any("too thin" in x for x in video.check_clip(c)[1])
assert video.check_clip(good_clip())[1] == []
# a service world changes the objects, the header keeps the same camera and stock
assert "Space Grey smartphone" in video.header(1, video.world_for({"id": "chatbot"})) and "Kodak Vision3 500T" in video.header(3, video.world_for({"id": "chatbot"}))
print("video test passed: style header, beat sheet + paste version, frame math, retry then fallback, validation")
