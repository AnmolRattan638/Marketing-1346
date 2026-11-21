"""Offline test: the SFX kit (320 CC0 sounds) places every effect on its exact sync point and level, and can never stop a draft."""
import json, os, pathlib, shutil, sys, tempfile
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "video-agent"))
os.chdir(REPO / "video-agent")
from agent import manifest, sfx_plan, sfxkit

cat = sfxkit.load()
# 1. the import is complete and sane
assert len(cat) == 320 and len(list(sfxkit.DIR.glob("*.mp3"))) == 320 and (sfxkit.DIR / "LICENSE.txt").exists()
assert all(0 <= e["sync_at"] <= e["duration"] + 0.01 and -40 < e["lufs"] < 0 and -12 <= e["under_voice_db"] <= 0 for e in cat.values())
assert sum(e["avoid_voice"] for e in cat.values()) == 57
# 2. every kind has sounds; nothing that masks a voice, and the unsuitable variants, are ever offered
for kind in ("whoosh", "pop", "click", "riser", "impact", "number"):
    assert sfxkit.entries(kind), kind
every = {i for k in sfxkit.RULES for i, _ in sfxkit.entries(k)}
assert not [i for i in every if cat[i]["avoid_voice"]] and not [i for i in every if i.startswith(("sting-", "bass-", "boom-", "cinematic-"))]
assert not [i for i, _ in sfxkit.entries("whoosh") if i.endswith(("-hard", "-strong")) or "zip-out" in i] and not [i for i, _ in sfxkit.entries("pop") if i.endswith("-out")]
assert [i for i, _ in sfxkit.entries("number")] == ["data-number-land"]

# 3. placement: a kit sound starts at (target - sync_at), at the kit volume; a sound that cannot start inside the scene is not used
cue = lambda kind, target, vol=0.55, at=None: {"src": f"assets/run/sfx/{kind}.mp3", "atSecond": at if at is not None else target, "volume": vol, "type": kind, "target": target}
legacy = {"whoosh_1", "whoosh_2", "pop_1", "riser_1", "click_1", "impact_1"}
cues = [cue("whoosh", 2.0), cue("pop", 3.0, 0.7)]
sfx_plan.assign_files([cues], legacy, seed="t")
for c in cues:
    e = sfxkit.get(c["file"])
    assert e, f"a kit sound was chosen for {c['type']}"
    assert c["atSecond"] == round(max(0.0, c["target"] - e["sync_at"]), 3) and c["src"] == f"assets/run/sfx/{c['file']}.mp3"
    assert c["volume"] == sfxkit.volume(0.55 if c["type"] == "whoosh" else 0.7, e)
early = [cue("riser", 0.4, 0.5, at=0.0)]                 # a riser that would have to start before the scene: not possible with any kit riser
sfx_plan.assign_files([early], legacy, seed="t")
assert early[0]["file"] == "riser_1" and early[0]["atSecond"] == 0.0, "falls back to the plain riser file"
late = [cue("riser", 4.0, 0.5, at=2.6)]
sfx_plan.assign_files([late], legacy, seed="t")
e = sfxkit.get(late[0]["file"]); assert e and late[0]["atSecond"] == round(4.0 - e["sync_at"], 3) and e["meets"] == "arrival", "a riser's arrival lands on the word"

# 4. levels: scaled to the kit reference and down by each sound's own under-voice amount; always inside 0.05..1
quiet, loud = {"under_voice_db": -8}, {"under_voice_db": -1}
assert sfxkit.volume(0.55, quiet) < sfxkit.volume(0.55, loud) <= 1.0 and sfxkit.volume(0.7, {"under_voice_db": 0}) == 1.0 and sfxkit.volume(0.0, loud) == 0.05

# 5. variety: no file more than MAX_USES times, never the same file twice in a row, same seed = same reel
many = lambda: [[cue("pop", 1.0 + i * 0.5, 0.7) for i in range(20)]]
a, b = many(), many()
sfx_plan.assign_files(a, legacy, seed="reel"); sfx_plan.assign_files(b, legacy, seed="reel")
files = [c["file"] for c in a[0]]
assert files == [c["file"] for c in b[0]] and all(files.count(f) <= sfx_plan.MAX_USES for f in set(files)) and all(x != y for x, y in zip(files, files[1:]))
assert len(set(files)) >= 8, "a 20-pop reel uses many different sounds"

# 6. a stat counter is still a 'pop' cue, but plays the number-landing sound
words = [{"text": "ye", "start": 0.2, "end": 0.4}]
cues = sfx_plan.plan_sfx(1, {"sfx": []}, words, {"pop", "whoosh"}, None, [{"type": "stat", "atSecond": 0.5}])
stat = next(c for c in cues if c["type"] == "pop" and c["atSecond"] == 0.5)
assert stat["kit_kind"] == "number" and stat["target"] == 0.5
sfx_plan.assign_files([cues], legacy, seed="s")
assert stat["file"] == "data-number-land" and stat["atSecond"] == round(0.5 - cat["data-number-land"]["sync_at"], 3)
plain = sfx_plan.plan_sfx(1, {"sfx": [{"type": "pop", "at_word": "ye"}]}, words, {"pop"})
assert plain and "kit_kind" not in plain[0], "an ordinary emphasis pop is not a number sound"

# 7. fail-open: no kit, a broken catalog, or a missing MP3 means the old files, never an error
real = sfxkit.DIR
try:
    for broken in ("empty", "garbage", "nofile"):
        d = pathlib.Path(tempfile.mkdtemp())
        if broken == "garbage":
            (d / "catalog.json").write_text("{not json", encoding="utf-8")
        if broken == "nofile":
            (d / "catalog.json").write_text(json.dumps({"sounds": {"pop-small-in": cat["pop-small-in"]}}), encoding="utf-8")     # listed, but its MP3 is absent
        sfxkit.DIR = d; sfxkit.reset()
        assert sfxkit.load() == {} and sfxkit.entries("pop") == [], broken
        cues = [cue("pop", 1.0, 0.7), cue("whoosh", 2.0)]
        sfx_plan.assign_files([cues], legacy, seed="x")
        assert [c["file"] for c in cues] == ["pop_1", "whoosh_" + cues[1]["file"][-1]] and all(c["src"].endswith(".mp3") for c in cues), broken
finally:
    sfxkit.DIR = real; sfxkit.reset()
assert len(sfxkit.load()) == 320

# 8. staging: kit sounds are copied from the kit, the old ones from assets/sfx
tmp = pathlib.Path(tempfile.mkdtemp()); manifest.WORK = tmp
manifest._stage_sfx({"whoosh-fast-soft", "pop_1"})
assert (tmp / "sfx" / "whoosh-fast-soft.mp3").stat().st_size == (real / "whoosh-fast-soft.mp3").stat().st_size and (tmp / "sfx" / "pop_1.mp3").exists()
shutil.rmtree(tmp)
print("video sfx kit test passed: 320 sounds, kinds mapped, no voice-masking sound, sync_at timing, kit levels, variety caps, stat number sound, fail-open, staging")
