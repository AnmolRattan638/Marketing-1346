"""Hook formulas for the script writer (config/hooks.json: nine open-loop openers from a 'Top 10 Hooks for Creators' reel, in Hinglish, with a ready example per service).
Each day the script is offered three formulas (rotating, so the openers vary) with an example for today's service; a hook that follows a formula scores higher and is labelled."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "config" / "hooks.json"
BONUS = 2.0          # added to a hook's score when it follows one of the formulas


def formulas() -> list[dict]:
    try:
        return json.loads(PATH.read_text(encoding="utf-8")).get("formulas", [])
    except Exception:
        return []


def pick(focus: str, today: date | None = None, n: int = 3, slot: int = 0) -> list[dict]:
    """n formulas for today, rotating through all of them so no formula repeats until every one has been offered (slot 2 = the second reel starts further along)."""
    fs = formulas()
    if not fs:
        return []
    start = ((today or date.today()).toordinal() * 3 + slot * 4) % len(fs)
    return [dict(fs[(start + k) % len(fs)], example=(fs[(start + k) % len(fs)].get("examples") or {}).get(focus, "")) for k in range(min(n, len(fs)))]


def formula_of(line: str) -> str:
    """Which formula a hook line follows ('' if none)."""
    for f in formulas():
        if re.search(f.get("match", "$^"), line or "", re.I):
            return f["id"]
    return ""


def block(focus: str, today: date | None = None, slot: int = 0) -> str:
    chosen = pick(focus, today, 3, slot)
    if not chosen:
        return ""
    lines = "\n".join(f'- {f["english"]}  ->  Hinglish: "{f["hinglish"]}..."  ({f["kind"]}).  Example for this service: "{f["example"]}"' for f in chosen)
    return ("PROVEN HOOK FORMULAS (from a top hooks reel). Of your 5 alternative first lines, three MUST follow these formulas, one each, filled with a concrete detail of today's topic; the other two may be any style. "
            "A formula hook is an OPEN LOOP: it ends unfinished (\"...\") and the next beat answers it with the first surprising, specific thing, so the viewer has a reason to stay.\n" + lines + "\n"
            "Keep it Hinglish, 5-13 words, no greeting, no promise stated as certain; 'nobody' becomes 'bohot kam log' (a hedge), never a flat claim.")
