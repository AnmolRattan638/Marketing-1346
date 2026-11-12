"""Offline test: picture, SFX, captions and B-roll stay in sync with the narration (cuts on words, SFX on cuts and emphasis words, per-shot B-roll)."""
import tempfile, json, os, pathlib, random, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent / "video-agent"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
for k in ("EDITS_DIR", "EDITS_DRIVE_URL", "PEXELS_API_KEY", "PIXABAY_API_KEY", "COVERR_API_KEY", "UNSPLASH_ACCESS_KEY"):
    os.environ.pop(k, None)
from agent import hybrid, sfx_plan, style
from agent.common import load_config
from agent.schema import validate_plan

prof = dict(style.DEFAULT)
cfg = load_config()

# 1. cuts land on the start of a spoken word (a hair early), shots stay inside the Hero range, the scene length does not change
rng = random.Random(1)
for seed in range(80):
    rng = random.Random(seed)
    total = rng.uniform(3.0, 8.0)
    words, t = [], 0.0
    while t < total - 0.3:
        d = rng.uniform(0.18, 0.5); words.append({"text": "w", "start": round(t, 3), "end": round(t + d, 3)}); t += d + rng.uniform(0, 0.12)
    durs = hybrid.split_scene(total, prof, rng, words)
    assert abs(sum(durs) - total) < 1e-6, (seed, sum(durs), total)
    assert all(prof["shot_min"] * 0.6 <= d <= prof["shot_max"] * 1.5 for d in durs), (seed, durs)
    starts = [w["start"] - hybrid.CUT_LEAD for w in words]
    cum = 0.0
    snapped = 0
    for d in durs[:-1]:
        cum += d
        if any(abs(cum - s) < 1e-6 for s in starts):
            snapped += 1
    assert snapped >= len(durs[:-1]) - 1, f"seed {seed}: only {snapped} of {len(durs) - 1} cuts sit on a word start: {durs}"
assert hybrid.split_scene(5.0, prof, random.Random(3)), "no words: still cuts by rhythm"

# 2. SFX are placed from real times
words = [{"text": "Most", "start": 0.0, "end": 0.3}, {"text": "customers", "start": 0.3, "end": 0.9}, {"text": "search", "start": 0.9, "end": 1.4},
         {"text": "online", "start": 2.0, "end": 2.6}, {"text": "today.", "start": 3.2, "end": 3.7}]
scene = {"sfx": [{"type": "pop", "at": "word", "at_word": "online"}, {"type": "riser", "at": "word", "at_word": "today"}]}
avail = {"whoosh", "pop", "riser", "click"}
beats = sfx_plan.emphasis_beats(scene, words)
assert beats == [("online", 2.0), ("today.", 3.2)], beats
cuts = [{"at": 1.5, "kind": "cut", "type": "stock", "effect": "none"}, {"at": 2.2, "kind": "fade", "type": "photo", "effect": "none"},
        {"at": 3.0, "kind": "cut", "type": "raw", "effect": "none"}]
LOUD = {"cut_sounds": True, "scene_whoosh": "always", "max_per_scene": 5}
cues = sfx_plan.plan_sfx(2, scene, words, avail, cuts, policy=LOUD)
by = lambda k: [c for c in cues if c["type"] == k]
assert by("pop") and by("pop")[0]["atSecond"] == 2.0, "the pop lands on the first sound of its word"
assert abs(by("riser")[0]["atSecond"] - (3.2 - sfx_plan.RISER_SECONDS)) < 1e-6, "the riser ends on its word"
assert any(abs(c["atSecond"] - (1.5 - sfx_plan.LEAD["whoosh"])) < 1e-6 for c in by("whoosh")), "the cutaway whoosh peaks on the cut"
assert not any(abs(c["atSecond"] - 2.2) < 0.25 for c in cues if c["type"] != "pop"), "a dissolve gets no sound"
hits = [c for c in cues if c["type"] != "riser"]
assert all(b["atSecond"] - a["atSecond"] >= sfx_plan.MIN_GAP - 1e-6 for a, b in zip(hits, hits[1:])), "transients never stack"
assert len(cues) <= 5 and cues == sorted(cues, key=lambda c: c["atSecond"])
many = [{"at": 0.4 * i, "kind": "cut", "type": "stock", "effect": "none"} for i in range(1, 14)]
crowded = sfx_plan.plan_sfx(1, scene, words, avail, many, policy=LOUD)
assert any(c["type"] == "pop" for c in crowded) and any(c["type"] == "riser" for c in crowded), "planner hints beat automatic cut sounds"
assert len(crowded) <= 5

