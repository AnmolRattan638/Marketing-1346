"""Footage: Pexels search and download, hero clips, and a placeholder if all else fails."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import requests

from .common import ROOT, log, media_duration, run

PEXELS_URL = "https://api.pexels.com/videos/search"


def _search(query: str, key: str) -> list[dict]:
    r = requests.get(
        PEXELS_URL,
        headers={"Authorization": key},
        params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 15},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("videos", [])


def _pick_file(video: dict) -> dict | None:
    files = [
        f for f in video.get("video_files", [])
        if f.get("file_type") == "video/mp4" and (f.get("height") or 0) > (f.get("width") or 0)
    ]
    files.sort(key=lambda f: abs(f["width"] - 1080))
    return files[0] if files else None


def _download(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)


def _placeholder(dest: Path, seconds: float = 8.0) -> None:
    """A moving dark-blue clip, so a run never fails just because footage is missing."""
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         f"color=c=0x1b2a41:s=1080x1920:r=30:d={seconds}",
         "-vf", "noise=alls=10:allf=t,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
         dest])


def fetch_clip(scene: dict, sid: str, out_dir: Path, used_ids: set, offline: bool) -> dict:
    """Return {"path": "assets/run/footage/s1.mp4", "seconds": float, "credit": {...}}."""
    dest = out_dir / f"{sid}.mp4"
    rel = f"assets/run/footage/{sid}.mp4"
    credit: dict = {"scene": sid, "source": "placeholder"}

    hero = scene.get("hero_clip")
    if hero and (ROOT / "assets" / "hero" / hero).exists():
        shutil.copy(ROOT / "assets" / "hero" / hero, dest)
        credit = {"scene": sid, "source": "hero_clip", "file": hero}
    elif not offline and os.environ.get("PEXELS_API_KEY"):
        key = os.environ["PEXELS_API_KEY"]
        q = scene["footage_query"]
        for query in (q, " ".join(q.split()[:2])):
            try:
                for v in _search(query, key):
                    f = _pick_file(v)
                    if not f or v["id"] in used_ids or v.get("duration", 0) < 3:
                        continue
                    _download(f["link"], dest)
                    used_ids.add(v["id"])
                    credit = {"scene": sid, "source": "pexels", "query": query,
                              "page": v.get("url"), "videographer": (v.get("user") or {}).get("name")}
                    break
            except Exception as e:  # network or API trouble: try the next query, then fall back
                log(f"pexels search failed for '{query}': {e}")
            if dest.exists():
                break

    if not dest.exists():
        log(f"{sid}: no footage found, using placeholder")
        _placeholder(dest)
    return {"path": rel, "seconds": round(media_duration(dest), 2), "credit": credit}
