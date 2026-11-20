"""Voice text: short forms, 9:16, customers, signs, full stops, takes with real pauses, per-sentence moods. HTTP mocked, no network."""
import base64, os, pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
os.environ["SARVAM_API_KEY"] = "k"
from agent import speech_text as st, sarvam, voice
from agent.common import media_duration

# 1. short forms and numbers are spoken in full
t = st.clean("Sirf 30 sec mein 9:16 reel, 50% log, 5k leads & 3x sales, 2 min lagega")
assert "second" in t and "sec " not in t, t
assert "nine by sixteen" in t and "9:16" not in t, t                      # a ratio, never "9 baje 16 minute"
assert "50 percent" in t and "5 thousand" in t and " and " in t and "3 times" in t and "2 minute" in t, t
assert "10:30 am" in st.expand("10:30 am") and "ten by thirty" not in st.expand("10:30 am")      # a real clock time is left alone
# 2. customers stay customers
assert "grahak" not in st.expand("Grahak aur grahakon ko").lower() and st.expand("Grahak ko").lower().startswith("customers")
assert st.untranslate("ग्राहकों को") == "कस्टमर्स को" and st.untranslate("ग्राहक") == "कस्टमर"
# 3. signs are never read; a missing full stop is added; a question is recognised
s = st.strip_signs('Ye *chatbot* (AI) → "kaam" karta hai 🔥 — sach: #1')
assert not any(c in s for c in '*#"→🔥—()'), s
assert st.clean("Ye chatbot kaam karta hai").endswith(".") and st.clean("Kya tumhe pata hai").endswith("?")
assert st.clean("Pehla. Kya tumhe pata hai").endswith("?") and st.clean("Kya tumhe pata hai? Ye sach hai").endswith(".")   # the LAST sentence decides
# 4. takes: sentence ends differ in pause, a long sentence is cut at its commas, a question pauses longer than a full stop
tk = st.sentences("Kya tumhe pata hai? Website se business premium dikhta hai, leads badhte hain, aur log bharosa karte hain. Bas itna.")
assert [x[2] for x in tk][0] == 0 and tk[-1][2] == 2
gaps = {x[0][-1]: x[1] for x in tk}
assert gaps["?"] > gaps["."] > 0.1 and any(g < 0.2 for _, g, _ in tk), tk                  # comma take = short breath
assert len(tk) == 4 and tk[1][0].endswith(","), tk
assert st.sentences("Aur ab...") [0][1] >= 0.5                                              # an ellipsis is the longest pause
# 5. Sarvam path: one request per take, mood per sentence from the model, exact pauses, dead air trimmed
d = pathlib.Path(tempfile.mkdtemp()); wav = d / "src.wav"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=200:duration=1.0", "-af", "apad=pad_dur=0.6", "-ar", "24000", "-ac", "1", wav], check=True)   # 0.6 s of dead air at the end
WAV = base64.b64encode(wav.read_bytes()).decode()
calls = []
class R:
    status_code = 200; text = "x"
    def json(s): return {"audios": [WAV]}
    def raise_for_status(s): pass
sarvam.requests.post = lambda url, headers=None, json=None, timeout=0: (calls.append(json), R())[1]
src = "Kya tumhe pata hai website ke fayde? Ye sach me kaam karta hai!"
asked = []
sarvam.prepare([src], lambda p: asked.append(p) or {"lines": [{"text": "क्या तुम्हें पता है वेबसाइट के फायदे? ये सच में काम करता है!", "moods": ["curious", "excited"]}]})
assert "NEVER translate" in asked[0] and "MOOD" in asked[0] and "customer" in asked[0]
assert sarvam.MOODS[src] == ["curious", "excited"]
cfg = {"voice_engine": "sarvam", "language": "hi", "voice_language": "hi", "voices": {"hi": {"sarvam": {"candidates": [{"model": "bulbul:v4-flash", "speaker": "aayan_hi_conversational"}]}}}}
secs = voice.synth(src, d / "a.mp3", cfg, False, "calm", "pain")
assert len(calls) == 2, [c["text"] for c in calls]
assert calls[0]["pace"] == sarvam.EMOTION["curious"][0] and calls[1]["pace"] == sarvam.EMOTION["excited"][0] and calls[1]["pitch"] > calls[0]["pitch"]   # the tag changes how it is said
assert not any(ch in c["text"] for c in calls for ch in "*#\"") and calls[0]["text"].endswith("?") and calls[1]["text"].endswith("!")
want = 1.0 + 0.34 + 1.0 + 0.45                                                              # speech + the ? pause + speech + the pain beat's pause (dead air is cut)
assert abs(secs - want) < 0.25, (secs, want)
# 6. the non-Sarvam engines get the same cleaned text
seen = []
voice.ENGINES["edge"] = lambda text, mp3, vcfg: (seen.append(text), mp3.write_bytes(b"x"))
voice.media_duration = lambda p: 1.0
voice.synth("Sirf 30 sec mein 9:16", d / "e.mp3", {"voice_engine": "edge", "language": "hi", "voices": {"hi": {"edge": "x"}}}, False)
assert seen == ["Sirf 30 second mein nine by sixteen."], seen
print("voice text test passed")
