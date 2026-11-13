"""Footage: your own hero clips, then stock video (Pexels -> Pixabay -> Coverr) and stock photos (Pixabay -> Pexels -> Unsplash), then a placeholder if all else fails."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import requests

from .stockquery import relevant, tech_queries
from .common import ROOT, log, media_duration, run

PEXELS_URL = "https://api.pexels.com/videos/search"
PIXABAY_URL = "https://pixabay.com/api/videos/"
COVERR_URL = "https://api.coverr.co/videos"
UNSPLASH_URL = "https://api.unsplash.com/search/photos"


_CFG: dict = {}      # set by run.py from config.json (stock.keywords / stock.anchors)


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


def _pixabay_search(query: str, key: str) -> list[dict]:
    r = requests.get(PIXABAY_URL, params={"key": key, "q": query, "per_page": 20, "safesearch": "true", "video_type": "film"}, timeout=30)
    r.raise_for_status()
    return r.json().get("hits", [])


def _pixabay_file(hit: dict) -> dict | None:
    """Prefer the 1080p 'large' file, then 'medium'; Pixabay has no portrait filter, so the clip is cropped to 9:16 after download."""
    vids = hit.get("videos") or {}
    for tier in ("large", "medium", "small"):
        f = vids.get(tier) or {}
        if f.get("url") and (f.get("width") or 0) >= 640:
            return f
    return None


def _coverr_search(query: str, key: str) -> list[dict]:
    """Coverr: key goes in the x-api-key header; urls=true is needed to get the mp4 links. Vertical clips first, landscape ones are centre-cropped later."""
    r = requests.get(COVERR_URL, headers={"x-api-key": key}, params={"query": query, "page_size": 20, "urls": "true"}, timeout=30)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    return sorted(hits, key=lambda h: not h.get("is_vertical"))


def _unsplash_search(query: str, key: str) -> list[dict]:
    r = requests.get(UNSPLASH_URL, headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"},
                     params={"query": query, "orientation": "portrait", "per_page": 20, "content_filter": "high"}, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


def _to_portrait(src: Path, dest: Path) -> None:
    """Fill a 1080x1920 frame from any footage (centre crop), 30 fps, no audio."""
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-an",
         "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", dest])


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


def _stock_video(query_text: str, dest: Path, used_ids: set) -> dict | None:
    """One portrait-ish stock video for the query (Pexels, then Pixabay, then Coverr). -> credit dict, or None when nothing was found."""
    queries = tech_queries(query_text, _CFG)      # always AI / technology (agent/stockquery.py)
    if os.environ.get("PEXELS_API_KEY"):
        key = os.environ["PEXELS_API_KEY"]
        for query in queries:
            try:
                for v in _search(query, key):
                    if not relevant(v.get("url", "")):
                        continue
                    f = _pick_file(v)
                    if not f or f"pexels:{v['id']}" in used_ids or v.get("duration", 0) < 3:
                        continue
                    _download(f["link"], dest)
                    used_ids.add(f"pexels:{v['id']}")
                    return {"source": "pexels", "query": query, "page": v.get("url"), "videographer": (v.get("user") or {}).get("name")}
            except Exception as e:  # network or API trouble: try the next query, then fall back
                log(f"pexels search failed for '{query}': {e}")
    if os.environ.get("PIXABAY_API_KEY"):
        key = os.environ["PIXABAY_API_KEY"]
        for query in queries:
            try:
                for hit in _pixabay_search(query, key):
                    if not relevant(hit.get("tags", "")):
                        continue
                    f = _pixabay_file(hit)
                    pid = f"pixabay:{hit.get('id')}"
                    if not f or pid in used_ids or (hit.get("duration") or 0) < 3:
                        continue
                    raw = dest.with_suffix(".src.mp4")
                    _download(f["url"], raw)
                    try:
                        _to_portrait(raw, dest)
                    finally:
                        raw.unlink(missing_ok=True)
                    used_ids.add(pid)
                    return {"source": "pixabay", "query": query, "page": hit.get("pageURL"), "videographer": hit.get("user")}
            except Exception as e:
                log(f"pixabay search failed for '{query}': {e}")
    if os.environ.get("COVERR_API_KEY"):
        key = os.environ["COVERR_API_KEY"]
        for query in queries:
            try:
                for v in _coverr_search(query, key):
                    if not relevant(v.get("title", ""), " ".join(v.get("tags") or []) if isinstance(v.get("tags"), list) else str(v.get("tags") or "")):
                        continue
                    url = (v.get("urls") or {}).get("mp4") or (v.get("urls") or {}).get("mp4_download")
                    cid = f"coverr:{v.get('id')}"
                    if not url or cid in used_ids or (v.get("duration") or 0) < 3:
                        continue
                    raw = dest.with_suffix(".src.mp4")
                    _download(url, raw)
                    try:
                        _to_portrait(raw, dest)
                    finally:
                        raw.unlink(missing_ok=True)
                    used_ids.add(cid)
                    return {"source": "coverr", "query": query, "page": f"https://coverr.co/videos/{v.get('id')}", "videographer": v.get("title")}
            except Exception as e:
                log(f"coverr search failed for '{query}': {e}")
    return None


def _stock_photo(query_text: str, dest: Path, used_ids: set) -> dict | None:
    """One portrait photo for the query (Pixabay, then Pexels, then Unsplash). -> credit dict, or None."""
    queries = tech_queries(query_text, _CFG)      # always AI / technology (agent/stockquery.py)
    if os.environ.get("PIXABAY_API_KEY"):
        for query in queries:
            try:
                r = requests.get("https://pixabay.com/api/", params={"key": os.environ["PIXABAY_API_KEY"], "q": query, "image_type": "photo",
                                 "orientation": "vertical", "per_page": 20, "safesearch": "true", "min_height": 1400}, timeout=30)
                r.raise_for_status()
                for hit in r.json().get("hits", []):
                    if not relevant(hit.get("tags", "")):
                        continue
                    pid = f"pixabay-photo:{hit.get('id')}"
                    url = hit.get("largeImageURL") or hit.get("webformatURL")
                    if pid in used_ids or not url:
                        continue
                    _download(url, dest)
                    used_ids.add(pid)
                    return {"source": "pixabay-photo", "query": query, "page": hit.get("pageURL"), "videographer": hit.get("user")}
            except Exception as e:
                log(f"pixabay photo search failed for '{query}': {e}")
    if os.environ.get("PEXELS_API_KEY"):
        for query in queries:
            try:
                r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": os.environ["PEXELS_API_KEY"]},
                                 params={"query": query, "orientation": "portrait", "per_page": 15}, timeout=30)
                r.raise_for_status()
                for ph in r.json().get("photos", []):
                    if not relevant(ph.get("alt", ""), ph.get("url", "")):
                        continue
                    pid = f"pexels-photo:{ph.get('id')}"
                    url = (ph.get("src") or {}).get("large2x")
                    if pid in used_ids or not url:
                        continue
                    _download(url, dest)
                    used_ids.add(pid)
                    return {"source": "pexels-photo", "query": query, "page": ph.get("url"), "videographer": ph.get("photographer")}
            except Exception as e:
                log(f"pexels photo search failed for '{query}': {e}")
    if os.environ.get("UNSPLASH_ACCESS_KEY"):
        key = os.environ["UNSPLASH_ACCESS_KEY"]
        for query in queries:
            try:
                for ph in _unsplash_search(query, key):
                    if not relevant(ph.get("alt_description", ""), ph.get("description", ""), " ".join(t.get("title", "") for t in ph.get("tags") or [])):
                        continue
                    pid = f"unsplash:{ph.get('id')}"
                    raw_url = (ph.get("urls") or {}).get("raw")
                    if pid in used_ids or not raw_url:
                        continue
                    _download(raw_url + ("&" if "?" in raw_url else "?") + "w=1080&h=1920&fit=crop&q=80", dest)
                    used_ids.add(pid)
                    try:   # Unsplash API rule: report a download to their tracking endpoint (best effort)
                        requests.get((ph.get("links") or {}).get("download_location", ""), headers={"Authorization": f"Client-ID {key}"}, timeout=15)
                    except Exception:
                        pass
                    return {"source": "unsplash", "query": query, "page": (ph.get("links") or {}).get("html"), "videographer": (ph.get("user") or {}).get("name")}
            except Exception as e:
                log(f"unsplash search failed for '{query}': {e}")
    return None


def stock_available(kind: str) -> bool:
    keys = ("PEXELS_API_KEY", "PIXABAY_API_KEY", "UNSPLASH_ACCESS_KEY" if kind == "photo" else "COVERR_API_KEY")
    return any(os.environ.get(k) for k in keys)


def fetch_clip(scene: dict, sid: str, out_dir: Path, used_ids: set, offline: bool) -> dict:
    """Old one-clip-per-scene path (kept for hybrid=off). Return {"path": ..., "seconds": float, "credit": {...}}."""
    dest = out_dir / f"{sid}.mp4"
    rel = f"assets/run/footage/{sid}.mp4"
    credit: dict = {"scene": sid, "source": "placeholder"}
    hero = scene.get("hero_clip")
    if hero and (ROOT / "assets" / "hero" / hero).exists():
        shutil.copy(ROOT / "assets" / "hero" / hero, dest)
        credit = {"scene": sid, "source": "hero_clip", "file": hero}
    elif not offline:
        c = _stock_video(scene["footage_query"], dest, used_ids)
        if c:
            credit = {"scene": sid, **c}
    if not dest.exists():
        log(f"{sid}: no footage found, using placeholder")
        _placeholder(dest)
    return {"path": rel, "seconds": round(media_duration(dest), 2), "credit": credit}
