"""Smart caption placement: find the emptiest part of the picture for the captions, moment by moment, so they never sit on a face, a sign or on-screen text.

For a footage scene the finished picture is sampled (SAMPLE_FPS frames/s, 9:16). Candidate positions (centre y on the 1920 px frame) are scored per sample by
  busy    mean edge strength inside the caption strip (faces, text, signs, busy textures are all high; sky, walls, tarmac, blur are low)
  motion  mean frame-to-frame change in the strip (a moving person or hand is not covered)
  prior   a small preference for the lower third, where viewers expect captions
A Viterbi pass picks the cheapest path over time with a cost for every move, so captions stay put unless a clearly emptier spot opens up
and the moves are few. Result: [{"from": s, "to": s, "y": px}] in scene seconds; the player eases between positions.
Motion-graphic scenes do not need this: their layouts keep the lower third free by construction.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from .common import log

H, W = 1920, 1080
SAMPLE_FPS = 4
GW, GH = 72, 128                       # analysis grid (9:16)
STRIP = 300                            # px, height of the area a caption phrase can cover
X0, X1 = 70, 1010                      # px, the caption's horizontal span
DEFAULT_Y = 1400                       # where the bottom captions sit when nothing says otherwise
CANDIDATES = {330: 0.12, 600: 0.10, 870: 0.08, 1140: 0.05, 1400: 0.0, 1560: 0.03}      # centre y -> preference cost
MOVE_COST = 0.9                        # leaving a position must buy at least this much emptiness (a second or two of a clearly emptier spot)
MIN_GAIN = 0.12                        # and the default spot is kept unless it is at least this busy


def _frames(path: Path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf",
                        f"fps={SAMPLE_FPS},scale=-2:{GH}:force_original_aspect_ratio=increase,crop={GW}:{GH},format=gray", "-f", "rawvideo", "-"],
                       capture_output=True)
    n = len(p.stdout) // (GW * GH)
    if p.returncode or n < 1:
        return None
    return np.frombuffer(p.stdout[: n * GW * GH], np.uint8).reshape(n, GH, GW).astype(np.float32)


def band_costs(f: np.ndarray) -> np.ndarray:
    """(samples, candidates) cost of putting the captions in each candidate strip at each sample."""
    n = len(f)
    gy = np.abs(np.diff(f, axis=1, prepend=f[:, :1]))
    gx = np.abs(np.diff(f, axis=2, prepend=f[:, :, :1]))
    edge = np.minimum(1.0, (gx + gy) / 2 / 40.0)                         # per pixel, 0..1
    mot = np.zeros_like(f)
    if n > 1:
        mot[1:] = np.abs(np.diff(f, axis=0))
        mot[0] = mot[1]
    mot = np.minimum(1.0, mot / 40.0)
    sx0, sx1 = int(X0 / W * GW), int(X1 / W * GW)
    out = np.zeros((n, len(CANDIDATES)))
    for k, (cy, prior) in enumerate(CANDIDATES.items()):
        r0, r1 = int((cy - STRIP / 2) / H * GH), int((cy + STRIP / 2) / H * GH)
        e = edge[:, r0:r1, sx0:sx1].mean(axis=(1, 2))
        m = mot[:, r0:r1, sx0:sx1].mean(axis=(1, 2))
        out[:, k] = np.minimum(1.0, e * 2.0) + 0.6 * m + prior
    return out


def plan_zones(path: Path, seconds: float) -> list[dict] | None:
    """-> caption positions over time for one footage scene, or None (keep the default bottom position) when the picture cannot be read."""
    f = _frames(path)
    if f is None:
        return None
    cost = band_costs(f)
    n, k = cost.shape
    ys = list(CANDIDATES)
    start = ys.index(DEFAULT_Y)
    # Viterbi: stay, or move to another position for MOVE_COST
    best = np.full((n, k), np.inf)
    back = np.zeros((n, k), int)
    best[0] = cost[0] + MOVE_COST * (np.arange(k) != start)
    for i in range(1, n):
        for j in range(k):
            stay = best[i - 1, j]
            move = best[i - 1].min() + MOVE_COST
            if stay <= move:
                best[i, j], back[i, j] = stay + cost[i, j], j
            else:
                best[i, j], back[i, j] = move + cost[i, j], int(best[i - 1].argmin())
    path_idx = [int(best[-1].argmin())]
    for i in range(n - 1, 0, -1):
        path_idx.append(int(back[i, path_idx[-1]]))
    path_idx.reverse()
    if cost[:, start].mean() < MIN_GAIN + CANDIDATES[DEFAULT_Y] and all(cost[i, start] <= cost[i].min() + MIN_GAIN for i in range(n)):
        return []                                                       # the default spot is already clear throughout
    zones: list[dict] = []
    for i, j in enumerate(path_idx):
        t = i / SAMPLE_FPS
        if zones and zones[-1]["y"] == ys[j]:
            continue
        zones.append({"from": round(t, 2), "y": ys[j]})
    zones = [z for i, z in enumerate(zones) if i == 0 or (zones[i + 1]["from"] if i + 1 < len(zones) else seconds) - z["from"] >= 0.6]      # no blink-and-gone positions
    for a, b in zip(zones, zones[1:] + [{"from": round(seconds, 2)}]):
        a["to"] = b["from"]
    zones[0]["from"] = 0.0
    return zones


def zones_for(path: Path, seconds: float) -> list[dict]:
    try:
        z = plan_zones(path, seconds)
    except Exception as e:                       # analysis must never stop a reel: fall back to the bottom position
        log(f"caption zones: {e}, using the bottom position")
        return []
    z = z or []
    if z:
        log(f"caption zones {Path(path).stem}: " + ", ".join(f"{a['from']:.1f}s@{a['y']}" for a in z))
    return z
