import os
import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "video-agent")]
from agent import looks
from agent.common import load_config


def lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


cfg = load_config()
seen = []
for n in range(1, 40):
    os.environ["GITHUB_RUN_NUMBER"] = str(n)
    seen.append(looks.pick_look("t", cfg)["name"])
assert all(a != b for a, b in zip(seen, seen[1:])), "two reels in a row share a look"
assert len(set(seen)) == len(looks.PRESETS)
combos = {(p["mode"], p["bg"], p["caption"], p["variant"]) for p in looks.PRESETS}
assert len(combos) == len(looks.PRESETS)
base = cfg["brand"]["palette"]
for p in looks.PRESETS:
    pal = looks.palette_mode(p["mode"], base)
    assert ratio(pal["text"], pal["bgTop"]) >= 7, (p["name"], "text contrast")
    assert ratio(pal["accent"], pal["bgTop"]) >= 3.5, (p["name"], "accent contrast")
os.environ["GITHUB_RUN_NUMBER"] = "5"
cfg2 = {**cfg, "looks": {"force": {"preset": "ink-karaoke"}}}
assert looks.pick_look("t", cfg2)["name"] == "ink-karaoke"
print("video looks ok")
