"""Find the best part of a short raw clip (5-10 s), so a shot uses the strongest moment instead of a random slice or the whole file.

How a moment is scored (cheap, no model): the clip is sampled at 4 frames/s at 96x96 grey and every sample gets
  - sharpness  (variance of a Laplacian: in focus, detailed frames beat blurry or empty ones)
  - motion     (mean change from the previous sample: something is happening, saturating so a shaky clip does not win)
  - exposure   (not nearly black, not blown out)
A window of the shot's length is scored as the mean of its samples, minus a heavy penalty when a hard cut sits inside it (a shot must not contain
a jump) and a small one when it touches the very first or last 0.25 s of the file (fades, auto-exposure settling).
Windows already used by earlier shots of the same clip are skipped, so one clip can be reused for several shots with DIFFERENT parts.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np

SAMPLE_FPS = 4
SIZE = 96
CUT_DIFF = 30.0         # mean grey-level change between two samples that means a hard cut or a whip
MAX_OVERLAP = 0.25      # seconds of overlap with an earlier shot from the same clip that is still accepted

_cache: dict[str, np.ndarray | None] = {}


def _samples(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """-> (score per sample, change-from-previous per sample), or None when the clip cannot be read."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf", f"fps={SAMPLE_FPS},scale={SIZE}:{SIZE},format=gray", "-f", "rawvideo", "-"],
                       capture_output=True)
    n = len(p.stdout) // (SIZE * SIZE)
    if p.returncode or n < 2:
        return None
    f = np.frombuffer(p.stdout[: n * SIZE * SIZE], np.uint8).reshape(n, SIZE, SIZE).astype(np.float32)
    lap = 4 * f[:, 1:-1, 1:-1] - f[:, :-2, 1:-1] - f[:, 2:, 1:-1] - f[:, 1:-1, :-2] - f[:, 1:-1, 2:]
    sharp = np.clip(np.log1p(lap.reshape(n, -1).var(axis=1)) / 6.0, 0, 1)
    diff = np.abs(np.diff(f, axis=0)).reshape(n - 1, -1).mean(axis=1)
    diff = np.concatenate([diff[:1], diff])
    motion = np.clip(diff / 6.0, 0, 1)
    lum = f.reshape(n, -1).mean(axis=1)
    expo = np.where((lum >= 45) & (lum <= 210), 1.0, 0.3)
    return 0.45 * sharp + 0.35 * motion + 0.20 * expo, diff


def _analyse(path: Path):
    key = str(path)
    if key not in _cache:
        _cache[key] = _samples(path)
    return _cache[key]


def window_score(path: Path, start: float, length: float) -> float | None:
    a = _analyse(path)
    if a is None:
        return None
    score, diff = a
    n = len(score)
    i0 = min(n - 1, max(0, int(round(start * SAMPLE_FPS))))
    i1 = min(n, max(i0 + 1, i0 + int(math.ceil(length * SAMPLE_FPS))))
    s = float(score[i0:i1].mean())
    if (diff[i0 + 1:i1] > CUT_DIFF).any():
        s -= 1.0
    if start < 0.25 or start + length > n / SAMPLE_FPS - 0.25:
        s -= 0.04
    return s


def best_start(path: Path, length: float, duration: float, taken: list[tuple[float, float]], step: float = 0.25) -> float | None:
    """Start (seconds) of the best window of `length` that does not reuse a part already in `taken`. None if the clip cannot be analysed."""
    if duration <= length:
        return 0.0
    best: tuple[float, float, float] | None = None       # (-overlap bucket, score, start)
    t = 0.0
    while t <= duration - length + 1e-6:
        sc = window_score(path, t, length)
        if sc is None:
            return None
        overlap = sum(max(0.0, min(t + length, b) - max(t, a)) for a, b in taken)
        # windows with acceptable overlap always beat windows that reuse footage; among equals the higher score wins
        key = (0 if overlap <= MAX_OVERLAP else -overlap, sc, t)
        if best is None or key[:2] > best[:2]:
            best = (key[0], key[1], t)
        t += step
    return best[2] if best else 0.0
