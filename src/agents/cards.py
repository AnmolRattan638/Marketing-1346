"""Designed post images (no AI imagery): a bold headline card or a chat-mock card, 1080x1350 (4:5).

The LLM only supplies the words; the layout is deterministic, so the result is always readable and on brand.
"""
import pathlib
import re
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from .. import llm

W, H = 1080, 1350
BG, PANEL, WHITE, MUTED = (9, 12, 20), (21, 27, 40), (255, 255, 255), (168, 176, 192)
ACCENT = (255, 214, 10)
FONTS = pathlib.Path(__file__).resolve().parents[2] / "assets" / "fonts"


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


def _wrap(d, words, fnt, maxw):
    """words: list of (text, color). Returns lines, each a list of (text, color)."""
    lines, cur, curw = [], [], 0
    space = d.textlength(" ", font=fnt)
    for w, c in words:
        ww = d.textlength(w, font=fnt)
        add = ww if not cur else ww + space
        if cur and curw + add > maxw:
            lines.append(cur)
            cur, curw = [(w, c)], ww
        else:
            cur.append((w, c))
            curw += add
    if cur:
        lines.append(cur)
    return lines


def _color_words(text, highlight):
    hl = {re.sub(r"\W", "", h).lower() for h in highlight or [] if h}
    return [(w, ACCENT if re.sub(r"\W", "", w).lower() in hl and re.sub(r"\W", "", w) else WHITE) for w in text.split()]


def _draw_lines(d, lines, fnt, x, y, lh):
    space = d.textlength(" ", font=fnt)
    for ln in lines:
        cx = x
        for w, c in ln:
            d.text((cx, y), w, font=fnt, fill=c)
            cx += d.textlength(w, font=fnt) + space
        y += lh
    return y


def _headline(d, text, highlight, x, y, maxw, max_h, sizes, max_lines):
    for size in sizes:
        fnt = font("ExtraBold", size)
        lines = _wrap(d, _color_words(text, highlight), fnt, maxw)
        lh = int(size * 1.16)
        if len(lines) <= max_lines and len(lines) * lh <= max_h:
            break
    return _draw_lines(d, lines, fnt, x, y, lh), len(lines) * lh


def _base():
    im = Image.new("RGB", (W, H), BG)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.ellipse([W - 520, -330, W + 330, 520], fill=ACCENT + (30,))      # soft accent glow, top right
    od.ellipse([-300, H - 420, 420, H + 300], fill=ACCENT + (14,))      # and bottom left
    im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    return im, ImageDraw.Draw(im)


def _top_and_footer(d, tag, cta):
    f = font("SemiBold", 27)
    tw = d.textlength(tag, font=f)
    d.rounded_rectangle([70, 70, 70 + tw + 56, 70 + 58], radius=29, outline=ACCENT, width=3)
    d.text((98, 83), tag, font=f, fill=ACCENT)
    d.text((70, H - 108), "Anmol  |  AR Designs", font=font("Medium", 30), fill=MUTED)
    if cta:
        cf = font("ExtraBold", 40)
        cw = d.textlength(cta, font=cf)
        x1, y1 = W - 70, H - 150
        d.rounded_rectangle([x1 - cw - 70, y1, x1, y1 + 84], radius=42, fill=ACCENT)
        d.text((x1 - cw - 35, y1 + 14), cta, font=cf, fill=(10, 10, 10))


