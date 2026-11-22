"""What shape a reel had, as labels the learning loop can compare: 'retention-v2' (context-first hook + rehook + open loops) vs 'classic' (the old structure).
The labels travel with the draft into data/post_results.json, so after ~10-15 reels the weekly review shows which structure and which business type really earn more
on THIS account; the pipeline never has to guess from other creators' advice."""
from __future__ import annotations

from . import verticals
from .agents import scriptwriter


def describe(master) -> dict:
    """Labels for a master script ({} when there is none)."""
    beats = (master or {}).get("beats") or []
    if not beats:
        return {}
    has_rehook = any(b.get("beat") == "rehook" for b in beats)
    vertical = verticals.of(beats[0].get("line"))
    loops = scriptwriter.open_loops(beats)
    return {"structure": "retention-v2" if (has_rehook and vertical) else ("rehook-only" if has_rehook else "classic"),
            "vertical": vertical or "none", "context_first": bool(vertical), "rehook": has_rehook, "open_loops": loops,
            "style": (master or {}).get("style"), "hook_formula": (master or {}).get("hook_formula") or "none",
            "words": sum(len(str(b.get("line") or "").split()) for b in beats)}
