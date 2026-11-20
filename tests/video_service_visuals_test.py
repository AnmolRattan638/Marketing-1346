import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import scenarios as sc, looks
SERVICES = ("website", "chatbot", "animated_ads", "lead_gen", "reel_scripts", "seo_blogs")
for s in SERVICES:
    spec = sc.spec(s)
    assert spec["beforeItems"] and spec["afterItems"], s
    sc.use(s)
    assert len(sc.hook_notifs()) == 3
# no service sees another service's picture or words
ads = sc.spec("animated_ads"); txt = " ".join([ads["beforeTitle"], ads["afterTitle"], *ads["beforeItems"], *ads["afterItems"]]).lower()
assert "website" not in txt and "chatbot" not in txt, txt
sc.use("animated_ads"); assert not any("whatsapp" in n.lower() for n in sc.hook_notifs())
assert sc.demo_kind("chatbot", "x") == "chat" and sc.demo_kind("website", "x") == "site"
assert all(sc.demo_kind(s, "x") is None and s in sc.DEMO_STEPS for s in ("animated_ads", "lead_gen", "reel_scripts", "seo_blogs"))
# the eight looks use distinct backdrops where it counts
assert len({p["bg"] for p in looks.PRESETS}) >= 7, [p["bg"] for p in looks.PRESETS]
print("service visuals test passed")
