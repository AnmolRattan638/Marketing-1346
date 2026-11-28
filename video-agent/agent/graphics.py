"""Motion-graphic scenes: the visual of a scene is built from animated components (headings, UI mock-ups, checklists...) instead of footage.

The planner describes a scene with `graphic`; every element appears on a SPOKEN word (Whisper word starts), the same way captions,
SFX and fx do. Styles follow the reference reels: a step badge + heading, a mock-up card (terminal typing, comment box, checklist,
browser page, file extract), struck-through lists, full-colour punch slides with a ghost word, and a closing logo animation.

  layout   what it shows
  title    kicker + big heading (+ chips)              opening / topic
  step     step badge, kicker, heading, mock-up card   one idea shown as an interface
  strike   list of words struck through one by one, then the heading   "no editing, no cutting, no software"
  numeral  card with a huge italic numeral (step) fading into the card, the item title (heading) built word by word, one small line (kicker)   "1  Music selection" list items
  inverse  the inverse (ice-white) card: one sentence (heading + heading2) fades in word by word, the last word bold italic   the line to remember
  tiles    hook title (heading, kicker) with number tiles (items: "1","2"...) popping in step with the count, hairlines to the title   "5 easy edits" openers
  punch    full-colour slide with a ghost word behind a short line   the one line that must land
  logo     your logo animation + call to action        added automatically at the end, never planned

  mock.type   items mean
  terminal    lines; "> text" is typed, "ok: text" appears with a green tick, anything else appears at once
  comment     [typed comment]; a POST button is pressed when typing ends
  checklist   rows, ticked one by one
  browser     [headline, sub line, button label]: a small website building up (your trade is websites)
  file        [file name, folder name]: the file turns into an extracted folder
  window      rows that fade in
  chat        bubbles: a customer message, "you: ..." is the business reply, "..." an unanswered state (PROOF CARD, drawn with an EXAMPLE tag)
  maps        [business name, category, status like "Closed now"]: a map listing (PROOF CARD)
  gauge       [label, verdict word, zone slow|ok|fast]: a speed gauge with no figure (PROOF CARD)
  proof       [id] (gym | restaurant | cafe | hotel = never answered; chatbot = a business's own WhatsApp AI that answered a mystery customer within a minute): a REAL blurred WhatsApp screenshot of a message sent to a local business, delivered, never answered (assets/proof, agent/proof.py). The
              card says only what the screenshot shows (sent date, no reply by the check date); say it the same way, never a percentage or "all businesses"
  tracker     rows of a list (title = topic): a "02/05" counter chip, a typed command bar, rows ticking one by one: the "wait for the end" counter
  follow      [handle, one line] (title = name): a profile card, a pointer glides to Follow and clicks on the first reveal word
  stickers    [starburst word, live pill, count badge, handwritten note]: badges that pop on their words
  widgets     [big, label, big, label, ...] up to 3 frosted glass cards floating in
  bill        ["name|price", ...] (title = header): a receipt printing line by line with a total
  stamp       [card text, stamp word]: a card and a stamp that slams on the first reveal word
  tier        [S item, A item, B item ...]: a tier list, each item drops into the next row on its word
  wall        [handles...] (title = you): a grid of profile tiles filling in, the last one highlighted
  phonefan    [line, line, line]: three phones fan out, one line each
  pullback    [line]: a phone fills the frame then pulls back into a feed of posts
  countdown   ["MM:SS"]: a flip clock counting down to zero over the scene
  keyrain     [key labels]: key caps rain down and pile up
  viewfinder  [line] (title unused): camera viewfinder (REC, timecode, corners) zooming in on the line
  lockon      [word]: tracking brackets snap onto the word and say LOCKED
  rabbit      [word]: nested frames shrinking to the word
  giant       [heavy word, script word]: giant stacked caption words
  collage     [giant word, line, line ...]: one giant gold word with bold lines under it

Timing: `heading_at` (a word) places the heading, `reveal` is one word per item (or fewer: the rest are spread evenly).
A word that is not spoken is replaced by an even spread, so nothing is ever placed at a random moment.
"""
from __future__ import annotations

import re

from .common import log

LAYOUTS = ("title", "step", "strike", "punch", "hook", "numeral", "inverse", "tiles")          # "hook" is never chosen by the planner: viral.stop_fix forces it on scene 1
EFFECTS = ("widgets", "bill", "stamp", "tier", "wall", "phonefan", "pullback", "countdown", "keyrain", "viewfinder", "lockon", "rabbit", "giant", "collage")      # the animation-style pool: every reel must use several (agent/effects_rule.py)
MOCKS = ("terminal", "comment", "checklist", "browser", "file", "window", "chat", "maps", "gauge", "tracker", "follow", "stickers", "proof",
         "widgets", "bill", "stamp", "tier", "wall", "phonefan", "pullback", "countdown", "keyrain", "viewfinder", "lockon", "rabbit", "giant", "collage")
