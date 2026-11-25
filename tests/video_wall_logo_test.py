"""Offline test: the logo goes on the wall behind the presenter in a few big-presenter cuts, never the hook or the last scene."""
import os, pathlib, sys
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "video-agent"))
os.chdir(REPO / "video-agent")
from agent import avatar

frames = [90, 120, 120, 120, 120, 120, 90]
starts = [sum(frames[:i]) for i in range(len(frames))]
cuts = [{"f": s, "n": n, "frame": "none" if i == 0 else "full"} for i, (s, n) in enumerate(zip(starts, frames))]
assert avatar._wall_logo(cuts, frames, {}) is None          # off by default: the branded backdrop already carries the look
path = avatar._wall_logo(cuts, frames, {"backdrop_logo": True})
assert path and path.endswith("backdrop_logo.png")
marked = [i for i, c in enumerate(cuts) if c.get("logo")]
assert marked == [1, 3, 5] and 0 not in marked and len(frames) - 1 not in marked, marked
cuts2 = [{"f": s, "n": n, "frame": "full"} for s, n in zip(starts, frames)]
assert sum(1 for c in avatar._wall_logo(cuts2, frames, {"backdrop_logo": True, "backdrop_logo_max": 1}) and cuts2 if c.get("logo")) == 1
assert avatar._wall_logo(cuts, frames, {"backdrop_logo": False}) is None
print("ok")
