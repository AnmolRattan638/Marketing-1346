"""Offline test of the reel agent: outline + one call per clip on Groq, film header added by code, beat sheet and paste version,
validation and one retry, DM keyword from services.json, no prices."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import llm
from src.agents import video

calls = []
def beat(s, e):
    return {"start": s, "end": e, "visual": "Extreme macro top-down shot of a hand resting on a Space Silver MacBook Pro keyboard on a Nordic oak desk, cold blue screen glow against a warm 3200K lamp, dust motes drifting in the light", "feel": "Dil mein halka sa darr hai.", "camera": "85mm Macro lens, f/1.4, micro-dolly push-in", "audio": "tense silence, then one heavy click"}
def paste(s, e):
    return {"start": s, "end": e, "text": "Macro probe-lens glide across the glowing screen at a 35-degree angle, crisp pixel detail, a cursor types a natural line while amber and teal tags light up in a clean outline, warm lamp light spilling over brushed aluminium"}
GOOD = {"beats": [beat(i, i + 1) for i in range(10)], "paste": [paste(0, 3), paste(3, 6), paste(6, 8), paste(8, 10)], "sync": "Voiceover starts at 00:01 over soft keystrokes and ends at 00:08 as the pad swells."}
state = {"bad_first": True}
def groq(p, s="", **k):
    calls.append(p)
    if "You plan only the outline" in p or "plan only the outline" in p:
        return json.dumps({"hook_first_3s": "Stiff scripts kill confidence", "parts": [
            {"goal": "problem", "voiceover": "Your script sounds like an exam answer.", "end_frame": "a glowing hero frame", "audio_motif": "keys"},
            {"goal": "how", "voiceover": "Write the way you actually talk.", "end_frame": "a clean slate", "audio_motif": "pad"},
            {"goal": "next step", "voiceover": "DM me SCRIPT and see how it sounds.", "end_frame": "a locked wide frame", "audio_motif": "vinyl"}]})
    if "Write clip 1 of 3" in p and state["bad_first"]:
        state["bad_first"] = False
        return json.dumps({**GOOD, "beats": GOOD["beats"][:2]})           # too few beats -> retry once
    return json.dumps(GOOD)
llm.groq = groq

out = video.run({"topic": "t", "hooks": [{"text": "Hook?"}], "chosen_hook": 0}, {"id": "reel_scripts", "name": "Reel scripts"}, {}, "note")
assert len(out["parts"]) == 3 and out["dm_keyword"] == "SCRIPT" and out["issues"] == []
assert any("FIX THESE PROBLEMS" in c and "beats" in c for c in calls), "a thin clip is retried once with the problems named"
assert len(calls) == 1 + 3 + 1
for i, p in enumerate(out["parts"]):
    assert p["flow_prompt"].startswith("Generate a 10-second vertical 9:16 video") and "ARRI Alexa Mini LF" in p["flow_prompt"]
    assert f"Story {i * 10}-{i * 10 + 3}s]" in p["flow_prompt"] and "Audio & Voiceover Sync:" in p["flow_prompt"]
    assert p["beat_sheet"].count("Story Feel:") == 10 and "Camera & Lens:" in p["beat_sheet"] and "frames 0-60" in p["beat_sheet"]
assert "script document" in out["parts"][0]["flow_prompt"] and "100mm Macro Anamorphic" in out["parts"][0]["flow_prompt"] and "85mm Anamorphic" in out["parts"][1]["flow_prompt"]
assert "opens from the previous clip" in calls[3] and "a glowing hero frame" in calls[3]
assert out["voiceover"].count(".") == 3 and out["hook_first_3s"]
assert all(len(p["flow_prompt"]) < 3900 for p in out["parts"]), "the paste version fits one Telegram message (the beat sheet is chunked by tg.send)"

# every service has a kit and a DM keyword; a price in the output is refused
for sid in ("website", "chatbot", "animated_ads", "lead_gen", "reel_scripts", "seo_blogs"):
    assert video.kit(video.style(), sid)["metaphor"] and video.keyword(sid), sid
bad = {**GOOD, "sync": "Starts at 00:01. Only INR 999 for this."}
llm.groq = lambda p, s="", **k: json.dumps({"hook_first_3s": "h", "parts": [{"goal": "g", "voiceover": "v", "end_frame": "e", "audio_motif": "a"}] * 3}) if "plan only the outline" in p else json.dumps(bad)
try:
    video.run({"topic": "t", "hooks": [{"text": "H"}], "chosen_hook": 0}, {"id": "chatbot", "name": "Chatbot"}, {})
    raise SystemExit("a price must be refused")
except ValueError as e:
    assert "banned" in str(e)
print("video test passed: outline + clips, film header, beat sheet, paste version, retry, keyword, price refused")