HEAD_AT = 0.12            # heading appears this long after the scene starts when no word is given
HOLD = 0.8                # last element lands at least this long before the scene ends, so it can be read
GAP = 0.35                # minimum seconds between two reveals
TYPE_CPS = 16             # typing speed (characters per second), shared with the Remotion components
MAX_ITEMS = 6


def _norm(w: str) -> str:
    return re.sub(r"[^\w]+", "", w.lower(), flags=re.UNICODE)


def _find(words: list[dict], target: str | None) -> float | None:
    t = _norm(target or "")
    hit = next((w for w in words if _norm(w["text"]) == t), None) if t else None
    return hit["start"] if hit else None


def spread(known: list[float | None], n: int, start: float, end: float, gap: float = GAP) -> list[float]:
    """n increasing times: the known ones are kept, the unknown ones are spread evenly between their neighbours (and up to `end`)."""
    known = (list(known) + [None] * n)[:n]
    out: list[float] = []
    prev = start - gap
    i = 0
    while i < n:
        k = known[i]
        if k is not None and k >= prev + gap:
            out.append(k)
            prev = k
            i += 1
            continue
        j = i
        while j < n and (known[j] is None or known[j] < prev + gap):
            j += 1
        run = j - i
        if j < n:
            step = max(gap, (known[j] - prev) / (run + 1))
        else:
            step = max(gap, (end - prev) / run)
        for _ in range(run):
            prev += step
            out.append(prev)
        i = j
    return [round(t, 3) for t in out]


HOOK_VARIANTS = ("phone", "slam", "zig")


def scene_kind(scene: dict) -> str:
    return "graphic" if scene.get("graphic") else "footage"


