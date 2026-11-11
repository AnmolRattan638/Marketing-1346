"""Your `edits` folder: Hero (reference reels that teach the style) and Raw (your own clips and photos).

Where it lives: a Google Drive folder shared by link (secret EDITS_DRIVE_URL), downloaded each run with gdown, or a local folder (EDITS_DIR) for tests.
Layout inside it (names are case-insensitive):
    hero/   finished reels you like, plus an optional notes.txt with explicit style rules
    raw/    your recordings, demos, screen captures and photos; an optional notes.txt of lines  `filename: what it shows`
"""
from __future__ import annotations

import os
import re
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
    try:
        import gdown        # the Python API: the command-line flags differ between gdown versions, the function arguments below exist in 5.x and 6.x
        got = gdown.download_folder(url=url, output=str(CACHE), quiet=True, resume=True)
    except Exception as e:
        raise RuntimeError("could not download the edits folder from Drive (is it shared as 'Anyone with the link'? a very large folder can also fail): " + str(e)[-300:]) from e
    if not got:
        raise RuntimeError("the Drive folder came back empty or could not be read (share it as 'Anyone with the link' and check the EDITS_DRIVE_URL secret)")
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


SERVICES = ["website", "chatbot", "animated_ads", "lead_gen", "reel_scripts", "seo_blogs"]


def detect_service(topic: str, cfg: dict) -> tuple[str, str]:
    """-> (service id or 'general', topic text without any [tag]). Never asks the model. An explicit `[chatbot] topic` tag wins; otherwise the
    service whose keywords match the topic most (whole words); a tie or no match is 'general', which only uses raw/general clips."""
    m = re.match(r"\s*\[([a-z_]+)\]\s*(.*)", topic, flags=re.S)
    if m:
        tag, rest = m.group(1), m.group(2)
        if tag in SERVICES or tag == "general":
            return tag, rest
        raise ValueError(f"unknown service tag [{tag}] in the topic; use one of: {', '.join(SERVICES)}, general")
    text = " " + re.sub(r"[^a-z0-9]+", " ", topic.lower()) + " "
    score = {sid: sum(1 for k in kws if f" {k} " in text) for sid, kws in (cfg.get("services") or {}).items()}
    best = sorted(score.items(), key=lambda kv: -kv[1])
    if best and best[0][1] > 0 and (len(best) == 1 or best[0][1] > best[1][1]):
        return best[0][0], topic
    return "general", topic


def tags_of(name: str) -> set[str]:
    words = re.split(r"[^a-z0-9]+", Path(name).stem.lower())
    return {w for w in words if len(w) > 2 and w not in STOP and not w.isdigit()}


def read_notes(folder: Path | None) -> list[str]:
    f = next((x for x in folder.iterdir() if x.is_file() and x.name.lower() == "notes.txt"), None) if folder else None
    return [l.strip() for l in f.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip() and not l.startswith("#")] if f else []


def service_of(rel: Path, desc: str) -> str:
    """Which service a raw file represents, from explicit labels only (never guessed from what is on screen):
    1. its subfolder: raw/chatbot/x.mp4 (raw/general/ for clips that fit every service)
    2. a notes.txt line  `x.mp4: service=chatbot, me demoing the bot`
    3. a file name that starts with the service id: chatbot_demo.mp4
    Anything else is 'unassigned' and is never used."""
    if len(rel.parts) > 1 and (rel.parts[0].lower() in SERVICES or rel.parts[0].lower() == "general"):
        return rel.parts[0].lower()
    m = re.search(r"service\s*=\s*([a-z_]+)", desc.lower())
    if m and (m.group(1) in SERVICES or m.group(1) == "general"):
        return m.group(1)
    for sid in SERVICES:
        if re.match(rf"{sid}[^a-z]", rel.name.lower() + "."):
            return sid
    return "unassigned"


def raw_library(root: Path | None) -> dict:
    """{'videos': [...], 'images': [...]} from edits/raw; each item has path, name, tags, service. notes.txt lines are `filename: service=chatbot, what it shows`."""
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
        d = desc.get(f.name.lower(), "")
        tags = tags_of(f.name) | tags_of(re.sub(r"service\s*=\s*[a-z_]+", "", d) + ".x")
        lib["videos" if ext in VIDEO_EXT else "images"].append({"path": f, "name": f.name, "tags": tags, "service": service_of(f.relative_to(raw), d)})
    return lib


def hero_reels(root: Path | None) -> tuple[list[Path], list[str]]:
    hero = _sub(root, "hero") if root else None
    if not hero:
        return [], []
    return [f for f in sorted(hero.rglob("*")) if f.is_file() and f.suffix.lower() in VIDEO_EXT], read_notes(hero)
