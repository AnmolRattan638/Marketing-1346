"""Build the Remotion manifest.json (claude-remotion-skill format) from the built scenes."""
from __future__ import annotations

import math
import shutil
from datetime import date

from .common import ROOT, WORK, log


def _stage_sfx(types: set) -> None:
    (WORK / "sfx").mkdir(parents=True, exist_ok=True)
    for t in types:
        shutil.copy(ROOT / "assets" / "sfx" / f"{t}.mp3", WORK / "sfx" / f"{t}.mp3")


def _stage_music(cfg: dict):
    tracks = sorted((ROOT / "assets" / "music").glob("*.mp3"))
    if not tracks:
        log("no tracks in assets/music, video will have no music bed")
        return None
    track = tracks[date.today().toordinal() % len(tracks)]
    (WORK / "music").mkdir(parents=True, exist_ok=True)
    shutil.copy(track, WORK / "music" / "bed.mp3")
    m = cfg["music"]
    return {"src": "assets/run/music/bed.mp3", "baseVolume": m["base_volume"], "duckTo": m["duck_to"]}


def available_sfx() -> set:
    return {p.stem for p in (ROOT / "assets" / "sfx").glob("*.mp3")}


def build_manifest(plan: dict, built: list[dict], cfg: dict) -> dict:
    v = cfg["video"]
    fps = v["fps"]
    scenes = []
    used_sfx: set = set()
    for i, b in enumerate(built):
        # Round up to whole frames so Remotion's total length equals the sum of scenes.
        frames = math.ceil((b["narration_seconds"] + v["tail_seconds"]) * fps)
        props = {
            "clip": b["clip"]["path"],
            "clipSeconds": b["clip"]["seconds"],
            "words": b["words"],
        }
        if i == len(built) - 1 and plan.get("cta", {}).get("text"):
            props["overlayText"] = plan["cta"]["text"]
        used_sfx |= {c["type"] for c in b["sfx"]}
        scenes.append({
            "id": b["id"],
            "component": "sequences/FootageScene",
            "duration": round(frames / fps, 4),
            "narration": b["narration"],
            "sfx": [{k: c[k] for k in ("src", "atSecond", "volume")} for c in b["sfx"]],
            "props": props,
        })
    _stage_sfx(used_sfx)
    total = sum(s["duration"] for s in scenes)
    if total > 60:
        log(f"warning: video is {total:.0f}s, longer than a typical short")
    return {
        "video": {"id": "daily", "width": v["width"], "height": v["height"], "fps": fps,
                  "title": plan["title"]},
        "audio": {"music": _stage_music(cfg)},
        "scenes": scenes,
    }
