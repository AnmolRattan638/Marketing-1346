"""Export polish shared by every route: one colour grade for all footage, a light voice EQ/compressor, and the cover frame.

* GRADE: stock and raw clips come from different cameras, so side by side they differ in exposure and colour. Every clip goes through the same chain:
  `normalize` stretches its own black/white points (smoothed over time, so no flicker), then a small shared contrast/saturation lift. Off with GRADE=0.
* VOICE: the narration gets a high-pass (rumble/plosive thump), a little presence, and a gentle 2.5:1 compressor so quiet words are not lost under music. Off with VOICE_POLISH=0.
* cover(): a still of the finished reel (the hook is on screen at about 1.2 s) so a cover is not picked by hand at posting time. Instagram's profile grid shows only the
  centre 3:4 of the 9:16 frame, so a second, centre-cropped preview is exported too.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .common import log


def _on(name: str) -> bool:
    return os.getenv(name, "1").strip().lower() not in ("0", "false", "off", "no")


def grade_filter() -> str:
    """ffmpeg video-filter fragment to put just before format=yuv420p ('' when switched off)."""
    return "normalize=blackpt=black:whitept=white:smoothing=24,eq=contrast=1.04:saturation=1.06," if _on("GRADE") else ""


def voice_filter() -> str:
    """ffmpeg audio-filter fragment (no leading/trailing comma) or '' when switched off."""
    return "highpass=f=80,equalizer=f=3200:t=q:w=1.0:g=1.5,acompressor=threshold=-21dB:ratio=2.5:attack=8:release=140:makeup=2" if _on("VOICE_POLISH") else ""


def cover(video: Path, at: float = 1.2) -> tuple[Path, Path] | None:
    """(full 1080x1920 cover, centre-cropped 3:4 grid preview) next to the video, or None. Never raises."""
    full, grid = video.with_name("cover.jpg"), video.with_name("cover_grid.jpg")
    try:
        for out, vf in ((full, "scale=1080:1920"), (grid, "scale=1080:1920,crop=1080:1440")):
            p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1", "-vf", vf, "-q:v", "2", str(out)],
                               capture_output=True, text=True, timeout=120)
            if p.returncode != 0 or not out.exists() or out.stat().st_size < 1000:
                log("cover: could not export a cover frame")
                return None
        return full, grid
    except Exception as e:
        log(f"cover: skipped ({str(e)[:100]})")
        return None
