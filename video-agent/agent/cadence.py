"""Picture cadence: something on screen must change at least every MAX_GAP seconds (2-3 s), or the viewer drifts.

A change is an fx graphic, an emphasis pulse, or a scene cut. When a scene runs longer than MAX_GAP without one, `fill` adds a pulse (the picture hits) at the
spoken word boundary nearest to each missing beat, never inside a word. Pure, so it is testable without a render.
"""
from __future__ import annotations

MAX_GAP = 2.6


def fill(events: list[float], seconds: float, words: list[dict] | None) -> list[float]:
    """events = seconds (scene-relative) where the picture already changes; returns them plus the pulses needed to keep every gap <= MAX_GAP."""
    ev = sorted(set([0.0, *[e for e in events if 0 <= e <= seconds]]))
    ends = sorted(float(w["end"]) for w in words or [] if w.get("end") is not None)
    added: list[float] = []
    i = 0
    while i < len(ev) - 1 or seconds - ev[-1] > MAX_GAP:
        nxt = ev[i + 1] if i < len(ev) - 1 else seconds
        if nxt - ev[i] > MAX_GAP:
            ideal = ev[i] + MAX_GAP * 0.9
            near = [e for e in ends if ev[i] + 1.0 <= e <= min(ev[i] + MAX_GAP, nxt - 0.5)]
            t = min(near, key=lambda e: abs(e - ideal)) if near else ideal
            if t >= nxt - 0.3:
                i += 1
                continue
            ev.insert(i + 1, t)
            added.append(round(t, 3))
        i += 1
        if i >= len(ev) - 1 and seconds - ev[-1] <= MAX_GAP:
            break
    return added
