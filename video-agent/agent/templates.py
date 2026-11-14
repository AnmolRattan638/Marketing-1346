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


def _norm(t: str) -> str:
    return "".join(c for c in str(t).lower() if c.isalnum())


def _spoken(words: list[dict], text: str, not_before: float) -> list[tuple[float, float] | None]:
    """For each word of `text`, (start, end) of the first matching spoken word in order, at/after `not_before` (None when not spoken)."""
    out, i = [], 0
    for tok in str(text).split():
        n, hit = _norm(tok), None
        for j in range(i, len(words)):
            if words[j]["start"] >= not_before - 0.35 and _norm(words[j]["text"]) == n and n:
                hit, i = (float(words[j]["start"]), float(words[j]["end"])), j + 1
                break
        out.append(hit)
    return out


# the template frame where each moment happens (read from the templates' own animation code)
ITEM0 = {"onboarding-flow": (10, 25), "screen-showcase": (20, 10)}       # first item frame, frames between items


def _anchors(tid: str, gp: dict, words: list[dict], head: float, seconds: float) -> list[tuple[float, int]]:
    """[(scene second, template frame)] pinning the template's moments to the spoken words. Fallback: start on the heading word."""
    heading = _clean(gp.get("heading"), 30)
    sp = _spoken(words, heading, head) if heading else []
    first = next((x for x in sp if x), None)
    t0 = first[0] if first else head
    last = next((x for x in reversed(sp) if x), None)
    t_last = last[0] if last else t0
    a: list[tuple[float, int]] = [(t0, 0)]
    if tid == "typewriter-reveal":
        a = [(t0, 0), (max((last[1] if last else t0 + 1.8), t0 + 0.8), 70)]               # typing runs exactly over the spoken phrase
    elif tid == "staggered-words":
        pts = [(x[0], i * 6 + 4) for i, x in enumerate(sp) if x]
        a = pts if len(pts) >= 2 else [(t0, 0)]
    elif tid == "toggle-switch":
        a = [(t0, 5), (max(t_last, t0 + 0.25), 15)]                                         # the switch flips on the last heading word
    elif tid == "app-feature-callout":
        a = [(t0, 15)]
    elif tid == "meme-card":
        second = _spoken(words, _clean(gp.get("heading2"), 30), t0 + 0.1)
        tb = next((x[0] for x in second if x), t0 + 0.7)
        a = [(t0, 3), (max(tb, t0 + 0.3), 22)]
    elif tid in ITEM0:
        f0, df = ITEM0[tid]
        times = (gp.get("times") or {}).get("items") or []
        n = len(gp.get("items") or (gp.get("mock") or {}).get("items") or [])
        n = min(n, 4 if tid == "onboarding-flow" else 3, len(times))
        a = [(float(times[i]), f0 + df * i) for i in range(n)]
        if a and head < a[0][0] - f0 / FPS + 0.01:
            a.insert(0, (head, 0))
    out: list[tuple[float, int]] = []                                                        # increasing in both, at least 0.12 s apart
    for t, f in sorted(a):
        if not out or (t - out[-1][0] >= 0.12 and f > out[-1][1]):
            out.append((round(t, 3), f))
    return out or [(round(t0, 3), 0)]


def _words_of(voiced: list, sid: str) -> list[dict]:
    return next((v[4] for v in voiced if v[0] == sid), [])


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
            if tid in used:
                continue
            props = props_for(tid, gp)
            if not props:
                continue
            anchors = _anchors(tid, gp, _words_of(voiced, sid), start, seconds)
            end = anchors[-1][0] + (frames - anchors[-1][1]) / FPS
            if end <= seconds + 0.4:                                      # the animation must finish inside the scene
                pool.append((tid, props, anchors))
        fresh = [p for p in pool if p[0] not in recent] or pool
        if not fresh:
            continue
        tid, props, anchors = rng.choice(fresh)
        gp.update({"layout": "tpl", "tpl": {"id": tid, "variant": variant, "props": props, "atFrame": round(start * FPS),
                                            "anchors": [[round(t * FPS), f] for t, f in anchors]}, "mock": None, "items": [], "chips": []})
        gp["sfx"] = [{"type": "pop", "atSecond": round(anchors[0][0] + 0.05, 3), "volume": 0.5}]
        if tid in ITEM0:
            gp["sfx"] += [{"type": "click", "atSecond": round(t + 0.02, 3), "volume": 0.28} for t, _ in anchors[1:] if t < seconds - 0.2][:3]
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
