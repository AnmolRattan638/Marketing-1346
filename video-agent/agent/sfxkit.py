"""The SFX Kit (CC0, 320 sounds, assets/sfxkit/): exact sync points and levels for the sound effects of a reel.

What the kit's data buys over the old single-point files:
  - sync_at: the second INSIDE the file that must meet the moment on screen (a whoosh's peak, a riser's arrival, a click's attack). A cue starts at
    (moment - sync_at), so the sound lands on the frame instead of "roughly near" it (the old code used one fixed lead per kind).
  - under_voice_db: how far a sound must come down where it overlaps speech. Reels are voice-led, so it is always applied.
  - avoid_voice: sounds that mask a voice (bass-heavy hits, stings, rings, busy celebrations, noisy glitches) are never used under narration.
  - levels sit on one loudness scale, so a soft whoosh stays quieter than a hard one; files are NOT re-normalised.

Fail-open by design: a missing or unreadable catalog, or a missing MP3, means no kit sounds, and sfx_plan falls back to the old files. Nothing here can stop a draft.
"""
from __future__ import annotations

import json

from .common import ROOT, log

DIR = ROOT / "assets" / "sfxkit"
REF_VOLUME = 0.55        # the old whoosh level: a peak-normalised file at 0.55 sits near the kit's own reference (about -20.5 LUFS for a medium effect)

_cache: dict = {}


def _no(i: str, *parts: str) -> bool:
    return not any(p in i for p in parts)


# kind -> which kit sounds may play it. The kinds are the ones the planner and the code already use (sfx_plan.FAMILIES) plus the internal 'number'.
RULES = {
    "whoosh": lambda i, e: (e["category"] in ("whooshes", "swishes-and-zips", "reverse-whooshes") and _no(i, "-hard", "-strong", "zip-out"))
                           or (e["category"] == "swipes" and i.endswith("-soft")),
    "pop": lambda i, e: (e["category"] == "pops" and not i.endswith("-out")) or i in ("tone-ding-mid", "tone-ding-high", "shimmer-short-sparkle", "shimmer-short-soft"),
    "click": lambda i, e: (e["category"] == "interface" and _no(i, "clap", "hover")) or i in ("data-tick", "writing-pen-tick", "writing-marker-tick"),
    "riser": lambda i, e: i.startswith(("riser-1s", "riser-2s")),
    "impact": lambda i, e: e["category"] == "impacts" and not i.endswith("-hard"),
    "number": lambda i, e: i == "data-number-land",
}


def reset() -> None:
    _cache.clear()


def load() -> dict:
    """{id: entry} for every catalog sound whose MP3 exists. {} when the kit is missing or broken."""
    if "sounds" not in _cache:
        sounds: dict = {}
        try:
            raw = json.loads((DIR / "catalog.json").read_text(encoding="utf-8"))["sounds"]
            sounds = {i: e for i, e in raw.items() if (DIR / f"{i}.mp3").exists() and isinstance(e.get("sync_at"), (int, float))}
        except Exception as ex:
            log(f"sfx kit not available ({str(ex)[:80]}); using the plain sound files")
        _cache["sounds"] = sounds
    return _cache["sounds"]


def get(sound_id: str) -> dict | None:
    return load().get(sound_id)


def entries(kind: str) -> list[tuple[str, dict]]:
    """Kit sounds that may play this kind, never one that masks a voice."""
    if kind not in _cache:
        rule = RULES.get(kind)
        _cache[kind] = sorted((i, e) for i, e in load().items() if rule and not e.get("avoid_voice") and rule(i, e)) if rule else []
    return _cache[kind]


def volume(base: float, entry: dict) -> float:
    """The cue's planned volume, scaled to the kit: relative to the old reference level, and down by the sound's own under-voice amount."""
    v = (float(base) / REF_VOLUME) * 10 ** (float(entry.get("under_voice_db", -3)) / 20)
    return round(max(0.05, min(1.0, v)), 3)