# 3. the plan accepts per-scene B-roll; each cutaway shot uses the next query
plan = json.loads((ROOT / "examples" / "sample_plan.json").read_text())
assert validate_plan(plan) == [] and all(len(s["broll"]) >= 2 for s in plan["scenes"] if not s.get("graphic"))
bad = json.loads(json.dumps(plan)); bad["scenes"][0]["broll"] = ["ok words", "x"]
assert validate_plan(bad), "a too-short B-roll query is rejected"
ed = hybrid.Editor(cfg, True, "general")
asked = []
orig = ed._fill
def spy(s, words_, scene_, base, i):
    asked.append((s["type"], scene_["footage_query"]))
    return orig(s, words_, scene_, base, i)
ed._fill = spy
sc = {"footage_query": "main look", "narration": "a b c", "broll": ["first cutaway", "second cutaway"]}
ed.prepare([("s1", sc, 9.0)], pathlib.Path(tempfile.mkdtemp()), {"s1": [{"text": "a", "start": 0.2, "end": 0.5}]})
non_raw = [q for t, q in asked if t != "raw"]
raw = [q for t, q in asked if t == "raw"]
assert non_raw[:2] == ["first cutaway", "second cutaway"][:len(non_raw[:2])] and set(non_raw) <= {"first cutaway", "second cutaway"}, asked
assert set(raw) == {"main look"}, "your own footage keeps the scene's main look"
assert all("t0" in s for s in ed.shots) and abs(sum(s["seconds"] for s in ed.shots) - 9.0) < 0.5

# 3b. animation effects (agent/fx_plan.py): anchored to spoken words, kept inside the scene, one graphic at a time, each with its own sound
from agent import fx_plan
fxw = [{"text": "Most", "start": 0.1, "end": 0.4}, {"text": "73%", "start": 0.5, "end": 1.0}, {"text": "search", "start": 1.2, "end": 1.6},
       {"text": "online,", "start": 1.7, "end": 2.2}, {"text": "never", "start": 3.4, "end": 3.8}]
fcfg = {"fx": {"enabled": True, "max_per_scene": 2, "default_transition": "settle"}}
got = fx_plan.plan_fx({"fx": [{"type": "stat", "at_word": "73%", "value": 73, "suffix": "%", "label": "x"}]}, fxw, 4.0, fcfg)
assert got and got[0]["atSecond"] == 0.5 and got[0]["value"] == 73 and got[0]["suffix"] == "%", got
assert fx_plan.plan_fx({"fx": [{"type": "glitch", "at_word": "missing", "text": "A"}]}, fxw, 4.0, fcfg) == [], "a word that is not spoken: no graphic"
late = fx_plan.plan_fx({"fx": [{"type": "title", "at_word": "never", "text": "T", "seconds": 4}]}, fxw, 4.0, fcfg)
assert late and late[0]["atSecond"] + late[0]["seconds"] <= 4.0 - 0.09, "a graphic never outlives its scene"
assert fx_plan.plan_fx({"fx": [{"type": "title", "at_word": "never", "text": "T", "seconds": 4}]}, fxw, 3.6, fcfg) == [], "no room left: skipped"
two = fx_plan.plan_fx({"fx": [{"type": "stat", "at_word": "73%", "value": 1}, {"type": "title", "at_word": "search", "text": "T", "seconds": 2}]}, fxw, 6.0, fcfg)
assert [f["type"] for f in two] == ["stat"], "two graphics never overlap"
sh = fx_plan.plan_fx({"fx": [{"type": "stat", "at_word": "73%", "value": 1}, {"type": "shake", "at_word": "search"}]}, fxw, 6.0, fcfg)
assert [f["type"] for f in sh] == ["stat", "shake"], "a camera shake may run under a graphic"
assert len(fx_plan.plan_fx({"fx": [{"type": "glitch", "text": "A"}, {"type": "title", "text": "B"}, {"type": "stat", "value": 1}]}, fxw, 9.0, fcfg)) <= 2
assert fx_plan.plan_fx({"fx": [{"type": "glitch", "text": "A"}]}, fxw, 4.0, {"fx": {"enabled": False}}) == [], "fx can be switched off in config.json"
assert fx_plan.resolve_transition({"transition": "whip"}, 0, fcfg) == "settle", "the first scene has nothing to arrive from"
assert fx_plan.resolve_transition({"transition": "whip"}, 2, fcfg) == "whip" and fx_plan.resolve_transition({}, 2, fcfg) == "settle"
assert fx_plan.resolve_transition({"transition": "nonsense"}, 2, fcfg) == "settle"
fx_cues = sfx_plan.plan_sfx(1, {"sfx": []}, fxw, avail, None, got)
quiet = sfx_plan.plan_sfx(2, {"sfx": []}, fxw, avail, cuts)
assert not any(c["type"] in ("whoosh", "click") for c in quiet), "default policy: no sound on plain cuts or plain scene starts"
assert any(c["type"] == "whoosh" and c["atSecond"] == 0.0 for c in sfx_plan.plan_sfx(2, {"sfx": []}, fxw, avail, None, None, "circle")), "a visible wipe gets its whoosh"
assert any(c["type"] == "pop" and c["atSecond"] == 0.5 for c in fx_cues), "a stat appears with its pop"
badfx = json.loads(json.dumps(plan)); badfx["scenes"][0]["fx"] = [{"type": "confetti"}]
assert validate_plan(badfx), "an unknown effect type is rejected"
assert validate_plan(plan) == [] and any(s.get("fx") for s in plan["scenes"]) and any(s.get("transition") for s in plan["scenes"])

