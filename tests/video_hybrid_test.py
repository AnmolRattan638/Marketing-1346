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
assert hs["min_photo_shots"] == 0, "no photo is required by default"
assert hs["min_raw_shots"] == 1 and "min_raw_share" not in hs, "the 40% share rule is replaced by at least 1 raw shot"
hs_photo = {**hs, "min_photo_shots": 1}
prof = dict(style.DEFAULT)
avail = {"raw": True, "raw_clips": 3, "stock": True, "photo": True}

# 1. allocation follows every rule over many seeds and reel lengths
for seed in range(60):
    rng = random.Random(seed)
    durs = [d for sc in range(rng.randint(3, 7)) for d in hybrid.split_scene(rng.uniform(2.5, 6.5), prof, rng)]
    types = hybrid.allocate(durs, avail, hs, prof, rng)
    shots = [{"type": t, "seconds": d} for t, d in zip(types, durs)]
    assert hybrid.audit(shots, avail, hs, prof) == [], (seed, hybrid.audit(shots, avail, hs, prof), types)

# 2. audit catches each violation
mk = lambda *pairs: [{"type": t, "seconds": s} for t, s in pairs]
assert any("raw shot" in b for b in hybrid.audit(mk(("stock", 2), ("photo", 2), ("stock", 2)), avail, hs, prof))
assert not any("raw shot" in b for b in hybrid.audit(mk(("raw", 1.8), ("stock", 2), ("photo", 2), ("stock", 2)), avail, hs, prof)), "ONE raw shot is enough"
one_file = lambda *fs: [{"type": "raw", "seconds": 2, "credit": {"file": f}} if f else {"type": "stock", "seconds": 2, "credit": {}} for f in fs]
assert any("at least 2 of your clips" in b for b in hybrid.audit(one_file("a.mp4", None, "a.mp4"), avail, hs, prof))
assert not any("clips" in b for b in hybrid.audit(one_file("a.mp4", None, "b.mp4"), avail, hs, prof))
assert not any("clips" in b for b in hybrid.audit(one_file("a.mp4", None, "a.mp4"), {**avail, "raw_clips": 1}, hs, prof)), "one clip available: one clip is fine"
# even a single-shot raw minimum of 3 is forced by allocate() when the reel is short
for seed in range(30):
    rng = random.Random(seed); durs = [2.0] * 6
    ty = hybrid.allocate(durs, avail, {**hs, "min_raw_shots": 4}, prof, rng)
    assert ty.count("raw") >= 4, (seed, ty)
assert any("stock video" in b for b in hybrid.audit(mk(("raw", 4), ("stock", 6)), avail, hs, prof))
assert any("in a row" in b for b in hybrid.audit(mk(("raw", 2), ("raw", 2), ("raw", 2), ("photo", 2), ("stock", 1)), avail, hs, prof))
assert any("first shot" in b for b in hybrid.audit(mk(("stock", 2), ("raw", 4), ("photo", 2)), avail, hs, prof))
assert hybrid.audit(mk(("raw", 3), ("stock", 2), ("raw", 3)), avail, hs, prof) == [], "no photo needed by default"
assert any("photo shots" in b for b in hybrid.audit(mk(("raw", 3), ("stock", 2), ("raw", 3)), avail, hs_photo, prof))
assert any("range" in b for b in hybrid.audit(mk(("raw", 9), ("stock", 2), ("photo", 2), ("raw", 3)), avail, hs, prof))
# a source that does not exist is not demanded
assert hybrid.audit(mk(("stock", 2), ("photo", 3), ("stock", 1), ("photo", 2)), {"raw": False, "stock": True, "photo": True}, hs, prof) == []

# 2b. the Drive download goes through gdown's Python API (the CLI flag --remaining-ok broke in CI) and fails with a clear message
import types
fake = types.ModuleType("gdown"); calls = {}
def fake_dl(url=None, output=None, quiet=False, resume=False, **kw):
    calls.update(url=url, output=output, kw=kw)
    root = pathlib.Path(output) / "edits"; (root / "raw" / "website").mkdir(parents=True, exist_ok=True); (root / "hero").mkdir(exist_ok=True)
    return [str(root / "raw" / "website" / "a.mp4")]
fake.download_folder = fake_dl
sys.modules["gdown"] = fake
os.environ["EDITS_DRIVE_URL"] = "https://drive.google.com/drive/folders/abc"
edits.CACHE = pathlib.Path(tempfile.mkdtemp())
synced = edits.sync()
assert synced.name == "edits" and calls["url"].endswith("abc") and "remaining_ok" not in calls["kw"]
fake.download_folder = lambda **kw: []
try:
    edits.sync(); raise SystemExit("an empty download must fail")
except RuntimeError as e:
    assert "empty or could not be read" in str(e)
def boom(**kw): raise ValueError("Cannot retrieve the public link")
fake.download_folder = boom
try:
    edits.sync(); raise SystemExit("a failed download must fail")
except RuntimeError as e:
    assert "Anyone with the link" in str(e)
