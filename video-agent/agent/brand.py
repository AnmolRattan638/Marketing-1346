"""The brand palette: the reel uses ONLY the colours of your website.

`python -m agent.brand path/to/index.html` reads the CSS variables of the page (:root { --gold: #c9a84c; ... }), maps them to the tokens the video
components use and writes them to config.json -> brand.palette. Re-run it when the site's colours change. At render time the palette travels in the
manifest (look.palette) and template/src/graphics/themes.ts applies it, so no component carries a colour of its own.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .common import ROOT, log

# website variable -> video token
MAP = {"black": "bgTop", "navy": "bgBottom", "navy-card": "card", "navy-border": "cardEdge", "gold-bright": "accent", "gold": "accent2",
       "gold-light": "hot", "text": "text", "muted": "muted"}
DEFAULT = {"bgTop": "#06080D", "bgBottom": "#0A1220", "card": "#0D182B", "cardEdge": "#1A2A44", "ink": "#06080D", "text": "#E8EBF2", "muted": "#9AA3B2",
           "accent": "#F0C040", "accent2": "#C9A84C", "hot": "#FFF0B3", "ok": "#F0C040", "glow": "rgba(240,192,64,0.45)", "glowSoft": "rgba(240,192,64,0.14)"}


def _rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def palette_from_css(css: str) -> dict:
    vars_ = {k: v.upper() for k, v in re.findall(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\b", css)}
    pal = dict(DEFAULT)
    for name, token in MAP.items():
        if name in vars_:
            pal[token] = vars_[name]
    pal["ink"] = pal["bgTop"]
    pal["ok"] = pal["accent"]
    pal["glow"] = _rgba(pal["accent"], 0.45)
    pal["glowSoft"] = _rgba(pal["accent"], 0.14)
    return pal


def load_palette(cfg: dict) -> dict:
    return {**DEFAULT, **((cfg.get("brand") or {}).get("palette") or {})}


if __name__ == "__main__":
    src = Path(sys.argv[1])
    pal = palette_from_css(src.read_text(encoding="utf-8", errors="ignore"))
    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.setdefault("brand", {})["palette"] = pal
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log("brand palette written to config.json: " + json.dumps(pal))
