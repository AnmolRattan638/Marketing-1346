import pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import avatar
cfg = {"avatar": {"enabled": True, "max_scenes": 2}}
assert avatar.enabled(cfg) and not avatar.enabled({"avatar": {"enabled": False}}) and not avatar.enabled({})
g = [{"layout": "hook"}, {"layout": "title"}, {"layout": "ba"}, {"layout": "punch"}, {"layout": "title"}, {"layout": "title"}, {"layout": "logo"}]
idx = avatar.choose(g, cfg)
assert len(idx) == 2 and all(0 < i < len(g) - 1 and g[i]["layout"] in avatar.PLAIN for i in idx), idx    # never the hook or the last scene, never a picture scene
assert avatar.choose([{"layout": "hook"}, {"layout": "step"}, {"layout": "logo"}], cfg) == []
# voice loudness: a loud half then silence gives high energy then ~0
tmp = pathlib.Path(tempfile.mkdtemp()); wav = tmp / "v.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=1", "-af", "volume=0.8,apad=pad_dur=1", "-t", "2", str(wav)], check=True)
e = avatar.energy(str(wav), 30, 60)
assert len(e) == 60 and max(e[:25]) > 0.8 and max(e[40:]) < 0.1, (e[:5], e[40:45])
assert avatar.energy(None, 30, 10) == [0.0] * 10
# the four poses exist and are the same size
from PIL import Image
sizes = {Image.open(p).size for p in (pathlib.Path(__file__).resolve().parent.parent / "video-agent" / "assets" / "avatar").glob("pose*.jpg")}
assert len(sizes) == 1, sizes
# permanent presenter: one block for the whole reel, hidden only in the hook, the big avatar scenes and the logo end
wav2 = tmp / "w2.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=6", str(wav2)], check=True)
built = [{"narration": str(wav2), "graphic": {"layout": "hook"}}, {"narration": str(wav2), "graphic": {"layout": "step"}}, {"narration": str(wav2), "graphic": {"layout": "avatar"}}, {"narration": str(wav2), "graphic": {"layout": "title"}}]
frames = [90, 180, 120, 90]
pc = avatar.presenter(built, frames, {"avatar": {"enabled": True}}, 30, True)
assert len(pc["energy"]) == sum(frames) and len(pc["src"]) == 4
assert pc["hide"][:2] == [[0, 90], [270, 390]], pc["hide"]               # the hook and the big avatar scene
assert pc["hide"][-1][0] == sum(frames)                                   # hidden for the logo end
shown = [c for c in pc["cuts"] if not any(a <= c["f"] < b for a, b in pc["hide"])]
assert len(shown) >= 3 and len({c["i"] for c in pc["cuts"]}) >= 3         # the pose keeps changing
assert all(a["i"] != b["i"] for a, b in zip(pc["cuts"], pc["cuts"][1:]))
assert avatar.presenter(built, frames, {"avatar": {"enabled": True, "presenter": False}}, 30, True) is None
print("avatar test passed")
