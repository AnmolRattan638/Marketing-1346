"""Offline test: the image style guide (shared style DNA + rotating visual families) keeps pictures consistent without copying a reference,
and the family used is saved on the draft so the weekly review can compare them."""
import json, pathlib, re, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import config, llm
from src.agents import image
import src.agents.cards as cards

ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = json.load(open(ROOT / "config/image_style.json"))
tmp = pathlib.Path(tempfile.mkdtemp())
config.DRAFTS = tmp / "drafts"
config.DRAFTS.mkdir()

# ---- 1. the style file: complete, and nothing in it can make a model draw text, numbers or a layout
vs = cfg["variants"]
assert len(vs) >= 4 and len({v["id"] for v in vs}) == len(vs) and all({"id", "name", "look", "elements", "accent"} <= set(v) for v in vs)
blob = " ".join([cfg["style_dna"]] + [f"{v['look']} {v['elements']} {v['accent']}" for v in vs])
assert not image.LAYOUT_WORDS.search(blob), "no layout words in the style text"
assert not re.search(r"[0-9$%]|\b(?:logo|watermark|headline|caption|label)\b", blob.replace("lower 40%", "lower area"), re.I), "no numbers, currency or text words in the style text (except the lower 40% rule)"
assert "lower 40%" in cfg["style_dna"], "the card puts the headline over the lower part"
assert cfg["quality_suffix"].startswith("Ultra-sharp 4K") and cfg["quality_suffix"] == image.DEFAULT_SUFFIX

# ---- 2. rotation: never the same family twice in a row, every family gets used, usage stays balanced, only earlier posts count
def save(date, sid):
    config.save_json(config.DRAFTS / f"{date}.json", {"date": date, "image": {"style_id": sid}})

assert image.pick_variant("2026-10-20")["id"] == vs[0]["id"]
seq = []
for day in range(1, 13):
    date = f"2026-10-{day:02d}"
    v = image.pick_variant(date)
    seq.append(v["id"])
    save(date, v["id"])
assert all(a != b for a, b in zip(seq, seq[1:])) and set(seq[:5]) == {v["id"] for v in vs}, seq
counts = [seq.count(v["id"]) for v in vs]
assert max(counts) - min(counts) <= 1, counts
assert image.pick_variant("2026-10-01")["id"] == vs[0]["id"], "drafts from the future are ignored"
image_style_saved = config.load_json(config.DRAFTS / "2026-10-03.json", {})["image"]["style_id"]
assert image_style_saved == seq[2]

# ---- 3. the prompt: shared look + ONE family, at most two of its elements, one new element from the topic, no copying
plan = {"hooks": [{"text": "Stop hunting leads. Start spotting them."}], "chosen_hook": 0, "topic": "finding local businesses that need clients", "image_idea": "a map"}
focus = {"id": "lead_gen", "name": "Lead generation (LocalSignal)"}
seen = []
good = "A laptop showing a glowing city map with bright location pins over small shopfronts, a cup of tea beside it, deep blue light, calm dark lower area"
llm.gemma = lambda p, s="", **k: seen.append(p) or f"<prompt>{good}</prompt>"
v = vs[0]
out = image.picture_prompt(plan, focus, {}, "", v)
q = seen[0]
for need in (cfg["style_dna"], v["name"], v["look"], v["elements"], v["accent"], "at most two of these elements", "ONE new element", plan["topic"], "Copy no existing artwork", "NEVER describe a layout"):
    assert need in q, need
assert out.startswith(good) and out.endswith(cfg["quality_suffix"])
seen.clear()
image.style = lambda: {"quality_suffix": cfg["quality_suffix"]}                       # a config without families keeps the old single look
image.picture_prompt(plan, focus, {}, "", None)
assert image.OLD_LOOK in seen[0] and "ONE new element" not in seen[0]
image.style = lambda: cfg

# ---- 4. the fallback scene carries the style too
llm.gemma = lambda p, s="", **k: "<prompt>Left: a laptop. Right: a panel divided into four sections, grid, minimalist.</prompt>"
fb = image.picture_prompt(plan, focus, {}, "", v)
assert "city map" in fb and cfg["style_dna"] in fb and v["elements"] in fb and "Accent colour: electric cyan" in fb and fb.endswith(cfg["quality_suffix"]), fb
assert not image.LAYOUT_WORDS.search(fb.split("Ultra-sharp")[0])

# ---- 5. the family is returned by the engine step and by run(), so it lands on the draft
def fake_engine(prompt, path):
    pathlib.Path(path).write_bytes(b"x")
image._engines = lambda: [fake_engine]
llm.gemma = lambda p, s="", **k: f"<prompt>{good}</prompt>"
assert image._ai_picture(plan, focus, {}, "", tmp / "a.jpg", [], v)["style_id"] == "glass-ui"
assert image._ai_picture(plan, focus, {}, "", tmp / "b.jpg", [])["style_id"] is None
cards.make_spec = lambda plan, focus, guidance="": {"style": "visual", "headline": "H"}
image._visual_card = lambda plan, focus, spec, guidance, path, errors, variant=None: {"engine": "visual:x", "style_id": variant["id"]}
r = image.run(plan, focus, "2026-10-20", "")
assert r["style_id"] == image.pick_variant("2026-10-20")["id"] and r["style_id"] in {x["id"] for x in vs}
print("image style test passed: clean style file, rotation never repeats, prompt = shared look + one family + one new element, fallback keeps the style, family saved on the draft")
