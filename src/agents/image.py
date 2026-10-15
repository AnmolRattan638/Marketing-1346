"""Agent 4: the post image. A topic-specific AI picture (Gemma writes the prompt, config/image_style.json adds the permanent quality
suffix) with the hook in real fonts on top; if no AI engine works, the designed text card; last, a plain card."""
import base64, io, json, os, pathlib, random, re, tempfile, urllib.parse
import requests
from PIL import Image
from .. import config, llm


XMP = ('<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/">'
       '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" '
       'xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-12/" '
       'Iptc4xmpExt:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"/>'
       '</rdf:RDF></x:xmpmeta><?xpacket end="w"?>').encode("utf-8")   # IPTC "AI generated" marker platforms can read


def clean_prompt(text, limit=900):
    """Some models leak their reasoning before the answer. Keep only the real prompt, on one line, capped."""
    tagged = re.findall(r"<prompt>(.*?)</prompt>", text, re.S | re.I)
    if tagged:
        out = tagged[-1]
    else:
        quoted = re.findall(r'"([^"\n]{80,}?)"', text)
        if quoted:
            out = quoted[-1]
        else:
            paras = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
            out = paras[-1] if paras else text
    out = re.sub(r"^[\s*\-\d.)]+", "", re.sub(r"\s+", " ", out).strip())
    return out.strip('" ')[:limit]


DEFAULT_SUFFIX = ("Ultra-sharp 4K resolution, highly detailed, crisp focus, clean edges, professional commercial lighting, "
                  "rich natural colour, high dynamic range, premium polished finish, vertical 4:5 composition.")


def style():
    try:
        return json.loads((config.ROOT / "config" / "image_style.json").read_text())
    except Exception:
        return {}


def enhance(prompt):
    """Append the permanent resolution/quality suffix. Every engine calls this, so no image is generated without it. Idempotent."""
    suffix = (style().get("quality_suffix") or DEFAULT_SUFFIX).strip()
    p = re.sub(r"\s+", " ", prompt or "").strip()
    if suffix.rstrip(".").lower() in p.lower():          # already there (compare without the final period, which the join below may move)
        return p
    return f"{p.rstrip('.')}. {suffix}" if p else suffix


def _write_jpeg(im, path, ai=True):
    """Best quality that still fits under 900 KB (Bluesky's limit); 4:4:4 chroma keeps text edges crisp."""
    for q in (92, 88, 83, 77, 70, 62):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, subsampling=0, optimize=True, **({"xmp": XMP} if ai else {}))
        if buf.tell() < 900_000:
            break
    path.write_bytes(buf.getvalue())


