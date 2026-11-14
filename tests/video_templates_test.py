"""Offline test: animation templates are picked per reel, vary between reels, fit the scene, and only ever carry our own words."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import templates as T
T.STATE = pathlib.Path(tempfile.mkdtemp()) / "last.json"
cfg = json.load(open(pathlib.Path(__file__).resolve().parent.parent / "video-agent" / "config.json"))
assert cfg["templates"]["enabled"]
# every imported template exists on disk and every selectable one is imported
root = pathlib.Path(__file__).resolve().parent.parent / "video-agent" / "template" / "src" / "locomotion"
files = {f.stem for f in (root / "templates").glob("*.tsx")}
assert len(files) >= 60 and set(T.SELECTABLE) <= files, set(T.SELECTABLE) - files
src = "".join(f.read_text() for f in (root / "templates").glob("*.tsx")) + (root / "styles.ts").read_text()
import re
assert not re.search(r"#[0-9a-fA-F]{3,6}\b", src), "off-brand hex left in the imported templates"
assert not re.search(r"rgba?\((?!6,8,13|232,235,242|240,192,64)\s*\d", src.replace(" ", "")), "off-brand rgb left"

def reel(n):
    g, v = {}, []
    for i in range(n):
        sid = f"s{i}"
        lay = ["title", "strike", "punch", "title", "strike", "punch"][i % 6]
        g[sid] = {"layout": lay, "heading": f"Heading number {i}", "heading2": "", "kicker": "k", "chips": ["a"], "mock": None,
                  "items": ["One thing", "Two things", "Three things", "Four things"] if lay == "strike" else [], "times": {"heading": 0.3, "mock": 0, "items": [1, 2, 3, 4], "chips": 0},
                  "sfx": [{"type": "click", "atSecond": 1, "volume": .3}]}
        v.append((sid, {}, 4.5, None, []))
    return g, v
seen_variants, seen_ids = [], []
for day in range(6):
    g, v = reel(6)
    done = T.apply(g, v, cfg, f"2026-11-{10+day}|topic")
    assert 1 <= len(done) <= 2, done
    seen_variants.append(done[0]["variant"]); seen_ids += [d["template"] for d in done]
    for d in done:
        gp = g[d["scene"]]
        assert gp["layout"] == "tpl" and gp["tpl"]["id"] in T.SELECTABLE and gp["tpl"]["variant"] in T.VARIANTS
        assert T.SELECTABLE[gp["tpl"]["id"]] / 30 + gp["tpl"]["atFrame"] / 30 <= 4.5 + 0.4 + 1e-6      # finishes inside the scene
        assert gp["sfx"][0]["type"] == "pop" and gp["mock"] is None
        words = json.dumps(gp["tpl"]["props"])
        assert "Acme" not in words and "$" not in words                                         # only our own words
    ids = [d["scene"] for d in done]
    assert len(ids) < 2 or abs(int(ids[0][1:]) - int(ids[1][1:])) >= 2                           # never two template scenes back to back
assert all(a != b for a, b in zip(seen_variants, seen_variants[1:])), seen_variants          # the style variant differs from the previous reel's
assert len(set(seen_ids)) >= 5, seen_ids                                                        # and the templates rotate
# a list template needs 3+ items; text templates need a heading
assert T.props_for("screen-showcase", {"items": ["a", "b"]}) is None and "bento-grid" not in T.SELECTABLE and T.props_for("bold-text-punch", {"heading": ""}) is None
assert T.props_for("onboarding-flow", {"heading": "Steps", "items": ["a", "b", "c", "d", "e"]})["steps"] == "a,b,c,d"
assert "," not in T.props_for("meme-card", {"heading": "A, b"})["topText"]
# scenes too short for the animation get none; footage-only reels get none
g, v = reel(2)
for s in g.values(): s["times"]["heading"] = 0.3
assert T.apply(g, [(a, b, 0.5, c, d) for a, b, _, c, d in v], cfg, "x") == [] and T.apply({}, [], cfg, "x") == []
off = dict(cfg, templates={"enabled": False}); g, v = reel(4); assert T.apply(g, v, off, "x") == []
print("video templates ok")