# 4. the manifest of a whole offline run lines picture, audio and captions up
import subprocess
r = subprocess.run([sys.executable, "-m", "agent.run", "--offline", "--no-render"], capture_output=True, text=True)
assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
import glob, shutil
run_dir = sorted(glob.glob(str(ROOT / "runs" / "*")))[-1]
m = json.loads((pathlib.Path(run_dir) / "manifest.json").read_text())
credits = json.loads((pathlib.Path(run_dir) / "credits.json").read_text())
fps = m["video"]["fps"]
for i, (scn, cr) in enumerate(zip(m["scenes"], credits)):
    p, dur = scn["props"], scn["duration"]
    if scn["component"] == "sequences/GraphicScene":                                           # a motion graphic: every element lands on a spoken word, inside the scene
        t = p["times"]
        spoken = [w["start"] for w in p["words"]]
        assert 0 <= t["heading"] < dur and all(0 <= x < dur for x in t["items"]), (scn["id"], t)
        assert all(any(abs(x - s0) < 0.6 for s0 in spoken) for x in t["items"] if p["layout"] in ("strike", "step")), (scn["id"], t, spoken)
    else:
        shot_total = sum(s["seconds"] for s in cr["shots"])
        assert abs(shot_total - dur) < 0.3, (scn["id"], shot_total, dur)                      # picture length = narration length
    assert all(0 <= c["atSecond"] <= dur for c in scn["sfx"]), scn["sfx"]                     # every SFX inside its scene
    assert all(w["end"] <= dur + 1e-6 for w in p["words"]), "caption words stay inside the scene"
    starts = {round(w["start"], 3) for w in p["words"] if w["text"].strip(".,!?").lower() in {e.strip(".,!?").lower() for e in p["emphasis"]}}
    fx_starts = {round(f["atSecond"], 3) for f in p["fx"] if f["type"] in ("stat", "glitch", "title")}
    assert set(p["pulses"]) <= starts | fx_starts, (p["pulses"], starts, fx_starts)           # the zoom pulse lands on an emphasis word or a graphic
    assert ("fadeOutFrames" in p) == (i == len(m["scenes"]) - 1), "only the last scene fades to black"
    assert p["transitionIn"] in fx_plan.TRANSITIONS and (i > 0 or p["transitionIn"] == "settle")
    for f in p["fx"]:                                                                          # graphics sit on a spoken word and inside the scene
        assert 0 <= f["atSecond"] and f["atSecond"] + f["seconds"] <= dur + 1e-6, (scn["id"], f)
        if f["type"] in ("stat", "glitch", "title"):
            assert f["atSecond"] in p["pulses"], "the picture hits with the graphic"
        assert any(abs(c["atSecond"] - max(0, f["atSecond"] - sfx_plan.LEAD.get(fx_plan.SFX_FOR[f["type"]], 0))) < 0.35 for c in scn["sfx"]), (scn["id"], f, scn["sfx"])
shutil.rmtree(run_dir, ignore_errors=True)
assert m["scenes"][-1]["id"] == "outro" and m["scenes"][-1]["props"]["layout"] == "logo", "the reel ends on the logo animation"
assert sum(1 for c in credits if c.get("source") in ("stock", "photo") or any(x.get("type") in ("stock", "photo") for x in c.get("shots", []))) <= 1
# 5. smart caption placement: a flat picture keeps the bottom position, a busy lower half moves the captions up, a broken file never stops a reel
from agent import caption_zones as cz
tmp = pathlib.Path(tempfile.mkdtemp())
def _mk(name, fc):
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=1080x1920:r=30:d=4", "-filter_complex", fc, "-pix_fmt", "yuv420p", str(tmp / name), "-y"], check=True)
_mk("flat.mp4", "[0:v]null")
_mk("busy_bottom.mp4", "[0:v]split[a][b];[b]drawgrid=w=40:h=40:t=6:c=black,crop=1080:1100:0:820[n];[a][n]overlay=0:820")
assert cz.plan_zones(tmp / "flat.mp4", 4) in ([], [{"from": 0.0, "y": 1400, "to": 4}]), "a clear picture keeps the bottom position"
z = cz.plan_zones(tmp / "busy_bottom.mp4", 4)
assert z and z[0]["y"] < 1000 and z[0]["from"] == 0.0 and z[-1]["to"] == 4, z
assert cz.zones_for(tmp / "missing.mp4", 4) == []
print("video sync test passed: cuts on words, SFX on cuts and emphasis words, per-shot B-roll, fx on spoken words, manifest lines up")