def _save(data, path, ai=True, max_side=1080):
    """Normalise any engine's output to an RGB JPEG (Instagram needs JPEG, Bluesky limits size)."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    _write_jpeg(im, path, ai)


def _cloudflare(img_prompt, path):
    acc, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
    url, img_prompt = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/flux-1-schnell", enhance(img_prompt)
    for steps in (8, 4):                                   # 8 = the model's maximum (best detail); 4 if the account rejects it
        r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json={"prompt": img_prompt, "steps": steps}, timeout=120)
        if r.status_code != 400 or steps == 4:
            break
    r.raise_for_status()
    _save(base64.b64decode(r.json()["result"]["image"]), path, max_side=1350)


def _gemini(img_prompt, path):
    model = os.getenv("GEMINI_IMAGE_MODEL") or "gemini-3.1-flash-image"
    img_prompt = enhance(img_prompt)
    url = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
    hdr = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}

    def call(m):
        body = {"contents": [{"parts": [{"text": img_prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "4:5"}}}
        try:
            return llm._post(url.format(m), hdr, body, tries=1)
        except RuntimeError as e:
            if "HTTP 400" not in str(e):
                raise
            del body["generationConfig"]["imageConfig"]    # this model does not take an aspect ratio: ask again without it
            return llm._post(url.format(m), hdr, body, tries=1)
    try:
        d = call(model)
    except RuntimeError as e:
        alt = llm._discover_gemini("image") if "HTTP 404" in str(e) else None
        if not alt or alt == model:
            raise
        print(f"[image] {model} unavailable; using {alt}")
        d = call(alt)
    for part in d["candidates"][0]["content"]["parts"]:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            _save(base64.b64decode(inline["data"]), path, max_side=1350)
            return
    raise RuntimeError("Gemini returned no image")


def _pollinations(img_prompt, path):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(enhance(img_prompt))
           + f"?width=1080&height=1350&nologo=true&enhance=false&seed={random.randint(1, 999999)}")
    r = requests.get(url, timeout=150)
    if not (r.ok and r.headers.get("content-type", "").startswith("image")):
        raise RuntimeError("pollinations failed")
    _save(r.content, path, max_side=1350)


def _card(plan, path):
    """Plain brand text card with the hook, used when no AI engine works (so Instagram still gets an image)."""
    from PIL import ImageDraw, ImageFont
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    im = Image.new("RGB", (1080, 1080), (11, 18, 32))
    d = ImageDraw.Draw(im)
    for size in (84, 70, 58, 48):
        font = ImageFont.load_default(size=size)
        lines, cur = [], ""
        for w in hook.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= 880:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= 6:
            break
    lh = int(size * 1.3)
    y = (1080 - lh * len(lines)) // 2 - 20
    d.rectangle([100, y - 50, 300, y - 42], fill=(212, 175, 55))
    for ln in lines:
        d.text((100, y), ln, font=font, fill=(255, 255, 255))
        y += lh
    d.text((100, 960), "Anmol | AR Designs", font=ImageFont.load_default(size=36), fill=(212, 175, 55))
    im.save(path, "JPEG", quality=90)    # no AI-generated marker: this is not AI imagery


# An image model draws ONE scene. A prompt that describes a layout ("Left: ... Right: a panel divided into four sections") is ignored
# or turned into a blurry gradient, which is what produced the empty grey panel on 2026-10-15. Such prompts are rejected.
LAYOUT_WORDS = re.compile(r"\b(?:left|right|top|bottom)\s*:|\bpanels?\b|\bdivided\b|\bsections?\b|\bgrid\b|\bsplit[- ]?screen\b|\bcollage\b|"
                          r"\bcolumns?\b|\binfographic\b|\bdiagram\b|\bflowchart\b|\b(?:two|three|four|five|six|2|3|4|5|6)\s+(?:equal\s+)?(?:parts|sections|panels|columns|boxes|cards|steps)\b", re.I)

SCENES = {      # a concrete, topic-specific picture used when the model's prompt is unusable; no text, brands or faces
    "lead_gen": "A laptop on a wooden desk showing a bright city map covered in glowing yellow location pins over small shopfronts, a cup of tea beside it, warm window light",
    "chatbot": "A smartphone on a cafe counter at night, its screen lit by a stack of unread chat bubbles, warm lamp light",
    "animated_ads": "A smartphone propped on a cafe counter playing a short colourful animated ad, warm afternoon light",
    "website": "A laptop on a tidy desk showing a clean mobile-friendly landing page, beside a cup of tea in warm window light",
    "reel_scripts": "A smartphone on a small tripod beside an open notebook and pen on a wooden desk, soft window light",
    "seo_blogs": "An open laptop beside a notebook and a cup of tea on a desk, a search results page glowing on the screen",
}


def scene_fallback(focus):
    scene = SCENES.get((focus or {}).get("id"), "A laptop on a wooden desk beside a cup of tea in warm window light")
    return enhance(f"{scene}. Premium commercial photography, one strong focal subject in the upper two thirds, shallow depth of field, "
                   "rich colour with a warm yellow accent, calm and uncluttered in the lower 40%.")


def picture_prompt(plan, focus, spec, guidance=""):
    """Ask Gemma for ONE concrete, topic-specific scene (not an empty abstract background). The headline is added afterwards in real fonts."""
    headline = (spec or {}).get("headline") or plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    prompt = f"""Write ONE image-generation prompt (45-70 words) for the PICTURE behind a social media post. The headline is added later as text, so the picture itself contains no text.
Headline: {headline} | Topic: {plan['topic']} | Service: {focus['name']} | Idea: {plan.get('image_idea')}
Strategist note: {guidance}

