"""No raw clips of your own: the reel is made from motion graphics (stock only as an option) instead of stopping."""
import os, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import hybrid
from agent.common import load_config

cfg = load_config()
empty = pathlib.Path(tempfile.mkdtemp()); (empty / "raw").mkdir(); (empty / "hero").mkdir()

for env in ({"EDITS_DIR": str(empty)}, {}):                      # an empty folder, and no folder connected at all
    os.environ.pop("EDITS_DIR", None); os.environ.pop("EDITS_DRIVE_URL", None); os.environ.update(env)
    ed = hybrid.Editor(cfg, False, "chatbot")                    # used to raise HybridError in strict mode
    assert ed.avail["raw"] is False and ed.no_raw_note and ed.hs["no_raw_stock_scenes"] == 2
    strict = {**cfg, "hybrid": {**cfg["hybrid"], "require_raw": True}}
    try: hybrid.Editor(strict, False, "chatbot"); assert False
    except hybrid.HybridError as e: assert "require_raw is on" in str(e)

# the audit does not demand raw shots when none exist
shots = [{"type": "stock", "seconds": 2.0, "credit": {}, "start": 0}]
assert not any("raw shot" in b for b in hybrid.audit(shots, {"raw": False, "stock": True, "photo": False}, hybrid.settings(cfg), {"first_shot": None, "shot_min": 1.0, "shot_max": 4.0}))
print("video no raw ok")
