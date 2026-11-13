"""Web research for the video planner: the same Tavily + Exa module the post pipeline uses (src/web_research.py), so keys, limits, cleaning and the
kill switch behave identically. Optional and fail-safe: no key, WEB_RESEARCH=0 or any error means no evidence and the planner works as before."""
from __future__ import annotations

import sys
from pathlib import Path

from .common import log

_REPO = Path(__file__).resolve().parents[2]          # video-agent/agent/webresearch.py -> repository root
if str(_REPO) not in sys.path:
    sys.path.append(str(_REPO))


def for_topic(topic: str) -> tuple[str, list[dict]]:
    """-> (evidence text for the planner prompt, sources to save with the plan). ("", []) when there is nothing."""
    try:
        from src import web_research as wr
        if not wr.enabled():
            return "", []
        items = wr.evidence_for({"topic": topic}, {})
        for p in wr.problems():
            log(p)
        if not items:
            log("web research: no sources found for this topic, planning without them")
            return "", []
        log(f"web research: {len(items)} sources for '{topic[:60]}' ({', '.join(sorted({i['provider'] for i in items}))})")
        return wr.evidence_text(items, 2800), wr.sources_for_draft(items)
    except Exception as e:
        log(f"web research skipped: {str(e)[:160]}")
        return "", []


def caption_line(sources: list[dict], limit: int = 3) -> str:
    """A short line for the Telegram caption so the owner can check where a quoted fact came from."""
    if not sources:
        return ""
    return "\nSources: " + "; ".join(f"{s['domain']} ({s['url'][:70]})" for s in sources[:limit])
