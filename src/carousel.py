"""Carousel slides. Slide 1 is the day's hook image (already generated, in the day's visual family). The other slides are drawn by code in the same family colour, so
the series looks connected: a role label, a slide counter, a progress bar along the bottom and a swipe cue. Text is crisp and never AI-drawn.
Order (enforced by src/agents/carousel.py): hook -> problem -> solution (-> service diagram when the taste asks for it) -> CTA.
Instagram and LinkedIn get every slide; Bluesky allows 4 images, so it gets hook, first problem, first solution and CTA."""
import datetime as dt
import pathlib
import re

from . import config, diagrams
from .agents import cards, image

M = 84
LABEL = {"problem": "THE PROBLEM", "solution": "THE FIX"}
BODY = (214, 220, 232)
TRACK = (56, 64, 84)


def _accent_for(style_id):
    for v in image.style().get("variants") or []:
        if v.get("id") == style_id and v.get("accent_rgb"):
            return v["accent_rgb"]
    return None


def _progress(d, n, total):
    W, H = cards.W, cards.H
    gap, y = 10, H - 96
    w = (W - 2 * M - gap * (total - 1)) / total
    for i in range(total):
        x0 = M + i * (w + gap)
        d.rounded_rectangle([x0, y, x0 + w, y + 10], radius=5, fill=cards.ACCENT if i < n else TRACK)
    if n < total:                                           # the font has no arrow glyph, so the arrow is drawn
        ay = y - 34
        d.line([(W - M - 46, ay), (W - M - 8, ay)], fill=cards.MUTED, width=5)
        d.polygon([(W - M - 18, ay - 12), (W - M, ay), (W - M - 18, ay + 12)], fill=cards.MUTED)
        d.text((W - M - 62, ay), "Swipe", font=cards.font("SemiBold", 30), fill=cards.MUTED, anchor="rm")


def _headline_size(text):
    n = len(text.split())
    return 88 if n <= 5 else 76 if n <= 9 else 64


