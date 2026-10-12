"""Offline tests: Instagram auto on normal days, manual on Wednesday; text-card image fallback."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import config, publish
from src.agents import image

# --- publish modes
class Fake:
    name, secrets = "fake", []
    def post(self, platform, text, image_url, image_path):
        return f"ok {platform} img={'yes' if image_url else 'no'}"
publish.PROVIDERS = [Fake]
base = {"posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}}
auto = publish.publish_draft({**base, "instagram_mode": "auto_image", "image": {"path": "data/media/x.jpg"}})
assert auto["instagram"]["ok"] and "img=yes" in auto["instagram"]["detail"] and set(auto) == {"instagram", "linkedin", "bluesky"}, auto
noimg = publish.publish_draft({**base, "instagram_mode": "auto_image", "image": {"path": None}})
assert not noimg["instagram"]["ok"] and noimg["linkedin"]["ok"], noimg
manual = publish.publish_draft({**base, "instagram_mode": "manual_reel", "image": {"path": "data/media/x.jpg"}})
assert "instagram" not in manual and manual["linkedin"]["ok"] and manual["bluesky"]["ok"], manual

# --- config: only Wednesday is manual
assert config.services()["instagram"]["manual_reel_weekdays"] == [2]

# --- fallback card when every AI engine fails
tmp = pathlib.Path(tempfile.mkdtemp())
config.ROOT, config.MEDIA = tmp, tmp
(tmp / "data").mkdir()
config.MEDIA = tmp / "data"
image.llm.gemma = lambda p, s="", **k: json.dumps({"style": "chat", "headline": "A customer messages you at 11 pm. When do they get a reply?",
    "highlight": ["reply?"], "sub": "No reply by morning.", "chat": [{"side": "left", "text": "Are you open tomorrow?", "time": "11:42 PM"}]}) if "JSON" in p else "a prompt"
plan0 = {"topic": "t", "hooks": [{"text": "Your website is slow"}], "chosen_hook": 0}
d0 = image.run(plan0, {"id": "chatbot", "name": "Chatbot"}, "2026-10-10")
assert d0["engine"] == "designed_card" and d0["ai_generated"] is False and d0["spec"]["cta"] == 'DM "BOT"', d0
assert b"trainedAlgorithmicMedia" not in (tmp / d0["path"]).read_bytes()
from src.agents import cards
def boom(*a, **k): raise RuntimeError("engine down")
cards.render = boom                 # designed card fails -> AI engines -> plain text card
image._pollinations = boom
plan = {"topic": "t", "hooks": [{"text": "Your website loads in six seconds, so customers leave before they see it"}], "chosen_hook": 0}
out = image.run(plan, {"name": "Websites"}, "2026-10-11")
assert out["engine"] == "text_card" and out["path"], out
raw = (tmp / out["path"]).read_bytes()
assert raw[:2] == b"\xff\xd8" and b"trainedAlgorithmicMedia" not in raw   # a text card must not be labelled AI-generated
print("mode tests passed: auto/manual publish, Wednesday-only manual, text-card fallback ->", out["path"])
