"""Offline test: sound variety (no file more than 3 times, no immediate repeat), brand-only colours, topic-first planner prompt."""
import json, os, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent / "video-agent"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from agent import sfx_plan, plan as planmod, brand
from agent.common import load_config
from agent.manifest import sfx_stems, available_sfx

stems = sfx_stems()
assert len(stems) >= 30, "a real library, not 4 files"
assert {"whoosh", "pop", "click", "riser", "impact"} <= available_sfx()

# 40 cues in one reel: every file <= 3 uses, never the same file twice in a row, files come from the right family
kinds = ["whoosh", "pop", "click", "pop", "riser", "click", "whoosh", "pop"] * 5
scenes = [[{"type": k, "atSecond": i * 0.5 + j, "volume": 0.5} for j, k in enumerate(kinds[i * 4:(i + 1) * 4])] for i in range(10)]
sfx_plan.assign_files(scenes, stems, seed="t")
flat = [c for s in scenes for c in sorted(s, key=lambda c: c["atSecond"])]
from collections import Counter
use = Counter(c["file"] for c in flat)
assert max(use.values()) <= 3, use
assert all(sfx_plan.stem_kind(c["file"]) in sfx_plan.FAMILIES[c["type"]] for c in flat)
assert all(a["file"] != b["file"] for a, b in zip(flat, flat[1:])), "same sound twice in a row"
assert len(use) >= 12, ("too few different sounds", len(use))
# a tiny library cannot be over-used: extra cues are dropped, not repeated
tiny = [[{"type": "pop", "atSecond": i, "volume": 0.5} for i in range(20)]]
sfx_plan.assign_files(tiny, {"pop_1", "pop_2"}, seed="t")
assert len(tiny[0]) == 6 and max(Counter(c["file"] for c in tiny[0]).values()) == 3
# determinism
a = [[{"type": "pop", "atSecond": i, "volume": 0.5} for i in range(5)]]; b = json.loads(json.dumps(a))
sfx_plan.assign_files(a, stems, seed="x"); sfx_plan.assign_files(b, stems, seed="x")
assert [c["file"] for c in a[0]] == [c["file"] for c in b[0]]

# colours: the palette is the website's, and no component carries a colour of its own
cfg = load_config()
pal = cfg["brand"]["palette"]
assert pal["accent"] == "#F0C040" and pal["accent2"] == "#C9A84C" and pal["bgTop"] == "#06080D" and pal["bgBottom"] == "#0A1220"
css = ":root{--black:#111111;--gold:#abcdef;--gold-bright:#123456;--navy:#222222}"
got = brand.palette_from_css(css)
assert got["accent2"] == "#ABCDEF" and got["accent"] == "#123456" and got["bgBottom"] == "#222222" and got["muted"] == brand.DEFAULT["muted"]
allowed = {v.lower() for v in pal.values() if v.startswith("#")} | {"#000000", "#ffffff"}
src = ROOT / "template" / "src"
bad = []
for f in list((src / "graphics").rglob("*.ts*")) + list((src / "effects").glob("*.tsx")) + [src / "components" / "Captions.tsx", src / "components" / "CaptionStyles.tsx", src / "sequences" / "GraphicScene.tsx", src / "sequences" / "FootageScene.tsx"]:
    if f.name in ("theme.ts",):
        continue
    for m in re.findall(r"#[0-9a-fA-F]{6}\b", f.read_text()):
        bad.append((f.name, m))
assert not bad, bad                       # every hex colour lives in graphics/theme.ts (brand tokens)

# planner: the topic leads, the angle changes, no website default
captured = {}
def fake(messages, cfg):
    captured["u"] = messages[-1]["content"]; captured["s"] = messages[0]["content"]
    return json.dumps(planmod.sample_plan())
from unittest import mock
users = []
with mock.patch.object(planmod, "_call_groq", fake):
    for _ in range(12):
        planmod.make_plan("[chatbot] AI chatbot answers customers at night", cfg, "", "chatbot")
        users.append(captured["u"])
u = users[0]
assert "TOPIC (the subject of the whole video)" in u and "chatbot" in u.lower() and "Do NOT drift into websites" in u
assert "Talk about chatbots, not websites" in u
assert len({re.search(r"Angle for this video: (.*)\.", x).group(1) for x in users}) >= 3, "angles should vary run to run"
assert "Topic first" in captured["s"]
print("video sfx variety / brand / topic test passed")