def render_bold(spec, path):
    im, d = _base()
    _top_and_footer(d, spec.get("tag") or "FOR EVERY SMALL BUSINESS", spec.get("cta"))
    y_end, h = _headline(d, spec["headline"], spec.get("highlight"), 70, 250, 940, 640, (132, 120, 108, 96, 84), 7)
    d.rounded_rectangle([70, y_end + 36, 70 + 150, y_end + 46], radius=5, fill=ACCENT)
    if spec.get("sub"):
        sf = font("Medium", 44)
        lines = _wrap(d, [(w, MUTED) for w in spec["sub"].split()], sf, 900)[:4]
        _draw_lines(d, lines, sf, 70, y_end + 86, 62)
    im.save(path, "JPEG", quality=92)


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def compose_visual(spec, bg_path):
    """An AI picture as a full-bleed 4:5 background, darkened behind the text, with the hook, tag and DM pill in real fonts.
    Image models garble lettering, so they are never asked for text. Returns a 1080x1350 RGB image."""
    bg = Image.open(bg_path).convert("RGB")
    scale = max(W / bg.width, H / bg.height)                           # cover-fit, then centre-crop to 4:5
    bg = bg.resize((round(bg.width * scale), round(bg.height * scale)), Image.LANCZOS)
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    im = bg.crop((left, top, left + W, top + H))
    if scale > 1.05:                                                   # undo some of the softness of upscaling
        im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=70, threshold=3))
    # measure the text first, so the dark scrim can be anchored to where the headline really starts
    sizes = (112, 104, 96, 88, 80, 72)
    probe = ImageDraw.Draw(Image.new("RGB", (W, H)))
    _, h = _headline(probe, spec["headline"], spec.get("highlight"), 70, 0, 940, 520, sizes, 5)
    sub_lines = []
    if spec.get("sub"):
        sub_lines = _wrap(probe, [(w, MUTED) for w in spec["sub"].split()], font("Medium", 40), 900)[:2]
    block = h + 58 + (len(sub_lines) * 56 + 22 if sub_lines else 0)
    y0 = max(300, 1150 - block)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for y in range(H):                                                 # light at the top for the tag, strong from just above the headline down
        a = max(int(218 * _smooth((y - (y0 - 400)) / 380)), int(150 * (1 - _smooth(y / 300))), 24)
        od.line([(0, y), (W, y)], fill=(5, 8, 16, a))
    im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(im)
    _top_and_footer(d, spec.get("tag") or "FOR EVERY SMALL BUSINESS", spec.get("cta"))
    y_end, _ = _headline(d, spec["headline"], spec.get("highlight"), 70, y0, 940, 520, sizes, 5)
    d.rounded_rectangle([70, y_end + 34, 70 + 150, y_end + 44], radius=5, fill=ACCENT)
    if sub_lines:
        _draw_lines(d, sub_lines, font("Medium", 40), 70, y_end + 72, 56)
    return im


def _bubble_lines(d, text, fnt, maxw):
    return _wrap(d, [(w, WHITE) for w in text.split()], fnt, maxw)


def _bubble_height(lines, size, time):
    return len(lines) * int(size * 1.36) + 26 + (30 if time else 0)


def _bubble(d, x_left, x_right, y, text, side, fnt, size, tfnt, time, maxw=600):
    lines = _bubble_lines(d, text, fnt, maxw)
    lh = int(size * 1.36)
    sp = d.textlength(" ", font=fnt)
    bw = max(sum(d.textlength(w, font=fnt) for w, _ in ln) + sp * (len(ln) - 1) for ln in lines) + 56
    bh = _bubble_height(lines, size, time)
    x0 = x_left if side == "left" else x_right - bw
    d.rounded_rectangle([x0, y, x0 + bw, y + bh], radius=28, fill=(38, 46, 62) if side == "left" else (0, 104, 88))
    _draw_lines(d, lines, fnt, x0 + 28, y + 12, lh)
    if time:
        d.text((x0 + bw - 26 - d.textlength(time, font=tfnt), y + bh - 36), time, font=tfnt, fill=(150, 160, 178))
    return y + bh + 16


