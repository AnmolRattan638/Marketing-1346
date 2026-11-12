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


def _stage_logo(cfg: dict):
    """Your logo as a small bug on every frame (config.json -> logo). None when disabled or the file is missing."""
    lg = cfg.get("logo") or {}
    src = ROOT / "assets" / "brand" / "logo.png"
    if not lg.get("enabled") or not src.exists():
        return None
    (WORK / "brand").mkdir(parents=True, exist_ok=True)
    shutil.copy(src, WORK / "brand" / "logo.png")
    return {"src": "assets/run/brand/logo.png", **{k: lg[k] for k in ("position", "size", "opacity", "marginX", "marginY") if k in lg}}


def available_sfx() -> set:
    return {p.stem for p in (ROOT / "assets" / "sfx").glob("*.mp3")}


def _outro(cfg: dict):
    """The logo for the closing animation: needs look.outro_logo and your logo file; None = no outro."""
    if not (cfg.get("look") or {}).get("outro_logo", True):
        return None
    lg = _stage_logo({**cfg, "logo": {**(cfg.get("logo") or {}), "enabled": True}})
    return lg


def build_manifest(plan: dict, built: list[dict], cfg: dict, look: dict | None = None) -> dict:
    v = cfg["video"]
    fps = v["fps"]
    spans = [b["narration_seconds"] + v["tail_seconds"] for b in built]      # progress bar: how far through the narrated part each scene is
    prog = [sum(spans[:k]) / (sum(spans) or 1) for k in range(len(spans) + 1)]
    outro = _outro(cfg)
    scenes = []
    used_sfx: set = set()
    for i, b in enumerate(built):
        # Round up to whole frames so Remotion's total length equals the sum of scenes.
        frames = math.ceil((b["narration_seconds"] + v["tail_seconds"]) * fps)
        props = {"words": b["words"]}
        if b.get("graphic"):                                # motion-graphic scene: no footage, the layout draws the picture
            props.update(b["graphic"])
            props.pop("sfx", None)
            props["progress"] = [round(prog[i], 4), round(prog[i + 1], 4)]
            props["showProgress"] = bool((cfg.get("look") or {}).get("progress_bar", True))
        else:
            props.update({"clip": b["clip"]["path"], "clipSeconds": b["clip"]["seconds"]})
        beats = b.get("beats") or []
        props["emphasis"] = [w for w, _ in beats]          # words the captions colour and the picture pulses on, same moments as the pop/riser
        props["pulses"] = [round(t, 3) for _, t in beats]
        fx = b.get("fx") or []
        props["fx"] = fx                                   # stat / glitch / title / lower_third / shake, each at a spoken word
        props["transitionIn"] = b.get("transition", "settle")
        if look:
            props["captionStyle"] = look["caption"]
        props["pulses"] += [f["atSecond"] for f in fx if f["type"] in ("stat", "glitch", "title")]     # the picture hits with the graphic
        props["pulses"].sort()
        if (cfg.get("fx") or {}).get("grain"):
            props["grain"] = cfg["fx"]["grain"]
        if i == len(built) - 1 and not outro:
            props["fadeOutFrames"] = 10                    # the only fade to black: the end of the video
        if i == len(built) - 1 and plan.get("cta", {}).get("text") and not outro:
            props["overlayText"] = plan["cta"]["text"]
        used_sfx |= {c["type"] for c in b["sfx"]}
        scenes.append({
            "id": b["id"],
            "component": "sequences/GraphicScene" if b.get("graphic") else "sequences/FootageScene",
            "duration": round(frames / fps, 4),
            "narration": b["narration"],
            "sfx": [{k: c[k] for k in ("src", "atSecond", "volume")} for c in b["sfx"]],
            "props": props,
        })
    if outro:                                              # always end on your logo animation, never on whatever stock clip was left
        secs = float((cfg.get("look") or {}).get("outro_seconds", 1.8))
        scenes.append({
            "id": "outro", "component": "sequences/GraphicScene", "duration": round(math.ceil(secs * fps) / fps, 4), "narration": None,
            "sfx": [{"src": "assets/run/sfx/pop.mp3", "atSecond": 0.35, "volume": 0.5}] if "pop" in available_sfx() else [],
            "props": {"layout": "logo", "words": [], "logo": outro["src"], "cta": plan.get("cta", {}).get("text", ""), "fadeOutFrames": 12,
                      "times": {"heading": 0.1, "mock": 0, "items": [], "chips": 0}},
        })
        used_sfx.add("pop")
    _stage_sfx(used_sfx)
    total = sum(s["duration"] for s in scenes)
    if total > 60:
        log(f"warning: video is {total:.0f}s, longer than a typical short")
    return {
        "video": {"id": "daily", "width": v["width"], "height": v["height"], "fps": fps,
                  "title": plan["title"]},
        "audio": {"music": _stage_music(cfg)},
        "brand": {"logo": _stage_logo(cfg)},
        "look": {"theme": (look or {}).get("theme", "ink"), "caption": (look or {}).get("caption", "pill")},
        "scenes": scenes,
    }
