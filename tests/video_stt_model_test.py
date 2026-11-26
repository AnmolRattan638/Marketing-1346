"""Word timing must use Whisper even when config.json has no captions.model (it was missing: KeyError 'model', every reel fell back to estimated times)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video-agent"))
from agent import captions

sent = {}
class R:
    status_code = 200
    def raise_for_status(self): pass
    def json(self): return {"words": [{"word": " hi", "start": 0.0, "end": 0.3}]}
def fake_post(url, headers=None, files=None, data=None, timeout=0):
    sent.update(data); return R()
captions.requests.post = fake_post
captions.groqkeys.rotated = lambda: ["k"]
mp3 = ROOT / "tests" / "_stt.mp3"; mp3.write_bytes(b"x")
try:
    for cfg in ({}, {"captions": {}}, {"captions": {"smart_position": True}}):
        sent.clear(); out = captions._transcribe(mp3, "hi", cfg)
        assert sent["model"] == "whisper-large-v3-turbo" and out[0]["text"] == "hi", (cfg, sent)
    sent.clear(); captions._transcribe(mp3, "hi", {"captions": {"model": "x"}}); assert sent["model"] == "x"
finally:
    mp3.unlink()
assert json.loads((ROOT / "video-agent" / "config.json").read_text())["captions"]["model"]
print("stt model ok")
