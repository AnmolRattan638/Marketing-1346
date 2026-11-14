"""Offline test: Sarvam voice path (bilingual prep, per-emotion params, speaker fallthrough, pauses) and script-word caption alignment. HTTP mocked."""
import base64, json, os, pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ["SARVAM_API_KEY"] = "k"
from agent import sarvam, voice, captions
from agent.common import media_duration

d = pathlib.Path(tempfile.mkdtemp())
wav = d / "src.wav"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=200:duration=1.0", "-ar", "24000", "-ac", "1", wav], check=True)
WAV = base64.b64encode(wav.read_bytes()).decode()
calls = []
class R:
    def __init__(s, c, j=None): s.status_code, s._j, s.text = c, j or {}, "x"
    def json(s): return s._j
    def raise_for_status(s): pass
def post(url, headers=None, json=None, timeout=0):
    calls.append(json)
    if json["speaker"] == "aayan_hi_conversational": return R(422)                  # this account does not know the first persona
    return R(200, {"audios": [WAV]})
sarvam.requests.post = post
cfg = {"voice_engine": "sarvam", "language": "en", "voice_language": "hi",
       "voices": {"hi": {"edge": "x", "sarvam": {"candidates": [{"model": "bulbul:v4-flash", "speaker": "aayan_hi_conversational"}, {"model": "bulbul:v4-flash", "speaker": "aayan_enhi_conversational"}]}}}}
# bilingual conversion: one batch call, cached, falls back to the Roman text
seen = []
voice_prepare = lambda texts, ask: sarvam.prepare(texts, ask)
voice_prepare(["Raat ko customer aaya", "Aap busy ho"], lambda p: seen.append(p) or {"lines": ["रात को customer आया", "आप busy हो"]})
assert len(seen) == 1 and sarvam.PREP["Raat ko customer aaya"].startswith("रात") and "exactly 2" in seen[0]
voice_prepare(["Raat ko customer aaya"], lambda p: seen.append(p) or {})                      # cached: no second call
assert len(seen) == 1
voice_prepare(["Naya line"], lambda p: (_ for _ in ()).throw(RuntimeError("rate limit")))
assert sarvam.PREP["Naya line"] == "Naya line"
# synth: first persona rejected -> second used; emotion changes pace/pitch; pause appended after the beat
mp3 = d / "a.mp3"
secs = voice.synth("Raat ko customer aaya", mp3, cfg, False, "excited", "payoff")
assert abs(secs - (1.0 + 0.40)) < 0.15, secs
assert [c["speaker"] for c in calls] == ["aayan_hi_conversational", "aayan_enhi_conversational"]
c = calls[-1]; assert c["text"].startswith("रात") and c["model"] == "bulbul:v4-flash" and c["language_code"] == "hi-IN"
assert c["pace"] > 1.05 and c["pitch"] > 0.05 and c["loudness"] > 1.1, c
calls.clear()
voice.synth("Aap busy ho", d / "b.mp3", cfg, False, "empathetic", "pain")
assert calls[-1]["pace"] < 0.95 and calls[-1]["pitch"] < 0
assert media_duration(d / "b.mp3") > 1.3                                                      # pain beat gets the longest pause
secs = voice.synth("Comment BOT", d / "c.mp3", cfg, False, "warm", "cta"); assert secs < 1.15           # no pause after the CTA
# every emotion the script can emit is known; errors are explicit; the reel never loses its voice (edge fallback order)
from src.agents import scriptwriter
assert set(scriptwriter.EMOTIONS) <= set(sarvam.EMOTION)
del os.environ["SARVAM_API_KEY"]
try: sarvam.synth("x", d / "z.mp3", {}, None, None); assert False
except RuntimeError as e: assert "SARVAM_API_KEY" in str(e)
# captions show the SCRIPT's Roman words on the heard (Devanagari) timings
heard = [{"text": "रात", "start": 0.0, "end": 0.4}, {"text": "को", "start": 0.4, "end": 0.6}, {"text": "customer", "start": 0.7, "end": 1.4}, {"text": "आया", "start": 1.4, "end": 1.9}]
w = captions.align_script("Raat ko customer aaya", heard)
assert [x["text"] for x in w] == ["Raat", "ko", "customer", "aaya"]
assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(w, w[1:])) and w[0]["start"] == 0.0 and abs(w[-1]["end"] - 1.9) < 0.15, w
assert 0.55 < w[2]["start"] < 0.95, w                                                         # "customer" starts near where it is heard
assert captions.align_script("", heard) == heard and captions.align_script("a b", []) == []
print("video sarvam ok")
