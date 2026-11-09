"""Your `edits` folder: Hero (reference reels that teach the style) and Raw (your own clips and photos).

Where it lives: a Google Drive folder shared by link (secret EDITS_DRIVE_URL), downloaded each run with gdown, or a local folder (EDITS_DIR) for tests.
Layout inside it (names are case-insensitive):
    hero/   finished reels you like, plus an optional notes.txt with explicit style rules
    raw/    your recordings, demos, screen captures and photos; an optional notes.txt of lines  `filename: what it shows`
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .common import ROOT, log

CACHE = ROOT / "edits_cache"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "your", "you", "my", "i", "it", "this", "that", "at", "by",
        "clip", "video", "img", "image", "final", "copy", "new", "raw", "screen", "recording", "screenrecording"}


def configured() -> bool:
    return bool(os.environ.get("EDITS_DIR") or os.environ.get("EDITS_DRIVE_URL"))


def sync() -> Path | None:
    """Return the local edits folder, downloading it from Drive when needed. None when nothing is configured; raises when Drive fails."""
    local = os.environ.get("EDITS_DIR")
    if local:
        return Path(local)
    url = (os.environ.get("EDITS_DRIVE_URL") or "").strip()
    if not url:
        return None
    CACHE.mkdir(exist_ok=True)
    log("syncing the edits folder from Google Drive")
    p = subprocess.run(["gdown", "--folder", url, "-O", str(CACHE), "--remaining-ok", "--quiet"], text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("could not download the edits folder from Drive (is it shared as 'Anyone with the link'? more than 50 files per folder also fails): " + (p.stderr or p.stdout)[-300:])
    # gdown puts the folder's own name under the cache; use whichever directory holds hero/ or raw/
    for d in [CACHE, *[x for x in CACHE.iterdir() if x.is_dir()]]:
        names = {x.name.lower() for x in d.iterdir() if x.is_dir()}
        if names & {"hero", "raw"}:
            return d
    raise RuntimeError("the Drive folder has no 'hero' or 'raw' subfolder")


def _sub(root: Path, name: str) -> Path | None:
    for x in root.iterdir():
        if x.is_dir() and x.name.lower() == name:
            return x
    return None


def tags_of(name: str) -> set[str]:
    words = re.split(r"[^a-z0-9]+", Path(name).stem.lower())
    return {w for w in words if len(w) > 2 and w not in STOP and not w.isdigit()}


def read_notes(folder: Path | None) -> list[str]:
    f = next((x for x in folder.iterdir() if x.is_file() and x.name.lower() == "notes.txt"), None) if folder else None
    return [l.strip() for l in f.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip() and not l.startswith("#")] if f else []


def raw_library(root: Path | None) -> dict:
    """{'videos': [{path, name, tags}], 'images': [...]} from edits/raw. Tags come from the file name plus any `filename: description` line in notes.txt."""
    lib = {"videos": [], "images": []}
    raw = _sub(root, "raw") if root else None
    if not raw:
        return lib
    desc = {}
    for line in read_notes(raw):
        if ":" in line:
            k, v = line.split(":", 1)
            desc[k.strip().lower()] = v
    for f in sorted(raw.rglob("*")):
        ext = f.suffix.lower()
        if not f.is_file() or f.name.startswith(".") or ext not in VIDEO_EXT | IMAGE_EXT:
            continue
        tags = tags_of(f.name) | tags_of(desc.get(f.name.lower(), "") + ".x")
        lib["videos" if ext in VIDEO_EXT else "images"].append({"path": f, "name": f.name, "tags": tags})
    return lib


def hero_reels(root: Path | None) -> tuple[list[Path], list[str]]:
    hero = _sub(root, "hero") if root else None
    if not hero:
        return [], []
    return [f for f in sorted(hero.rglob("*")) if f.is_file() and f.suffix.lower() in VIDEO_EXT], read_notes(hero)
