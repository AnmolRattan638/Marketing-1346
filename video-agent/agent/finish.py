"""Final audio finishing for the rendered reel: loudness.

From the sound-design and style-instagram-reels skills: short social video is delivered at about -14 LUFS integrated with true peak at or below -1 dBTP
(a quieter video sounds weak next to its neighbours in the feed; a hotter one gets turned down by the platform). Remotion renders the mix at whatever level
voice + music + effects happen to sum to, so the file is measured and, only when it is off target, brought to -14 LUFS with ffmpeg's two-pass loudnorm.

Safe by construction: the video stream is copied untouched, the result is accepted only if it is still a valid video of the same length, and ANY failure
(no audio, a silent file, ffmpeg missing, a bad measurement) leaves the original file exactly as rendered. normalize() never raises.
Switch off with LOUDNESS_NORMALIZE=0. Targets by env: LOUDNESS_LUFS (default -14), LOUDNESS_TP (default -1.5).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from .common import log, media_duration

TOLERANCE = 1.0          # LU: closer than this to the target is left alone (no needless re-encode of the audio)


def _target() -> tuple[float, float]:
    try:
        return float(os.getenv("LOUDNESS_LUFS") or -14.0), float(os.getenv("LOUDNESS_TP") or -1.5)
    except ValueError:
        return -14.0, -1.5


def _ffmpeg(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *map(str, args)], capture_output=True, text=True, timeout=600)


def measure(path: Path) -> dict | None:
    """Integrated loudness, true peak and loudness range of the first audio stream, or None (no audio, silent, unreadable)."""
    i, tp = _target()
    p = _ffmpeg(["-i", path, "-map", "0:a:0", "-af", f"loudnorm=I={i}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr or "", re.S)
    if p.returncode != 0 or not m:
        return None
    d = json.loads(m.group(0))
    vals = {k: float(d[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    return vals if all(v == v and abs(v) != float("inf") for v in vals.values()) and vals["input_i"] > -60 else None


def normalize(path: Path) -> bool:
    """Bring the audio of `path` to the target loudness in place. True if the file was changed. Never raises."""
    tmp = path.with_suffix(".norm.mp4")
    try:
        if os.getenv("LOUDNESS_NORMALIZE", "1").strip().lower() in ("0", "false", "off", "no"):
            return False
        i, tp = _target()
        m = measure(path)
        if m is None:
            log("loudness: no measurable audio, left as rendered")
            return False
        log(f"loudness: {m['input_i']:.1f} LUFS, true peak {m['input_tp']:.1f} dBTP (target {i:.0f} LUFS, peak <= {tp:.1f})")
        if abs(m["input_i"] - i) <= TOLERANCE and m["input_tp"] <= tp + 0.5:
            return False
        flt = (f"loudnorm=I={i}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
               f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
        p = _ffmpeg(["-y", "-i", path, "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-af", flt, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", tmp])
        if p.returncode != 0 or not tmp.exists():
            log("loudness: normalising failed, left as rendered")
            return False
        if abs(media_duration(tmp) - media_duration(path)) > 0.15 or measure(tmp) is None:
            log("loudness: the normalised file did not check out, left as rendered")
            return False
        os.replace(tmp, path)
        after = measure(path)
        log(f"loudness: now {after['input_i']:.1f} LUFS, true peak {after['input_tp']:.1f} dBTP" if after else "loudness: normalised")
        return True
    except Exception as e:
        log(f"loudness: skipped ({str(e)[:100]})")
        return False
    finally:
        try:
            tmp.unlink()
        except (FileNotFoundError, OSError):
            pass
