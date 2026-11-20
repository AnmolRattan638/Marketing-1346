import json, os, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from src import run_reel2 as r2
brand = {"services": [{"id": "chatbot", "priority": 1}, {"id": "animated_ads", "priority": 1}, {"id": "lead_gen", "priority": 1}, {"id": "website", "priority": 2}, {"id": "seo_blogs", "priority": 3}], "schedule": {}}
for first in ("chatbot", "animated_ads", "lead_gen", "website", "seo_blogs"):
    assert r2.other_focus(brand, [], first)["id"] != first, first          # reel 2 is never the same service as reel 1
# the video side: slot 2 reads only its own script
from agent import master_script as ms
tmp = pathlib.Path(tempfile.mkdtemp())
ms.EARLY = tmp; ms.DRAFTS = tmp
(tmp / "2026-11-19.json").write_text(json.dumps({"master_script": {"beats": [{"beat": "hook", "line": "reel one"}]}}))
os.environ.pop("REEL_SLOT", None)
assert ms.load(today="2026-11-19")["beats"][0]["line"] == "reel one"
os.environ["REEL_SLOT"] = "2"
assert ms.load(today="2026-11-19") is None                                  # no slot-2 script yet: never silently re-make reel 1
(tmp / "2026-11-19-2.json").write_text(json.dumps({"master_script": {"beats": [{"beat": "hook", "line": "reel two"}]}, "service": "website"}))
m = ms.load(today="2026-11-19")
assert m["beats"][0]["line"] == "reel two" and m["service"] == "website"
print("second reel test passed")