del sys.modules["gdown"]; os.environ.pop("EDITS_DRIVE_URL")

# 3. strict mode refuses to run without the edits folder or raw clips
try:
    hybrid.Editor(cfg, False); raise SystemExit("must refuse without edits")
except hybrid.HybridError as e:
    assert "EDITS_DRIVE_URL" in str(e)
tmp = pathlib.Path(tempfile.mkdtemp()); (tmp / "raw").mkdir(); (tmp / "hero").mkdir()
os.environ["EDITS_DIR"] = str(tmp)
try:
    hybrid.Editor(cfg, False, "website"); raise SystemExit("must refuse an empty raw folder")
except hybrid.HybridError as e:
    assert "no raw video clip is labelled for 'website'" in str(e)

# 4. the folder reader: tags from file names and notes.txt; hero notes override the measured style
import subprocess
def ff(*a): subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)
for sub in ("website", "chatbot", "general"):
    (tmp / "raw" / sub).mkdir()
mkv = lambda path: ff("-f", "lavfi", "-i", "testsrc=s=1920x1080:r=30:d=5", "-pix_fmt", "yuv420p", str(path))
mkv(tmp / "raw" / "website" / "Website_Demo_final.mp4")
mkv(tmp / "raw" / "chatbot" / "bot_demo.mp4")                    # another service: must never appear in a website reel
mkv(tmp / "raw" / "chatbot_phone.mp4")                            # labelled by file-name prefix
mkv(tmp / "raw" / "mystery.mp4")                                  # no label: never used
mkv(tmp / "raw" / "labelled_by_note.mp4")
ff("-f", "lavfi", "-i", "testsrc2=s=1080x1920:d=1", "-frames:v", "1", str(tmp / "raw" / "general" / "IMG_2031.jpg"))
(tmp / "raw" / "notes.txt").write_text("IMG_2031.jpg: owner at desk with laptop\nlabelled_by_note.mp4: service=website, a site walkthrough\n")
(tmp / "hero" / "notes.txt").write_text("shot_seconds: 1.6-3.0\ntransitions: cut 60, fade 40\npunch_in: 50%\nfirst_shot: raw\n")
lib = edits.raw_library(tmp)
svc = {v["name"]: v["service"] for v in lib["videos"]}
assert svc == {"Website_Demo_final.mp4": "website", "bot_demo.mp4": "chatbot", "chatbot_phone.mp4": "chatbot", "mystery.mp4": "unassigned", "labelled_by_note.mp4": "website"}, svc
assert [v["tags"] for v in lib["videos"] if v["name"] == "Website_Demo_final.mp4"] == [{"website", "demo"}]
assert lib["images"][0]["tags"] >= {"owner", "desk", "laptop"} and lib["images"][0]["service"] == "general"
# the service of a topic: explicit tag, whole-word keywords, or general; never guessed by the model
assert edits.detect_service("[chatbot] Why replies matter", cfg) == ("chatbot", "Why replies matter")
assert edits.detect_service("Why every local shop needs a website", cfg)[0] == "website"
assert edits.detect_service("How a Google Business profile and a website work together", cfg)[0] == "website"
assert edits.detect_service("Three small habits", cfg)[0] == "general"
assert edits.detect_service("website chatbot", cfg)[0] == "general", "a tie is general, not a guess"
assert edits.detect_service("a website and web design, not a chatbot", cfg)[0] == "website"
try:
    edits.detect_service("[webste] x", cfg); raise SystemExit("unknown tag must fail")
except ValueError:
    pass
p = style.profile([], edits.read_notes(tmp / "hero"))
assert (p["shot_min"], p["shot_max"]) == (1.6, 3.0) and p["transitions"] == {"cut": 60.0, "fade": 40.0} and p["punch_in"] == 50
# measured rhythm: a reel with hard cuts every 2 seconds is measured as about 2 s shots
ff("-f", "lavfi", "-i", "testsrc=s=540x960:r=30:d=2", "-f", "lavfi", "-i", "mandelbrot=s=540x960:r=30", "-filter_complex",
   "[1:v]trim=duration=2,setpts=PTS-STARTPTS[b];[0:v][b][0:v]concat=n=3:v=1:a=0,format=yuv420p", "-t", "6", str(tmp / "hero" / "a.mp4"))
lens = style.shot_lengths(tmp / "hero" / "a.mp4")
assert 2 <= len(lens) <= 3 and all(1.5 < x < 2.6 for x in lens), lens

# 5. a real render with fades: scene length stays exact
cfg["hybrid"]["min_raw_shots"] = 1
ed = hybrid.Editor(cfg, False, "website")
assert {v["name"] for v in ed.lib["videos"]} == {"Website_Demo_final.mp4", "labelled_by_note.mp4"}, "only website clips (no chatbot, no unlabelled)"
assert ed.unassigned == ["mystery.mp4"] and ed.others == 2
ed_chat = hybrid.Editor(cfg, False, "chatbot")
assert {v["name"] for v in ed_chat.lib["videos"]} == {"bot_demo.mp4", "chatbot_phone.mp4"}
assert ed_chat.library_summary() and "website" not in ed_chat.library_summary()
try:
    hybrid.Editor(cfg, False, "lead_gen"); raise SystemExit("no clips for lead_gen: must refuse")
