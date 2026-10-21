"""Service explainer diagrams: colourful, structured, drawn by code (crisp, correct text; no AI picture) from config/services.json and
config/service_details.json. A SUPPORTING image (second slide, comment, story, library), never the post thumbnail.
No prices, no payment wording and no brand line on the image: only the service, who it is for, how it works or what is included, and the DM button.
Only verified facts are drawn (the real steps, plus anything the owner wrote in service_details.json); a layout that needs details the owner has
not provided is never used. Layouts and colour palettes rotate by date, so two diagrams in a row never look alike."""
import datetime as dt
import pathlib

from PIL import Image, ImageDraw

from . import config
from .agents import cards

W, H, M = 1080, 1350, 64
INK, MUTED, BG, WHITE, GREY = (17, 24, 39), (100, 110, 130), (246, 247, 251), (255, 255, 255), (170, 176, 192)
PALETTES = [      # accent, four step colours (all dark enough for white text), a soft second blob
    {"accent": (37, 99, 235), "steps": [(37, 99, 235), (124, 58, 237), (219, 39, 119), (21, 128, 61)], "blob": (219, 39, 119)},
    {"accent": (13, 148, 136), "steps": [(13, 148, 136), (37, 99, 235), (79, 70, 229), (21, 128, 61)], "blob": (37, 99, 235)},
    {"accent": (234, 88, 12), "steps": [(234, 88, 12), (225, 29, 72), (147, 51, 234), (180, 83, 9)], "blob": (147, 51, 234)},
    {"accent": (219, 39, 119), "steps": [(219, 39, 119), (124, 58, 237), (37, 99, 235), (13, 148, 136)], "blob": (37, 99, 235)},
]
LAYOUTS = ["steps", "path", "hub", "checklist", "tiers", "inquiry"]
FOR_WHOM = {"lead_gen": "Freelancers and agencies that sell to local businesses"}
DEFAULT_FOR = "Small businesses anywhere in India"


def details():
    return config.load_json(config.ROOT / "config" / "service_details.json", {})


def _wrap(d, text, fnt, maxw):
    lines, cur = [], ""
    for w in (text or "").split():
        t = f"{cur} {w}".strip()
        if cur and d.textlength(t, font=fnt) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = t
    return lines + ([cur] if cur else [])


def _fit(text, n=44):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "..."


def _short(service, det):
    if det.get("short"):
        return det["short"]
    first = service["pitch"].split(". ")[0].split(" (")[0].rstrip(".")
    return first if len(first) <= 120 else first[:117].rsplit(" ", 1)[0] + "..."


def steps(service):
    """The real process, in words that already exist in config/services.json (offers rule 2, audience, pay-after-approval). No price or payment wording."""
    return [("DM " + service["dm_keyword"], "Send the word in a message"), ("Honest advice", "A reply on whether it fits your business"),
            ("Done online", "In English and Hindi/Hinglish"), ("You approve the work", "You review it and approve it")]


def includes_of(det):
    return [_fit(x) for x in (det.get("includes") or []) if str(x).strip()][:6]


def tiers_of(det):
    """Packages the owner listed: [{name, includes}] (2 or 3, each with 1-4 short lines). No prices are ever drawn."""
    out = []
    for t in det.get("tiers") or []:
        inc = [_fit(x, 46) for x in (t.get("includes") or []) if str(x).strip()][:4]
        if str(t.get("name", "")).strip() and inc:
            out.append({"name": _fit(t["name"], 28), "includes": inc})
    return out[:3]


def eligible(det):
    if det.get("inquiry_only"):                      # e.g. lead generation: no packages, only how to enquire
        return ["inquiry"]
    n = len(includes_of(det))
    return ["steps", "path"] + (["hub"] if n >= 3 else []) + (["checklist"] if n >= 2 else []) + (["tiers"] if len(tiers_of(det)) >= 2 else [])


