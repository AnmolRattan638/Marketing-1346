"""Offline test: the strict hybrid editor (video-agent/agent/hybrid.py): rules, audit, style profile, notes, and a real ffmpeg render with fades."""
import os, pathlib, random, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent / "video-agent"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
for k in ("EDITS_DIR", "EDITS_DRIVE_URL", "PEXELS_API_KEY", "PIXABAY_API_KEY"):
    os.environ.pop(k, None)
from agent import edits, hybrid, style
from agent.common import load_config, media_duration

cfg = load_config()
hs = hybrid.settings(cfg)
prof = dict(style.DEFAULT)
avail = {"raw": True, "stock": True, "photo": True}

# 1. allocation follows every rule over many seeds and reel lengths
for seed in range(60):
    rng = random.Random(seed)
    durs = [d for sc in range(rng.randint(3, 7)) for d in hybrid.split_scene(rng.uniform(2.5, 6.5), prof, rng)]
    types = hybrid.allocate(durs, avail, hs, prof, rng)
    shots = [{"type": t, "seconds": d} for t, d in zip(types, durs)]
    assert hybrid.audit(shots, avail, hs, prof) == [], (seed, hybrid.audit(shots, avail, hs, prof), types)

# 2. audit catches each violation
mk = lambda *pairs: [{"type": t, "seconds": s} for t, s in pairs]
assert any("raw footage" in b for b in hybrid.audit(mk(("raw", 1), ("stock", 2), ("photo", 2), ("stock", 2), ("raw", 1)), avail, hs, prof))
assert any("stock video" in b for b in hybrid.audit(mk(("raw", 4), ("stock", 6)), avail, hs, prof))
assert any("in a row" in b for b in hybrid.audit(mk(("raw", 2), ("raw", 2), ("raw", 2), ("photo", 2), ("stock", 1)), avail, hs, prof))
assert any("first shot" in b for b in hybrid.audit(mk(("stock", 2), ("raw", 4), ("photo", 2)), avail, hs, prof))
assert any("photo shots" in b for b in hybrid.audit(mk(("raw", 3), ("stock", 2), ("raw", 3)), avail, hs, prof))
assert any("range" in b for b in hybrid.audit(mk(("raw", 9), ("stock", 2), ("photo", 2), ("raw", 3)), avail, hs, prof))
# a source that does not exist is not demanded
assert hybrid.audit(mk(("stock", 2), ("photo", 3), ("stock", 1), ("photo", 2)), {"raw": False, "stock": True, "photo": True}, hs, prof) == []

# 3. strict mode refuses to run without the edits folder or raw clips
try:
    hybrid.Editor(cfg, False); raise SystemExit("must refuse without edits")
except hybrid.HybridError as e:
    assert "EDITS_DRIVE_URL" in str(e)
tmp = pathlib.Path(tempfile.mkdtemp()); (tmp / "raw").mkdir(); (tmp / "hero").mkdir()
os.environ["EDITS_DIR"] = str(tmp)
try:
    hybrid.Editor(cfg, False); raise SystemExit("must refuse an empty raw folder")
except hybrid.HybridError as e:
    assert "no raw video" in str(e)

# 4. the folder reader: tags from file names and notes.txt; hero notes override the measured style
import subprocess
def ff(*a): subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)
ff("-f", "lavfi", "-i", "testsrc=s=1920x1080:r=30:d=5", "-pix_fmt", "yuv420p", str(tmp / "raw" / "Website_Demo_final.mp4"))
ff("-f", "lavfi", "-i", "testsrc2=s=1080x1920:d=1", "-frames:v", "1", str(tmp / "raw" / "IMG_2031.jpg"))
(tmp / "raw" / "notes.txt").write_text("IMG_2031.jpg: owner at desk with laptop\n")
(tmp / "hero" / "notes.txt").write_text("shot_seconds: 1.6-3.0\ntransitions: cut 60, fade 40\npunch_in: 50%\nfirst_shot: raw\n")
lib = edits.raw_library(tmp)
assert [v["name"] for v in lib["videos"]] == ["Website_Demo_final.mp4"] and lib["videos"][0]["tags"] == {"website", "demo"}
assert lib["images"][0]["tags"] >= {"owner", "desk", "laptop"}
p = style.profile([], edits.read_notes(tmp / "hero"))
assert (p["shot_min"], p["shot_max"]) == (1.6, 3.0) and p["transitions"] == {"cut": 60.0, "fade": 40.0} and p["punch_in"] == 50
# measured rhythm: a reel with hard cuts every 2 seconds is measured as about 2 s shots
ff("-f", "lavfi", "-i", "testsrc=s=540x960:r=30:d=2", "-f", "lavfi", "-i", "mandelbrot=s=540x960:r=30", "-filter_complex",
   "[1:v]trim=duration=2,setpts=PTS-STARTPTS[b];[0:v][b][0:v]concat=n=3:v=1:a=0,format=yuv420p", "-t", "6", str(tmp / "hero" / "a.mp4"))
lens = style.shot_lengths(tmp / "hero" / "a.mp4")
assert 2 <= len(lens) <= 3 and all(1.5 < x < 2.6 for x in lens), lens

# 5. a real render with fades: scene length stays exact
cfg["hybrid"]["min_raw_share"] = 0.4
ed = hybrid.Editor(cfg, False)
assert ed.avail["raw"] and ed.prof["shot_min"] == 1.6
ed.avail["stock"] = ed.avail["photo"] = True
ed._fill_orig = ed._fill
def synth_fill(s, words, scene, base, i):
    if s["type"] == "raw":
        return ed._fill_orig(s, words, scene, base, i)
    dest = base.with_suffix(".jpg" if s["type"] == "photo" else ".mp4")
    ed._synthetic(s["type"], dest, i); s.update(src=dest, credit={"source": "synthetic"})
ed._fill = synth_fill
ed.prof["transitions"] = {"cut": 20, "fade": 80}
out = pathlib.Path(tempfile.mkdtemp())
ed.prepare([("s1", {"footage_query": "website demo", "narration": "x"}, 6.0), ("s2", {"footage_query": "owner desk", "narration": "y"}, 5.0)], out)
assert ed.shots[0]["type"] == "raw" and ed.violations == []
assert any(s["transition_in"] == "fade" for s in ed.shots)
for sid, want in (("s1", 6.0), ("s2", 5.0)):
    r = ed.render_scene(sid, out)
    assert abs(media_duration(out / f"{sid}.mp4") - want) < 0.25, (sid, r["seconds"])
print("video hybrid test passed: rules over 60 seeds, audit, strict refusals, folder reader, style notes, measured rhythm, fade render")