def resolve_graphic(scene: dict, words: list[dict], seconds: float) -> dict | None:
    """The planner's `graphic` -> the props of the GraphicScene component, with every element's time. None = not usable, use footage."""
    g = scene.get("graphic") or {}
    layout = g.get("layout")
    if layout not in LAYOUTS:
        return None
    mock = g.get("mock") if isinstance(g.get("mock"), dict) and g["mock"].get("type") in MOCKS else None
    proof = None
    if mock and mock.get("type") == "proof":
        from . import proof as _proof
        proof = _proof.props(str((mock.get("items") or [""])[0]))
        if not proof:
            mock = None                           # no usable proof (unknown id or stale check): never fake one
    if layout == "step" and not mock:
        layout = "title"                          # a step without a mock-up is a title
    items = [str(x)[:60] for x in ((mock or {}).get("items") if layout == "step" else g.get("items")) or []][:MAX_ITEMS]
    if layout in ("title", "step", "punch", "numeral", "inverse", "tiles") and not str(g.get("heading") or "").strip():
        log(f"graphic '{layout}' has no heading, scene falls back to footage")
        return None
    if layout in ("strike", "tiles") and not items:
        log("graphic 'strike' has no items, scene falls back to footage")
        return None

    last = max(seconds - HOLD, 0.8)
    head = _find(words, g.get("heading_at")) if g.get("heading_at") else None
    if layout in ("strike", "tiles"):
        # the list comes first, the heading lands after the last strike
        first = HEAD_AT + 0.5
        times = spread([_find(words, w) for w in (g.get("reveal") or [])], len(items), first, max(last - 0.9, first + GAP * len(items)))
        head = head if head is not None and head > times[-1] else min(times[-1] + 0.9, last)
    else:
        head = head if head is not None else HEAD_AT
        first = max(head + 0.55, 0.7)
        times = spread([_find(words, w) for w in (g.get("reveal") or [])], len(items), first, max(last, first + GAP * len(items))) if items else []
    mock_at = round(max(0.0, (times[0] - 0.3) if times else head + 0.4), 3)
    if proof and mock:
        mock_at = round(min(mock_at, head + 0.3), 3)           # the real screenshot is the point of the scene: it lands with the heading, never seconds into an empty screen
    chips = [str(c)[:24] for c in (g.get("chips") or [])][:3]
    chips_at = round(min((times[-1] + 0.5) if times else head + 0.6, max(seconds - 0.5, 0.2)), 3)

    props: dict = {
        "layout": layout,
        "step": str(g.get("step") or "")[:14],
        "kicker": str(g.get("kicker") or "")[:40],
        "heading": (f"{g.get('heading') or ''} {g.get('heading2') or ''}".strip()[:60] if layout == "inverse" else str(g.get("heading") or "")[:30]),
        "heading2": str(g.get("heading2") or "")[:30],
        "ghost": str(g.get("ghost") or g.get("heading") or "")[:12],
        "chips": chips,
        "items": items if layout in ("strike", "tiles") else [],
        "mock": {"type": mock["type"], "title": str(mock.get("title") or "")[:30], "items": items} if mock and layout == "step" else None,
        "times": {"heading": round(head, 3), "mock": mock_at, "items": times, "chips": chips_at},
    }
    if proof and props["mock"]:
        from . import proof as _proof
        _proof.stage(proof["id"])
        props["mock"]["items"] = [proof["tag"], proof["src"], str(proof["ratio"])]
    if props["mock"] and mock["type"] == "comment" and items:
        props["mock"]["pressAt"] = round(times[0] + len(items[0]) / TYPE_CPS + 0.4, 3)     # POST is pressed when the typing ends

    cues: list[dict] = []                         # soft UI sounds, deliberately few
    if layout == "punch":
        cues.append({"type": "pop", "atSecond": props["times"]["heading"], "volume": 0.6})
    elif layout == "step" and mock["type"] == "checklist":
        cues += [{"type": "click", "atSecond": t, "volume": 0.28} for t in times[:3]]
    elif layout == "step" and mock["type"] == "comment" and "pressAt" in props["mock"]:
        cues.append({"type": "click", "atSecond": props["mock"]["pressAt"], "volume": 0.4})
    elif layout == "step":
        cues.append({"type": "click", "atSecond": mock_at, "volume": 0.28})
    elif layout == "strike":
        cues += [{"type": "click", "atSecond": t, "volume": 0.3} for t in times[:3]]
    if layout == "hook":                                                       # the breaking-phone opening: an impact on EVERY spoken word, a whoosh into it
        from . import scenarios
        seed = sum(ord(c) for w in words for c in str(w.get("text", "")))
        props["hook"] = {"notifs": scenarios.hook_notifs(), "variant": HOOK_VARIANTS[seed % len(HOOK_VARIANTS)] if len(words) <= 7 else HOOK_VARIANTS[seed % 2]}      # the opening is not the same picture every time
        props["emphasis"] = [str(w)[:20] for w in (g.get("emphasis") or [])][:6]
        cues = [{"type": "whoosh", "atSecond": 0.0, "volume": 0.5}] + [{"type": "impact", "atSecond": round(float(w["start"]), 3), "volume": 0.55 if i == 0 else 0.4} for i, w in enumerate(words[:9])]
    props["sfx"] = [c for c in cues if 0 <= c["atSecond"] < seconds - 0.1]
    return props


def _heading(narration: str) -> str:
    """Up to three of the longest words of the line, in the order spoken, as a big heading."""
    ws = re.findall(r"[^\W\d_][\w']*", narration or "")
    big = sorted(range(len(ws)), key=lambda i: -len(ws[i]))[:3]
    big = [i for i in sorted(big) if len(ws[i]) >= 4]
    return " ".join(ws[i] for i in big).upper()[:30] or "WATCH THIS"


def repair_graphic(scene: dict) -> dict:
    """The planner's graphic that could not be used (no heading, a layout we do not have, an empty list, a step without a mock-up): keep what is good (a real proof stays a
    proof) and fill the rest from the narration, so a scene is never left as an empty screen with only captions."""
    g = dict(scene.get("graphic") or {})
    mock = g.get("mock") if isinstance(g.get("mock"), dict) else None
    head = str(g.get("heading") or "").strip() or _heading(scene.get("narration", ""))
    if mock and mock.get("type") == "proof":
        return {"layout": "step", "heading": head[:30], "kicker": str(g.get("kicker") or "")[:40], "mock": mock}
    return {"layout": "title", "heading": head[:30], "kicker": str(g.get("kicker") or "")[:40]}


def fallback_graphic(scene: dict) -> dict:
    """A scene that must be a graphic but has none (for example no raw clips exist, so footage is limited to one stock shot)."""
    words = [w for w in re.findall(r"[^\W\d_]{4,}", scene.get("narration", ""))]
    heading = max(words, key=len).upper() if words else "WATCH THIS"
    return {"layout": "title", "heading": heading[:30], "kicker": ""}