def choose(date, det):
    """(layout, palette index) for a date: consecutive days differ in layout (when 2+ are eligible) and always in palette."""
    n = dt.date.fromisoformat(str(date)).toordinal()
    el = eligible(det)
    return el[n % len(el)], n % len(PALETTES)


def _pill(d, x, y, text, fnt, fill, ink=WHITE, padx=22, h=52):
    w = int(d.textlength(text, font=fnt)) + 2 * padx
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=fill)
    d.text((x + padx, y + h // 2), text, font=fnt, fill=ink, anchor="lm")
    return w


def _header(d, f, service, det, accent):
    _pill(d, M, 64, "SERVICE EXPLAINER", f("SemiBold", 24), accent, h=48)
    y = 140
    for ln in _wrap(d, service["name"], f("ExtraBold", 62), W - 2 * M)[:2]:
        d.text((M, y), ln, font=f("ExtraBold", 62), fill=INK)
        y += 72
    y += 6
    for ln in _wrap(d, _short(service, det), f("Medium", 28), W - 2 * M)[:2]:
        d.text((M, y), ln, font=f("Medium", 28), fill=MUTED)
        y += 38
    d.text((M, y + 14), "FOR  " + _fit(det.get("for") or FOR_WHOM.get(service["id"], DEFAULT_FOR), 58), font=f("SemiBold", 26), fill=INK)
    return y + 14 + 34 + 24


def _steps(d, f, service, pal, y0, y1):
    sh = max(78, min(132, (y1 - y0 - 3 * 22) // 4))
    y = y0
    for i, (ttl, sub) in enumerate(steps(service)):
        col = pal["steps"][i]
        d.rounded_rectangle([M, y, W - M, y + sh], radius=28, fill=col)
        cy = y + sh // 2
        d.ellipse([M + 22, cy - 32, M + 86, cy + 32], fill=WHITE)
        d.text((M + 54, cy), str(i + 1), font=f("ExtraBold", 34), fill=col, anchor="mm")
        d.text((M + 112, cy - 16), ttl, font=f("SemiBold", 33), fill=WHITE, anchor="lm")
        d.text((M + 112, cy + 22), sub, font=f("Medium", 24), fill=WHITE, anchor="lm")
        y += sh
        if i < 3:
            d.polygon([(W // 2 - 12, y + 3), (W // 2 + 12, y + 3), (W // 2, y + 17)], fill=GREY)
            y += 22


def _path(d, f, service, pal, y0, y1):
    """A timeline: a spine down the middle, four numbered stops, cards alternating left and right."""
    gap = (y1 - y0) / 4
    cx, cw = W // 2, 408
    d.line([(cx, y0 + gap * 0.5), (cx, y0 + gap * 3.5)], fill=GREY, width=8)
    for i, (ttl, sub) in enumerate(steps(service)):
        col, cy = pal["steps"][i], int(y0 + gap * (i + 0.5))
        left = i % 2 == 0
        x0 = cx - 66 - cw if left else cx + 66
        d.rounded_rectangle([x0, cy - 70, x0 + cw, cy + 70], radius=26, fill=col)
        d.text((x0 + 26, cy - 28), ttl, font=f("SemiBold", 30), fill=WHITE, anchor="lm")
        for j, ln in enumerate(_wrap(d, sub, f("Medium", 23), cw - 52)[:2]):
            d.text((x0 + 26, cy + 10 + 28 * j), ln, font=f("Medium", 23), fill=WHITE, anchor="lm")
        d.line([(cx, cy), (x0 + cw if left else x0, cy)], fill=col, width=8)
        d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=WHITE, outline=col, width=8)
        d.text((cx, cy), str(i + 1), font=f("ExtraBold", 32), fill=col, anchor="mm")


def _hub(d, f, service, pal, y0, y1, items):
    """The service in a circle, what it includes on both sides, joined by lines."""
    cx, cy, r = W // 2, (y0 + y1) // 2, 120
    n = len(items)
    cw, ch = 330, 84
    left, right = items[: (n + 1) // 2], items[(n + 1) // 2:]
    pos = []
    for col, group in ((0, left), (1, right)):
        step = (y1 - y0) / max(len(group), 1)
        for k, t in enumerate(group):
            pos.append((M if col == 0 else W - M - cw, int(y0 + step * k + step / 2 - ch / 2), t, col))
    for i, (x, y, t, col) in enumerate(pos):
        d.line([(x + cw if col == 0 else x, y + ch // 2), (cx, cy)], fill=pal["steps"][i % 4], width=6)
    for i, (x, y, t, col) in enumerate(pos):
        d.rounded_rectangle([x, y, x + cw, y + ch], radius=24, fill=pal["steps"][i % 4])
        lines = _wrap(d, t, f("SemiBold", 27), cw - 40)[:2]
        for j, ln in enumerate(lines):
            d.text((x + cw // 2, y + ch // 2 + (j - (len(lines) - 1) / 2) * 32), ln, font=f("SemiBold", 27), fill=WHITE, anchor="mm")
    d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill=WHITE)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["accent"])
    lines = _wrap(d, service["name"], f("ExtraBold", 28), 2 * r - 30)[:3]
    for j, ln in enumerate(lines):
        d.text((cx, cy + (j - (len(lines) - 1) / 2) * 34), ln, font=f("ExtraBold", 28), fill=WHITE, anchor="mm")


def _checklist(d, f, service, pal, y0, y1, items):
    rh = min(122, (y1 - y0) // max(len(items), 1))
    y = y0 + max(0, ((y1 - y0) - rh * len(items)) // 2 - 10)
    for i, t in enumerate(items):
        col = pal["steps"][i % 4]
        d.rounded_rectangle([M, y, W - M, y + rh - 12], radius=24, fill=(236, 239, 247) if i % 2 == 0 else WHITE)
        cy = y + (rh - 12) // 2
        d.ellipse([M + 22, cy - 26, M + 74, cy + 26], fill=col)
        d.line([(M + 36, cy), (M + 46, cy + 10), (M + 62, cy - 10)], fill=WHITE, width=7, joint="curve")
        d.text((M + 100, cy), t, font=f("SemiBold", 33), fill=INK, anchor="lm")
        y += rh


def _tiers(d, f, service, pal, y0, y1, tiers):
    """One card per package, sized to its content and centred: the package name on a coloured pill, its included lines below.
    Text gets as large as the free height allows (never smaller than 25px)."""
    gap, avail = 22, y1 - y0

    def total(lh):
        return sum(22 + 60 + 22 + lh * len(t["includes"]) + 22 for t in tiers) + gap * (len(tiers) - 1)
    lh = next((x for x in (46, 40, 36, 32) if total(x) <= avail), 32)
    size = {46: 33, 40: 30, 36: 27, 32: 25}[lh]
    y = y0 + min(40, max(0, (avail - total(lh)) // 2))
    for i, t in enumerate(tiers):
        col = pal["steps"][i % 4]
        ch = 22 + 60 + 22 + lh * len(t["includes"]) + 22
        d.rounded_rectangle([M, y, W - M, y + ch], radius=30, fill=WHITE, outline=col, width=5)
        _pill(d, M + 26, y + 22, t["name"], f("ExtraBold", 32), col, h=60, padx=28)
        ty = y + 22 + 60 + 22
        for inc in t["includes"]:
            d.ellipse([M + 34, ty + lh // 2 - 7, M + 48, ty + lh // 2 + 7], fill=col)
            d.text((M + 68, ty + lh // 2), inc, font=f("Medium", size), fill=INK, anchor="lm")
            ty += lh
        y += ch + gap


def _inquiry(d, f, service, pal, y0, y1):
    """No packages: one clear message to enquire, with a chat bubble drawn by code and an arrow to the DM button."""
    cy = (y0 + y1) // 2
    d.rounded_rectangle([M, cy - 250, W - M, cy + 250], radius=44, fill=WHITE, outline=pal["accent"], width=6)
    bx, by = W // 2 - 70, cy - 200
    d.rounded_rectangle([bx, by, bx + 140, by + 100], radius=30, fill=pal["accent"])
    d.polygon([(bx + 30, by + 96), (bx + 30, by + 134), (bx + 66, by + 98)], fill=pal["accent"])
    for i in range(3):
        d.ellipse([bx + 34 + i * 34, by + 42, bx + 52 + i * 34, by + 60], fill=WHITE)
    ty = cy - 30
    for ln in _wrap(d, "Interested? Send a message to enquire.", f("ExtraBold", 54), W - 2 * M - 120)[:3]:
        d.text((W // 2, ty), ln, font=f("ExtraBold", 54), fill=INK, anchor="mm")
        ty += 66
    d.text((W // 2, ty + 18), "Message the word below to start the conversation.", font=f("Medium", 28), fill=MUTED, anchor="mm")
    d.polygon([(W // 2 - 22, cy + 270), (W // 2 + 22, cy + 270), (W // 2, cy + 304)], fill=pal["accent"])


def render(service, path, brand=None, det=None, layout=None, palette=0):
    """1080x1350 explainer. Draws only verified facts and the owner's own details; a details layout without details is refused."""
    det = det if det is not None else details().get(service["id"], {})
    pal = PALETTES[palette % len(PALETTES)]
    items = includes_of(det)
    layout = layout or "steps"
    tiers = tiers_of(det)
    if (layout in ("hub", "checklist") and len(items) < (3 if layout == "hub" else 2)) or (layout == "tiers" and len(tiers) < 2):
        raise ValueError(f"layout {layout!r} needs package details for {service['id']}")
    im = Image.new("RGB", (W, H), BG)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.ellipse([W - 470, -300, W + 280, 450], fill=pal["accent"] + (38,))
    od.ellipse([-260, H - 380, 380, H + 240], fill=pal["blob"] + (22,))
    im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(im)
    f = cards.font

    y = _header(d, f, service, det, pal["accent"])
    d.text((M, y), {"steps": "HOW IT WORKS", "path": "HOW IT WORKS", "hub": "WHAT IT INCLUDES", "checklist": "WHAT YOU GET", "tiers": "PACKAGES", "inquiry": "TO ENQUIRE"}[layout], font=f("SemiBold", 24), fill=MUTED)
    y0, y1 = y + 42, H - 200
    if layout == "steps":
        _steps(d, f, service, pal, y0, y1)
    elif layout == "path":
        _path(d, f, service, pal, y0, y1)
    elif layout == "hub":
        _hub(d, f, service, pal, y0, y1, items)
    elif layout == "tiers":
        _tiers(d, f, service, pal, y0, y1, tiers)
    elif layout == "inquiry":
        _inquiry(d, f, service, pal, y0, y1)
    else:
        _checklist(d, f, service, pal, y0, y1, items)

    label = "DM " + service["dm_keyword"]                           # the only thing at the bottom
    fnt = f("ExtraBold", 40)
    pw = int(d.textlength(label, font=fnt)) + 120
    d.rounded_rectangle([W // 2 - pw // 2, H - 150, W // 2 + pw // 2, H - 62], radius=44, fill=INK)
    d.text((W // 2, H - 106), label, font=fnt, fill=WHITE, anchor="mm")

    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=92, optimize=True)
    return path


def render_for(service, date, path, brand=None):
    """The diagram for a service on a date: rotating layout and palette, details-based layouts only when the owner provided details."""
    det = details().get(service["id"], {})
    layout, pal = choose(date, det)
    render(service, path, brand, det=det, layout=layout, palette=pal)
    return {"path": str(path), "layout": layout, "palette": pal}
