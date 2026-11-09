"""Learn the editing style from your Hero reels: measure the cut rhythm, then apply the explicit rules in hero/notes.txt on top.

Measured automatically (ffmpeg scene detection): how long a shot lasts, how many cuts per 10 seconds, reel length.
NOT measured (be honest): which transition or effect a reel uses. That comes from notes.txt, and only from effects the renderer can do:
cut, fade (cross-dissolve), punch_in (quick zoom on the cut), push_in (slow zoom), ken_burns (photos).

notes.txt lines, all optional:   shot_seconds: 1.6-3.0   |   transitions: cut 80, fade 20   |   punch_in: 30   |   first_shot: raw
"""
from __future__ import annotations

import re
import statistics
import subprocess
from pathlib import Path

from .common import log, media_duration

DEFAULT = {"shot_min": 1.4, "shot_max": 3.6, "shot_median": 2.3, "transitions": {"cut": 85, "fade": 15}, "punch_in": 30, "first_shot": "raw", "reels_measured": 0}


def cut_times(path: Path, threshold: float = 0.32) -> list[float]:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"],
                       text=True, capture_output=True)
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", p.stderr)]


def shot_lengths(path: Path) -> list[float]:
    total = media_duration(path)
    cuts = [0.0] + cut_times(path) + [total]
    return [b - a for a, b in zip(cuts, cuts[1:]) if b - a >= 0.4]


def _parse_notes(lines: list[str]) -> dict:
    out = {}
    for line in lines:
        if ":" not in line:
            continue
        k, v = (x.strip().lower() for x in line.split(":", 1))
        if k == "shot_seconds" and re.fullmatch(r"[0-9.]+\s*-\s*[0-9.]+", v):
            a, b = (float(x) for x in re.split(r"\s*-\s*", v))
            out["shot_min"], out["shot_max"] = min(a, b), max(a, b)
        elif k == "transitions":
            t = {m[0]: float(m[1]) for m in re.findall(r"(cut|fade)\s*=?\s*([0-9.]+)", v)}
            if t:
                out["transitions"] = t
        elif k == "punch_in" and re.fullmatch(r"[0-9.]+%?", v):
            out["punch_in"] = float(v.rstrip("%"))
        elif k == "first_shot" and v in ("raw", "stock", "photo", "any"):
            out["first_shot"] = v
    return out


def profile(reels: list[Path], notes: list[str]) -> dict:
    prof = dict(DEFAULT)
    lengths: list[float] = []
    for r in reels[:12]:
        try:
            lengths += shot_lengths(r)
            prof["reels_measured"] += 1
        except Exception as e:
            log(f"could not measure {r.name}: {e}")
    if len(lengths) >= 8:
        lengths.sort()
        prof["shot_median"] = round(statistics.median(lengths), 2)
        prof["shot_min"] = round(max(1.0, lengths[len(lengths) // 10]), 2)
        prof["shot_max"] = round(min(5.0, lengths[(len(lengths) * 9) // 10]), 2)
        prof["measured_shots"] = len(lengths)
    prof.update(_parse_notes(notes))
    prof["shot_min"] = min(prof["shot_min"], prof["shot_max"])
    prof["shot_median"] = min(max(prof["shot_median"], prof["shot_min"]), prof["shot_max"])
    return prof