def render_chat(spec, path):
    im, d = _base()
    _top_and_footer(d, spec.get("tag") or "FOR EVERY SMALL BUSINESS", spec.get("cta"))
    y_end, _ = _headline(d, spec["headline"], spec.get("highlight"), 70, 215, 940, 330, (88, 80, 72, 64), 4)
    top, bottom = y_end + 30, H - 262
    d.rounded_rectangle([70, top, W - 70, bottom], radius=44, fill=PANEL, outline=(52, 60, 78), width=2)
    d.ellipse([105, top + 26, 163, top + 84], fill=(70, 80, 102))
    d.text((120, top + 34), "C", font=font("SemiBold", 32), fill=WHITE)
    d.text((183, top + 22), spec.get("chat_name") or "Customer", font=font("SemiBold", 30), fill=WHITE)
    d.text((183, top + 58), "typing...", font=font("Medium", 23), fill=(120, 200, 150))
    d.rounded_rectangle([W - 110 - 150, top + 32, W - 110, top + 72], radius=20, fill=(60, 52, 10))
    d.text((W - 110 - 150 + 24, top + 39), "EXAMPLE", font=font("SemiBold", 21), fill=ACCENT)
    msgs = [m for m in (spec.get("chat") or []) if m.get("text")][:4]
    avail = bottom - (top + 108) - 14
    chosen = None
    for size in (36, 33, 30, 27):
        fnt = font("Medium", size)
        for n in range(len(msgs), 0, -1):
            tot = sum(_bubble_height(_bubble_lines(d, m["text"], fnt, 600), size, m.get("time")) + 16 for m in msgs[:n])
            if tot <= avail:
                chosen = (size, n)
                break
        if chosen and chosen[1] == len(msgs):
            break
    size, n = chosen or (27, 1)
    bf, tf = font("Medium", size), font("Medium", max(20, size - 11))
    y = top + 108
    for m in msgs[:n]:
        y = _bubble(d, 105, W - 105, y, m["text"], "right" if m.get("side") == "right" else "left", bf, size, tf, m.get("time"))
    if spec.get("sub"):
        d.text((70, bottom + 22), spec["sub"][:44], font=font("SemiBold", 34), fill=(255, 120, 110))
    im.save(path, "JPEG", quality=92)


def render(spec, path):
    (render_chat if spec.get("style") == "chat" and spec.get("chat") else render_bold)(spec, path)


# ----------------------------------------------------------------- the words
CTA_BY_SERVICE = {"chatbot": "BOT", "animated_ads": "ADS", "lead_gen": "LEADS", "website": "SITE",
                  "reel_scripts": "SCRIPT", "seo_blogs": "BLOG"}


def make_spec(plan, focus, guidance=""):
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    kw = focus.get("dm_keyword") or CTA_BY_SERVICE.get(focus.get("id"), "HI")
    prompt = f"""Design copy for ONE square social media image (Instagram/LinkedIn).
Topic: {plan['topic']} | Hook: {hook} | Service: {focus['name']}
Strategist note: {guidance}

Rules:
- Universal: any small business owner should relate. Never one niche. No demos, samples or claims of work done.
- "headline": 4-9 words, plain English, stops the scroll (a pain, a question or a sharp truth). Based on the hook. No absolute claims (no "kill", "guaranteed", "always", "never", "eliminates").
- "highlight": 1-3 words from the headline to show in yellow.
- "sub": one short supporting line, max 12 words (or empty).
- "style": "chat" ONLY if the headline itself is about customers messaging, waiting for a reply or unanswered enquiries; otherwise "bold" (forms, ads, websites, leads, SEO are "bold").
- If style is "chat": "chat" = 2-3 messages of a plausible customer-to-business conversation as an illustrative EXAMPLE
  [{{"side":"left","text":"max 9 words","time":"1:47 AM"}}, ...] (at most 3 messages); "sub" = the cost of the delay, max 6 words (e.g. "No reply by morning.").
Return JSON: {{"style": "bold|chat", "headline": "...", "highlight": ["..."], "sub": "...", "chat": []}}"""
    try:
        spec = llm.ask_json(llm.gemma, prompt, "You are a sharp social media art director. Short, plain, honest copy.")
        if not str(spec.get("headline", "")).strip():
            raise ValueError("no headline")
    except Exception:
        spec = {"style": "bold", "headline": hook, "highlight": [], "sub": ""}
    if not spec.get("highlight"):
        words = [w for w in str(spec["headline"]).split() if len(re.sub(r"\W", "", w)) > 3]
        spec["highlight"] = words[-1:]
    spec["cta"] = f'DM "{kw}"'
    spec["tag"] = "FOR EVERY SMALL BUSINESS" if focus.get("id") != "lead_gen" else "FOR FREELANCERS & AGENCIES"
    return spec
