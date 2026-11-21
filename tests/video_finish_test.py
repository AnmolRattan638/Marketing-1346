"""Offline test: the final loudness step brings a reel to about -14 LUFS, never damages it, and never raises."""
import hashlib, os, pathlib, subprocess, sys, tempfile
from unittest import mock
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "video-agent"))
os.chdir(REPO / "video-agent")
os.environ.pop("LOUDNESS_NORMALIZE", None)
from agent import finish

T = pathlib.Path(tempfile.mkdtemp())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def make(name, audio):
    out = T / name
    a = ["-f", "lavfi", "-i", audio, "-c:a", "aac", "-ar", "48000"] if audio else ["-an"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=320x568:r=30:d=3", *a, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "3", str(out)], check=True)
    return out


def info(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,codec_type,nb_frames", "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True).stdout
    return sorted(out.split())


# 1. too quiet: raised to the target, true peak under the ceiling, video stream untouched, same length
quiet = make("quiet.mp4", "sine=f=440:d=3,volume=0.02")
before = finish.measure(quiet); video_before = [x for x in info(quiet) if x.startswith("h264")]
assert before and before["input_i"] < -25
assert finish.normalize(quiet) is True
after = finish.measure(quiet)
assert abs(after["input_i"] - -14.0) <= 1.0 and after["input_tp"] <= -1.0, after
assert [x for x in info(quiet) if x.startswith("h264")] == video_before, "the video stream is copied, not re-encoded"
assert abs(finish.media_duration(quiet) - 3.0) < 0.15 and not list(T.glob("*.norm.mp4"))
# 2. already on target: left alone byte for byte
h = sha(quiet)
assert finish.normalize(quiet) is False and sha(quiet) == h
# 3. too hot: brought down
hot = make("hot.mp4", "sine=f=440:d=3,volume=5")
assert finish.measure(hot)["input_i"] > -12 and finish.normalize(hot) is True and abs(finish.measure(hot)["input_i"] - -14.0) <= 1.0
# 4. nothing to normalise: no audio, silence, a missing file; the originals are untouched and nothing raises
noaudio, silent = make("noaudio.mp4", None), make("silent.mp4", "anullsrc=r=48000:cl=mono")
for f in (noaudio, silent):
    h = sha(f)
    assert finish.normalize(f) is False and sha(f) == h, f.name
assert finish.normalize(T / "does-not-exist.mp4") is False
# 5. a failing ffmpeg or a broken result leaves the original as rendered and cleans up
q2 = make("q2.mp4", "sine=f=440:d=3,volume=0.02"); h = sha(q2)
real = finish._ffmpeg
def failing(args):
    if "-c:v" in [str(a) for a in args]:
        return subprocess.CompletedProcess(args, 1, "", "boom")
    return real(args)
with mock.patch.object(finish, "_ffmpeg", failing):
    assert finish.normalize(q2) is False and sha(q2) == h and not list(T.glob("*.norm.mp4"))
def truncated(args):
    p = real(args)
    if "-c:v" in [str(a) for a in args]:
        pathlib.Path(str(args[-1])).write_bytes(b"not a video")
    return p
with mock.patch.object(finish, "_ffmpeg", truncated):
    assert finish.normalize(q2) is False and sha(q2) == h and not list(T.glob("*.norm.mp4")), "a result that does not check out is thrown away"
with mock.patch.object(finish, "_ffmpeg", side_effect=OSError("ffmpeg missing")):
    assert finish.normalize(q2) is False and sha(q2) == h
# 6. switches
os.environ["LOUDNESS_NORMALIZE"] = "0"
assert finish.normalize(q2) is False and sha(q2) == h
os.environ.pop("LOUDNESS_NORMALIZE")
os.environ["LOUDNESS_LUFS"] = "-16"
assert finish.normalize(q2) is True and abs(finish.measure(q2)["input_i"] - -16.0) <= 1.2
os.environ["LOUDNESS_LUFS"] = "garbage"
assert finish._target() == (-14.0, -1.5)
print("video finish test passed: -14 LUFS reached, video stream copied, on-target/no-audio/silent untouched, failures leave the original, switches work")
