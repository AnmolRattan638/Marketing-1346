"""Animation templates (the Locomotion pack, imported by scripts/import_locomotion.py) used as motion-graphic scenes.

A few graphic scenes per reel are upgraded to one of these templates, so reels differ: each reel gets one STYLE VARIANT (default / rounded / glass / neo / brutalist /
minimal) and different templates, avoiding what the last reels used (state/last_templates.json when the folder is writable). Colours are the brand's (the pack is remapped
at import). Only templates whose words come from OUR script are selectable; templates with built-in demo content (prices, names, testimonials, stock tickers ...) are
imported but never picked, so a reel can never show an invented client, figure or quote.

Force with config.json -> templates: {"enabled": true, "max_per_video": 2, "variants": [...], "force": {"variant": "glass", "ids": ["bento-grid"]}}.
"""
from __future__ import annotations

import hashlib
import json
import random

from .common import ROOT, log

FPS = 30
VARIANTS = ("default", "rounded", "glass", "neo", "brutalist", "minimal")
STATE = ROOT / "state" / "last_templates.json"

# id -> (kind, animation length in frames, props builder name)
TEXT = {
    "bold-text-punch": 30, "fade-slide-up": 30, "spring-scale-in": 30, "typewriter-reveal": 90, "staggered-words": 90,
    "gradient-text": 90, "toggle-switch": 90, "app-feature-callout": 90, "meme-card": 90,
}
LIST = {"screen-showcase": 90, "onboarding-flow": 150}      # need 3+ items from the script (bento-grid is imported but not picked: its icons are multi-coloured emoji)
SELECTABLE = {**TEXT, **LIST}


def _clean(t: str, n: int) -> str:
    return " ".join(str(t or "").replace(",", " ").split())[:n]


def props_for(tid: str, gp: dict) -> dict | None:
    """The template's props from the scene's own words. None = not enough material for this template."""
    heading = _clean(gp.get("heading"), 30)
    if tid in LIST:
        items = [_clean(x, 28) for x in (gp.get("items") or (gp.get("mock") or {}).get("items") or []) if _clean(x, 28)]
        if len(items) < 3:
            return None
        items = items[:4] if tid == "onboarding-flow" else items[:3]
        key = "steps" if tid == "onboarding-flow" else "features"
        out = {key: ",".join(items), "title": heading or _clean(gp.get("kicker"), 30) or "Here is how"}
        return out
    if not heading:
        return None
    if tid == "meme-card":
        return {"topText": heading, "bottomText": _clean(gp.get("heading2"), 30), "emoji": ""}
    return {"text": heading}


def _state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def apply(graphics: dict, voiced: list, cfg: dict, seed: str) -> list[dict]:
    """Upgrade up to max_per_video graphic scenes in `graphics` (sid -> props) in place. Returns [{scene, template, variant}]."""
    tc = cfg.get("templates") or {}
    if not tc.get("enabled", True) or not graphics:
        return []
    rng = random.Random(int(hashlib.sha256(("tpl|" + seed).encode()).hexdigest(), 16))
    last = _state()
    force = tc.get("force") or {}
    variants = [v for v in tc.get("variants", VARIANTS) if v in VARIANTS] or list(VARIANTS)
    variant = force.get("variant") or rng.choice([v for v in variants if v != last.get("variant")] or variants)
    recent = set(last.get("ids", [])[-10:])
    used, done, prev_idx = [], [], -5
    for idx, (sid, sc, seconds, _mp3, _words) in enumerate(voiced):
        gp = graphics.get(sid)
        if not gp or gp.get("layout") not in ("title", "punch", "strike") or len(done) >= int(tc.get("max_per_video", 2)) or idx - prev_idx < 2:
            continue
        start = float((gp.get("times") or {}).get("heading", 0.3))
        pool = []
        for tid, frames in SELECTABLE.items():
            if force.get("ids") and tid not in force["ids"]:
                continue
            if frames / FPS + start > seconds + 0.4 or tid in used:        # the animation must finish inside the scene
                continue
            props = props_for(tid, gp)
            if props:
                pool.append((tid, props))
        fresh = [p for p in pool if p[0] not in recent] or pool
        if not fresh:
            continue
        tid, props = rng.choice(fresh)
        gp.update({"layout": "tpl", "tpl": {"id": tid, "variant": variant, "props": props, "atFrame": round(start * FPS)}, "mock": None, "items": [], "chips": []})
        gp["sfx"] = [{"type": "pop", "atSecond": round(start + 0.05, 3), "volume": 0.5}]
        used.append(tid)
        done.append({"scene": sid, "template": tid, "variant": variant})
        prev_idx = idx
    if done:
        log("templates: " + ", ".join(f"{d['scene']}={d['template']}" for d in done) + f" (variant {variant})")
    try:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps({"variant": variant, "ids": (last.get("ids", []) + used)[-24:]}))
    except OSError:
        pass
    return done
