"""The script writer's pronunciation gate.

The voice rules live in video-agent/agent/speech_text.py (a pure standard-library file). This module loads THAT file by path, so the script writer and the voice use the very same
rules and cannot drift apart. A script is rejected here when a spoken line contains something the voice would still say wrong (an unknown ALL-CAPS word, digits glued to letters,
a leftover symbol). The reason names the beat, the word, where it was heard and what to write instead, so the repair round rewrites only that beat and the lesson is concrete."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SPEECH = ROOT / "video-agent" / "agent" / "speech_text.py"
_mod = None


def speech():
    global _mod
    if _mod is None:
        spec = importlib.util.spec_from_file_location("speech_text_shared", _SPEECH)
        _mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = _mod                  # a @dataclass inside the file needs its module registered first
        spec.loader.exec_module(_mod)
    return _mod


def keywords(*extra: str) -> set[str]:
    """Every DM keyword (SITE, BOT, ADS...): capital-letter words that are MEANT as words, so they are never flagged."""
    found = {str(e) for e in extra if e}
    try:
        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == "dm_keyword" and v:
                        found.add(str(v))
                    else:
                        walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(json.loads((ROOT / "config" / "services.json").read_text(encoding="utf-8")))
    except Exception:
        pass
    return found


def problems(script: dict, *extra_keywords: str) -> list[str]:
    """Rejection reasons for a master script, one per finding, each starting with the beat name (so by_beat() routes it to that beat)."""
    try:
        sp = speech()
    except Exception as e:                       # the gate must never take the day down: without the voice rules it steps aside and says so
        print(f"[pronounce] voice rules not available ({e}); pronunciation not checked", file=sys.stderr)
        return []
    allow, out = keywords(*extra_keywords), []
    for b in script.get("beats") or []:
        for f in sp.audit(str(b.get("line") or ""), allow):
            out.append(f"{b.get('beat')}: pronunciation: {f.message}")
    return out