The picture must show ONE concrete, specific scene that makes the headline visible at a glance: a real object in a real situation, for example a phone playing a short animated ad on a cafe counter, a shop owner's phone lighting up with unanswered messages late at night, a laptop showing a clean booking page beside a cup of tea. Generic, not a real brand and not a claim about real client work.
Look: premium commercial photography or a polished 3D render, one strong focal subject in the upper two thirds, shallow depth of field, dramatic but natural light, rich colour with warm yellow as the accent, calm and uncluttered in the lower 40% (the headline goes there).
Write ONLY what should be visible, in positive wording (do not use the words no, not, without, avoid). Do not mention signs, screens with words, labels, logos, watermarks or any text. No close-up faces.
ONE subject in ONE scene. NEVER describe a layout: no left/right halves, panels, sections, grids, collages, split screens, diagrams or counts of parts. If the Idea describes a layout, keep only its object and situation.
Return ONLY the final prompt wrapped in <prompt></prompt> tags. No notes, no drafts, no explanation."""
    for attempt in (0, 1):
        ask = prompt if attempt == 0 else prompt + "\nYOUR LAST PROMPT DESCRIBED A LAYOUT OR WAS TOO VAGUE. Describe ONE real object in ONE real place instead."
        try:
            text = clean_prompt(llm.gemma(ask))
        except Exception as e:
            print(f"[image] picture prompt failed: {e}")
            break
        if len(text.split()) >= 12 and not LAYOUT_WORDS.search(text):
            return enhance(text)
        print(f"[image] picture prompt rejected (layout or too short): {text[:90]}")
    return scene_fallback(focus)


def _engines():
    return (([_cloudflare] if os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ACCOUNT_ID") else [])
            + ([_gemini] if os.getenv("GEMINI_API_KEY") else []) + [_pollinations])


def _ai_picture(plan, focus, spec, guidance, out_path, errors):
    """Write an AI picture to out_path with the first engine that works. Returns {prompt, engine}; raises if none does."""
    img_prompt = picture_prompt(plan, focus, spec, guidance)
    for engine in _engines():
        for _ in range(2):
            try:
                engine(img_prompt, out_path)
                return {"prompt": img_prompt, "engine": engine.__name__.strip("_")}
            except Exception as e:
                print(f"[image] {engine.__name__} failed: {e}")
                errors.append(f"{engine.__name__.strip('_')}: {str(e)[:110]}")
    raise RuntimeError("no AI image engine worked")


def visuals_enabled():
    return os.getenv("IMAGE_VISUALS", "1") != "0"


def _visual_card(plan, focus, spec, guidance, path, errors):
    """AI picture + the hook, tag and DM pill in real fonts, 1080x1350, marked as AI-generated."""
    from . import cards
    with tempfile.TemporaryDirectory() as td:
        bg = pathlib.Path(td) / "picture.jpg"
        info = _ai_picture(plan, focus, spec, guidance, bg, errors)
        im = cards.compose_visual(spec, bg)
    _write_jpeg(im, path, ai=True)
    return {"prompt": info["prompt"], "path": str(path.relative_to(config.ROOT)), "engine": "visual:" + info["engine"], "style": "visual",
            "ai_generated": True, "spec": spec, "errors": errors[-4:]}


def run(plan, focus, date, guidance=""):
    """1) AI picture + hook text (skipped for chat cards, which are already a specific visual, or when IMAGE_VISUALS=0)
    2) designed card  3) plain AI picture, only if 1 did not already try the engines  4) plain text card."""
    path = config.MEDIA / f"{date}.jpg"
    errors, spec, ai_tried = [], None, False
    try:
        from . import cards
        spec = cards.make_spec(plan, focus, guidance)
    except Exception as e:
        print(f"[image] card copy failed: {e}")
        errors.append(f"card_copy: {str(e)[:110]}")
    if spec and spec.get("style") != "chat" and visuals_enabled():
        ai_tried = True
        try:
            return _visual_card(plan, focus, spec, guidance, path, errors)
        except Exception as e:
            print(f"[image] visual card failed: {e}")
            errors.append(f"visual_card: {str(e)[:110]}")
    if spec:
        try:
            from . import cards
            cards.render(spec, path)
            return {"prompt": None, "path": str(path.relative_to(config.ROOT)), "engine": "designed_card",
                    "style": spec.get("style"), "ai_generated": False, "spec": spec, "errors": errors[-4:]}
        except Exception as e:
            print(f"[image] designed card failed: {e}")
            errors.append(f"designed_card: {str(e)[:110]}")
    img_prompt = None
    if not ai_tried:
        try:
            info = _ai_picture(plan, focus, spec, guidance, path, errors)
            return {"prompt": info["prompt"], "path": str(path.relative_to(config.ROOT)), "engine": info["engine"], "errors": errors[-4:]}
        except Exception as e:
            img_prompt = None
            errors.append(f"ai_picture: {str(e)[:110]}")
    try:
        _card(plan, path)
        return {"prompt": img_prompt, "path": str(path.relative_to(config.ROOT)), "engine": "text_card", "errors": errors[-4:]}
    except Exception as e:
        errors.append(f"text_card: {str(e)[:80]}")
    return {"prompt": img_prompt, "path": None, "errors": errors[-4:]}
