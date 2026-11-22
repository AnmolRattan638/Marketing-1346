"""The viewer's business type for each reel (config/verticals.json). One is offered per reel, rotating so none repeats until all were used; the hook must name a business
type (any of them) so the context is clear in the first two seconds. `of()` says which one a line names ('' if none)."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "config" / "verticals.json"


def all_verticals() -> list[dict]:
    try:
        return json.loads(PATH.read_text(encoding="utf-8")).get("verticals", [])
    except Exception:
        return []


def pick(focus: str = "", today: date | None = None, slot: int = 0) -> dict:
    """The business type offered today: rotates daily (+ the second reel starts 5 further along, a different type from the first)."""
    vs = all_verticals()
    if not vs:
        return {}
    d = (today or date.today()).toordinal()
    return vs[(d + slot * 5) % len(vs)]


def of(line: str) -> str:
    """id of the business type the line names ('' if none)."""
    for v in all_verticals():
        try:
            if re.search(v["rx"], str(line or ""), re.I):
                return v["id"]
        except re.error:
            continue
    return ""


def block(focus: str = "", today: date | None = None, slot: int = 0, force: str = "") -> str:
    v = next((x for x in all_verticals() if x["id"] == force), None) or pick(focus, today, slot)
    if not v:
        return ""
    return (f"CONTEXT FIRST (the viewer must know in 2 seconds who this is for): the HOOK names the viewer's business, today: a {v['label']} (use the everyday word: clinic, salon, cafe, "
            f"coaching...). Never just 'business owners'. The whole script then stays true for that kind of business, the examples and scenes too.\n")
