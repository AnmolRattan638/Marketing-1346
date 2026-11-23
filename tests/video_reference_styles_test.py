"""Offline test: the styles from the two reference reels (reference_styles.json) are wired end to end: caption styles exist in Remotion AND in the look presets,
new graphic layouts / mocks / transitions pass the schema and the resolver, and every colour stays on the brand palette."""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video-agent"))
from agent import graphics, looks, schema, fx_plan

SRC = ROOT / "video-agent/template/src"
ref = (SRC / "components/RefCaptions.tsx").read_text()
kit = (SRC / "components/captionKit.tsx").read_text()
tsx_styles = set(re.findall(r"^\s{2}(?:[a-z]+: [A-Z][A-Za-z]+,\s*)+", ref, re.M) and re.findall(r"\b([a-z]+): [A-Z][A-Za-z]+(?:,|\s*\n?\})", ref.split("export const REF_CAPTIONS")[1].split("};")[0]))
want = {"chest", "glass", "depth", "smoke", "wallink", "orbit", "bounce", "neon", "giant", "explode", "retro", "outline", "hierarchy", "goldcta", "serifface", "quoted"}
assert want <= tsx_styles, want - tsx_styles
for st in want:
    assert f'"{st}"' in kit.split("export type CaptionStyle")[1].split(";")[0], st      # the TS union knows it
    assert st in looks.CAPTIONS, st
used = {p["caption"] for p in looks.PRESETS}
assert want - {"goldcta"} <= used, f"every reference caption style has a look: {want - used}"      # goldcta is applied by manifest.py to the comment-keyword line
combos = {(p["mode"], p["bg"], p["caption"], p["variant"]) for p in looks.PRESETS}
assert len(combos) == len(looks.PRESETS) and len({p["name"] for p in looks.PRESETS}) == len(looks.PRESETS)
for p in looks.PRESETS:
    assert p["caption"] in looks.CAPTIONS and p["transitions"] in looks.TRANSITION_SETS

# transitions
assert {"sweep", "leak"} <= set(fx_plan.TRANSITIONS)
text = (ROOT / "video-agent/agent/schema.py").read_text()
assert '"sweep", "leak"' in text and '"numeral", "inverse", "tiles"' in text and '"tracker", "follow", "stickers"' in text
assert "sweep" in (SRC / "effects/motion.ts").read_text() and "ArrivalOverlay" in (SRC / "sequences/FootageScene.tsx").read_text()

# layouts and mocks resolve
W = [{"text": t, "start": 0.2 + i * 0.4, "end": 0.55 + i * 0.4} for i, t in enumerate("pehla music chuno phir cut lagao aur hook likho".split())]
def res(g, secs=6.0):
    return graphics.resolve_graphic({"graphic": g}, W, secs)
n = res({"layout": "numeral", "step": "1", "heading": "Music selection", "kicker": "Pick the sound first"})
assert n and n["layout"] == "numeral" and n["step"] == "1" and n["heading"] == "Music selection"
i = res({"layout": "inverse", "heading": "Ek message miss", "heading2": "ek customer gaya"})
assert i and i["heading"] == "Ek message miss ek customer gaya", i
t = res({"layout": "tiles", "heading": "5 easy edits", "kicker": "for engagement", "items": ["1", "2", "3", "4", "5"]})
assert t and t["items"] == ["1", "2", "3", "4", "5"] and len(t["times"]["items"]) == 5
assert res({"layout": "tiles", "heading": "x"}) is None and res({"layout": "numeral"}) is None, "no heading / no items falls back to footage"
for mk, items in (("tracker", ["Hook", "Proof", "CTA"]), ("follow", ["@arrdesigns", "Websites + AI bots"]), ("stickers", ["FREE", "live", "30+ styles", "just drag"])):
    r = res({"layout": "step", "heading": "Tips", "mock": {"type": mk, "title": "Tips", "items": items}})
    assert r and r["mock"]["type"] == mk and r["mock"]["items"] == items, mk

# brand palette: no hex colour outside theme.ts in the new files
for f in ("components/RefCaptions.tsx", "graphics/RefScenes.tsx", "graphics/mocks/RefMocks.tsx"):
    bad = re.findall(r"#[0-9a-fA-F]{6}\b", (SRC / f).read_text())
    assert not bad, (f, bad)
# graphic scenes keep the bottom pill for the placed styles (they would collide with the heading)
assert "REF_FIXED.has(captionStyle)" in (SRC / "sequences/GraphicScene.tsx").read_text()
print("reference styles ok")

mf = (ROOT / "video-agent/agent/manifest.py").read_text()
assert 'props["captionStyle"] = "goldcta"' in mf and "[A-Z][A-Z0-9]{2,}" in mf
