"""Offline: export polish. CRF 18, one grade for all clips (and it really runs in ffmpeg), voice EQ/compressor runs, cover + grid preview exported."""
import os, pathlib, subprocess, sys, tempfile
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "video-agent"))
os.chdir(REPO / "video-agent")
from agent import grade, render
from unittest import mock

T = pathlib.Path(tempfile.mkdtemp())
ff = lambda *a: subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, a)], capture_output=True, text=True)

# 1. render encodes at CRF 18 (24 made small text blocky), overridable
seen = []
with mock.patch.object(render, "run", lambda cmd, cwd=None: seen.append(list(map(str, cmd)))), mock.patch.object(render, "TEMPLATE", T):
    os.environ.pop("REEL_CRF", None)
    render.render({"scenes": []}, T / "o.mp4")
    assert seen[-1][seen[-1].index("--crf") + 1] == "18"
    os.environ["REEL_CRF"] = "16"; render.render({"scenes": []}, T / "o.mp4")
    assert seen[-1][seen[-1].index("--crf") + 1] == "16"; del os.environ["REEL_CRF"]

# 2. the grade chain is valid ffmpeg and pulls a dark clip and a bright clip closer together
def mean(p):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"], capture_output=True, text=True).stderr
    v = [float(x.split("=")[1]) for x in o.splitlines() if "YAVG" in x]
    return sum(v) / len(v)
raw = {}
for name, src in (("dark", "testsrc2=s=270x480:r=30:d=2,eq=brightness=-0.25"), ("bright", "testsrc2=s=270x480:r=30:d=2,eq=brightness=0.2")):
    a, g = T / f"{name}.mp4", T / f"{name}_g.mp4"
    assert ff("-f", "lavfi", "-i", src, "-pix_fmt", "yuv420p", a).returncode == 0
    p = ff("-i", a, "-vf", grade.grade_filter() + "format=yuv420p", g); assert p.returncode == 0, p.stderr
    raw[name] = (mean(a), mean(g))
assert abs(raw["dark"][1] - raw["bright"][1]) < abs(raw["dark"][0] - raw["bright"][0]), raw
os.environ["GRADE"] = "0"; assert grade.grade_filter() == ""; del os.environ["GRADE"]

# 3. voice polish filter runs and keeps the length
w = T / "v.wav"; ff("-f", "lavfi", "-i", "sine=f=300:d=2", w)
p = ff("-i", w, "-af", grade.voice_filter(), T / "v2.wav"); assert p.returncode == 0, p.stderr
os.environ["VOICE_POLISH"] = "0"; assert grade.voice_filter() == ""; del os.environ["VOICE_POLISH"]

# 4. cover + grid preview: 1080x1920 and 1080x1440
vid = T / "final.mp4"; ff("-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=3", "-pix_fmt", "yuv420p", vid)
full, grid = grade.cover(vid)
size = lambda p: subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip()
assert size(full) == "1080,1920" and size(grid) == "1080,1440", (size(full), size(grid))
assert grade.cover(T / "missing.mp4") is None
print("export quality ok")