except hybrid.HybridError as e:
    assert "lead_gen" in str(e) and "raw/lead_gen" in str(e)
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
assert all(s["credit"].get("service") in (None, "website", "general") for s in ed.shots), "a foreign-service clip was used"
assert any(s["transition_in"] == "fade" for s in ed.shots)
for sid, want in (("s1", 6.0), ("s2", 5.0)):
    r = ed.render_scene(sid, out)
    assert abs(media_duration(out / f"{sid}.mp4") - want) < 0.25, (sid, r["seconds"], [(s["type"], round(s["seconds"], 2), s["transition_in"]) for s in ed.shots if s["sid"] == sid])
# 5b. raw shots are the BEST PART of several clips, reused with different parts, never the whole file
raw_shots = [x for x in ed.shots if x["type"] == "raw"]
assert raw_shots and all(x.get("start") is not None and "start" in x["credit"] for x in raw_shots), "every raw shot records which part it uses"
assert len({x["credit"]["file"] for x in raw_shots}) >= min(2, len(raw_shots)), "two or more clips are used"
for name in {x["credit"]["file"] for x in raw_shots}:        # parts of one clip never overlap by more than the tolerance
    spans = sorted((x["start"], x["start"] + x["seconds"]) for x in raw_shots if x["credit"]["file"] == name)
    assert all(b[0] >= a[1] - 0.6 for a, b in zip(spans, spans[1:])), (name, spans)

from agent import clipscore
clip = pathlib.Path(tempfile.mkdtemp()) / "demo.mp4"      # 3 s of a black, still frame, then 4 s of detailed, moving picture
ff("-f", "lavfi", "-i", "color=c=black:s=640x360:r=30:d=3", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=4", "-filter_complex",
   "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p", str(clip))
dur = media_duration(clip)
t1 = clipscore.best_start(clip, 2.0, dur, [])
assert t1 >= 2.4, f"the best 2 s is in the detailed half, not the black intro: {t1}"
t2 = clipscore.best_start(clip, 2.0, dur, [(t1, t1 + 2.0)])
assert abs(t2 - t1) >= 1.7, f"a second shot from the same clip takes a different part: {t1} then {t2}"
assert clipscore.best_start(clip, dur + 1, dur, []) == 0.0, "a clip shorter than the shot is used whole"
bad_clip = pathlib.Path(tempfile.mkdtemp()) / "broken.mp4"; bad_clip.write_bytes(b"not a video")
assert clipscore.best_start(bad_clip, 2.0, 8.0, []) is None, "an unreadable clip falls back to a random slice"

# a cut inside a window is avoided: 3 s of testsrc2, a hard cut to mandelbrot, 3 s more; the best 2 s window must not straddle the cut at 3 s
cut = pathlib.Path(tempfile.mkdtemp()) / "cut.mp4"
ff("-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=3", "-f", "lavfi", "-i", "mandelbrot=s=640x360:r=30", "-filter_complex",
   "[1:v]trim=duration=3,setpts=PTS-STARTPTS[b];[0:v][b]concat=n=2:v=1:a=0,format=yuv420p", str(cut))
tc = clipscore.best_start(cut, 2.0, media_duration(cut), [])
assert not (tc < 2.9 < tc + 2.0), f"the chosen window straddles the hard cut: {tc}"
print("best-part test passed: strongest moment, different parts on reuse, cuts avoided, unreadable clips fall back")

print("video hybrid test passed: rules over 60 seeds, audit, strict refusals, folder reader, style notes, measured rhythm, fade render")

# 6. the planner survives a retired Groq model (404 -> next model) and a model that rejects JSON mode (400 -> retry without it)
from unittest import mock
from agent import plan as planmod
class R:
    def __init__(self, code, body=None): self.status_code, self._b, self.text = code, body or {}, "x"
    def json(self): return self._b
    def raise_for_status(self): assert self.status_code < 400
seen = []
def post(url, headers=None, json=None, timeout=None):
    seen.append((json["model"], "response_format" in json, json.get("reasoning_effort")))
    if json["model"] == "openai/gpt-oss-120b": return R(404)
    if json["model"] == "llama-3.3-70b-versatile" and "response_format" in json: return R(400)
    return R(200, {"choices": [{"message": {"content": "{}"}}]})
os.environ["GROQ_API_KEY"] = "k"; os.environ.pop("GROQ_MODEL", None)
with mock.patch.object(planmod.requests, "post", post):
    assert planmod._call_groq([{"role": "user", "content": "x"}], cfg) == "{}"
assert seen == [("openai/gpt-oss-120b", True, "low"), ("llama-3.3-70b-versatile", True, None), ("llama-3.3-70b-versatile", False, None)], seen
assert cfg["planner"]["model"] == "openai/gpt-oss-120b"
print("groq model fallback test passed")