def _text_slide(slide, n, total, source=None):
    im, d = cards._base()
    f, W = cards.font, cards.W
    label = LABEL.get(slide["role"])
    if label:
        fnt = f("SemiBold", 28)
        w = int(d.textlength(label, font=fnt)) + 56
        d.rounded_rectangle([M, 84, M + w, 84 + 54], radius=27, outline=cards.ACCENT, width=3)
        d.text((M + 28, 84 + 27), label, font=fnt, fill=cards.ACCENT, anchor="lm")
    d.text((W - M, 111), f"{n} / {total}", font=f("SemiBold", 30), fill=cards.MUTED, anchor="rm")
    size = _headline_size(slide["headline"])
    head = diagrams._wrap(d, slide["headline"], f("ExtraBold", size), W - 2 * M)[:5]
    body = diagrams._wrap(d, slide["body"], f("Medium", 42), W - 2 * M)[:9]
    block = len(head) * int(size * 1.16) + 28 + len(body) * 60
    y = 190 + max(40, (cards.H - 230 - 190 - block) // 2)       # the text block sits in the middle of the free space
    for ln in head:
        d.text((M, y), ln, font=f("ExtraBold", size), fill=cards.WHITE)
        y += int(size * 1.16)
    y += 28
    for ln in body:
        d.text((M, y), ln, font=f("Medium", 42), fill=BODY)
        y += 60
    if source:
        d.text((M, cards.H - 150), f"Source: {source}", font=f("Medium", 27), fill=cards.MUTED, anchor="ls")
    _progress(d, n, total)
    return im


def _cta_slide(slide, n, total):
    im, d = cards._base()
    f, W, H = cards.font, cards.W, cards.H
    d.text((W // 2, 430), "THE NEXT STEP", font=f("SemiBold", 30), fill=cards.MUTED, anchor="mm")
    lines = diagrams._wrap(d, slide["body"] or "Interested? Send a message to enquire.", f("ExtraBold", 62), W - 2 * M - 40)[:3]
    y = 520
    for ln in lines:
        d.text((W // 2, y), ln, font=f("ExtraBold", 62), fill=cards.WHITE, anchor="mm")
        y += 76
    fnt = f("ExtraBold", 96)
    pw = int(d.textlength(slide["headline"], font=fnt)) + 150
    top = y + 40
    d.rounded_rectangle([W // 2 - pw // 2, top, W // 2 + pw // 2, top + 170], radius=85, fill=cards.ACCENT)
    d.text((W // 2, top + 85), slide["headline"], font=fnt, fill=cards.BG, anchor="mm")
    d.polygon([(W // 2 - 26, top + 210), (W // 2 + 26, top + 210), (W // 2, top + 250)], fill=cards.ACCENT)
    _progress(d, n, total)
    return im


def render(car, focus, date, hook_path, style_id=None, fact=None):
    """car = agents.carousel.build()[0]; hook_path = the day's hook image (relative to the repo root). Returns what the draft stores and the publishers need."""
    slides = car["slides"]
    rels, alts, roles, record = [hook_path], [slides[0]["headline"]], ["hook"], [dict(slides[0])]
    body = slides[1:-1]
    total = len(slides) + (1 if car.get("diagram") else 0)
    with cards.accent(_accent_for(style_id)):
        n = 1
        for s in body:
            n += 1
            show_src = fact["source_name"] if fact and fact["claim"].lower() in s["body"].lower() + " " + s["headline"].lower() else None
            path = config.MEDIA / f"{date}-s{n}.jpg"
            _text_slide(s, n, total, show_src).save(path, "JPEG", quality=90, optimize=True)
            rels.append(str(path.relative_to(config.ROOT)))
            alts.append(f"Slide {n} of {total}: {s['headline']}. {s['body']}"[:1000])
            roles.append(s["role"])
            record.append(dict(s))
        if car.get("diagram"):
            n += 1
            path = config.MEDIA / f"{date}-s{n}.jpg"
            diagrams.render_for(focus, date, path)
            rels.append(str(path.relative_to(config.ROOT)))
            alts.append(f"Slide {n} of {total}: how {focus['name']} works. DM {focus['dm_keyword']} to enquire.")
            roles.append("diagram")
            record.append({"role": "diagram", "headline": f"How {focus['name']} works", "body": ""})
        n += 1
        cta = slides[-1]
        path = config.MEDIA / f"{date}-s{n}.jpg"
        _cta_slide(cta, n, total).save(path, "JPEG", quality=90, optimize=True)
        rels.append(str(path.relative_to(config.ROOT)))
        alts.append(f"Slide {n} of {total}: {cta['headline']}. {cta['body']}"[:1000])
        roles.append("cta")
        record.append(dict(cta))
    first = lambda r: roles.index(r)
    return {"flavor": car["flavor"], "fact_id": car.get("fact_id"), "checked": car.get("checked", False), "paths": rels, "alts": alts, "roles": roles,
            "bluesky": [0, first("problem"), first("solution"), len(roles) - 1], "slides": record}


def prune_media(today, days=30):
    """Slides and images are only needed while a post is pending or being published: delete media older than `days` (never a file a pending draft uses)."""
    keep = set()
    for f in config.DRAFTS.glob("*.json"):
        d = config.load_json(f, None)
        if isinstance(d, dict) and d.get("status") in ("pending", "publishing"):
            keep |= {pathlib.Path(x).name for x in (d.get("carousel") or {}).get("paths", [])}
            if (d.get("image") or {}).get("path"):
                keep.add(pathlib.Path(d["image"]["path"]).name)
    cutoff = dt.date.fromisoformat(str(today)) - dt.timedelta(days=days)
    gone = 0
    for f in config.MEDIA.glob("*"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
        if f.is_file() and m and dt.date.fromisoformat(m.group(1)) < cutoff and f.name not in keep:
            f.unlink()
            gone += 1
    return gone
