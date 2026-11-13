"""Agent 4: the post image. A topic-specific AI picture (Gemma writes the prompt, config/image_style.json adds the permanent quality
suffix) with the hook in real fonts on top; if no AI engine works, the designed text card; last, a plain card.
AI engines, in order (the first one that works wins; a missing key skips an engine): 1) Ideogram 3 (the default), 2) Cloudflare FLUX.1 schnell, 3) Gemini image,
4) Pollinations (free). IMAGE_ENGINE_ORDER (for example "cloudflare,ideogram") changes the order."""
import base64, datetime, io, json, os, pathlib, random, re, tempfile, urllib.parse
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
    out = re.sub(r"</?prompt>", " ", out, flags=re.I)                      # a stray tag or the six part labels must never reach the image engine
    out = re.sub(r"\b(?:subject|composition|lighting|environment|colou?r and mood|camera and texture)\s*[:\u2013\u2014-]\s*", "", out, flags=re.I)
    out = re.sub(r"\s+", " ", out).strip().strip('" ')
    if len(out) > limit:                      # cut at a word boundary, never mid-word
        out = out[:limit].rsplit(" ", 1)[0].rstrip(",;: ")
    return out


OLD_LOOK = "premium commercial photography or a polished 3D render, one strong focal subject in the upper two thirds, shallow depth of field, dramatic but natural light, rich colour with warm yellow as the accent, calm and uncluttered in the lower 40% (the headline goes there)."


DEFAULT_SUFFIX = ("Ultra-sharp 4K resolution, highly detailed, crisp focus, clean edges, "
                  "cinematic lighting with soft glow, rich contrast, high dynamic range, premium polished finish, vertical 4:5 composition.")


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


IDEOGRAM_URL = "https://api.ideogram.ai/v1/ideogram-v3/generate"
IDEOGRAM_NEGATIVE = "text, letters, words, numbers, captions, watermark, logo, signature, interface labels, distorted hands, extra fingers, blurry, low resolution"


def _ideogram(img_prompt, path):
    """Ideogram 3. The post's headline is added later in real fonts, so the picture itself must carry no text (negative prompt). Settings by env:
    IDEOGRAM_RENDERING_SPEED TURBO | DEFAULT | QUALITY (default DEFAULT), IDEOGRAM_MAGIC_PROMPT OFF | AUTO | ON (default OFF: the prompt is already engineered), IDEOGRAM_STYLE (optional style_type)."""
    key = os.environ["IDEOGRAM_API_KEY"]
    form = {"prompt": enhance(img_prompt), "rendering_speed": (os.getenv("IDEOGRAM_RENDERING_SPEED") or "DEFAULT").strip().upper(),
            "magic_prompt": (os.getenv("IDEOGRAM_MAGIC_PROMPT") or "OFF").strip().upper(), "negative_prompt": IDEOGRAM_NEGATIVE, "num_images": "1"}
    if (os.getenv("IDEOGRAM_STYLE") or "").strip():
        form["style_type"] = os.environ["IDEOGRAM_STYLE"].strip().upper()
    for ratio in ("4x5", "3x4", None):                    # 4:5 is the post shape; if the account rejects it, the nearest ratio, then none
        fields = dict(form, **({"aspect_ratio": ratio} if ratio else {}))
        r = requests.post(IDEOGRAM_URL, headers={"Api-Key": key}, files={k: (None, v) for k, v in fields.items()}, timeout=180)   # multipart/form-data
        if r.status_code not in (400, 422) or ratio is None:
            break
    r.raise_for_status()
    items = (r.json() or {}).get("data") or []
    if not items or not items[0].get("url"):
        raise RuntimeError("Ideogram returned no image")
    if items[0].get("is_image_safe") is False:
        raise RuntimeError("Ideogram flagged the image as unsafe")
    g = requests.get(items[0]["url"], timeout=120)         # the link expires, so the picture is downloaded right away
    g.raise_for_status()
    _save(g.content, path, max_side=1350)


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

SCENES = {      # a concrete, topic-specific object for when the model's prompt is unusable; no text, brands or faces; the style family sets the light
    "lead_gen": "A laptop showing a bright city map covered in glowing location pins over small shopfronts, with a cup of tea beside it",
    "chatbot": "A smartphone on a cafe counter at night, its screen lit by a stack of unread chat bubbles",
    "animated_ads": "A smartphone propped on a cafe counter playing a short colourful animated ad",
    "website": "A laptop showing a clean mobile-friendly landing page, beside a cup of tea",
    "reel_scripts": "A smartphone on a small tripod beside an open notebook and pen on a desk",
    "seo_blogs": "An open laptop beside a notebook and a cup of tea on a desk, a search results page glowing on the screen",
}

ANATOMY = """Write the prompt as ONE flowing paragraph that covers all six parts, each with concrete detail:
1. SUBJECT: the main object or hands-only action, with material, colour, size and state (for example "a matte-black laptop with a softly glowing screen", never "a nice laptop").
2. COMPOSITION: where the subject sits (upper two thirds), the angle (eye level, slightly above, low), and calm, uncluttered, soft-focus space across the lower 40% of the frame, where the headline goes.
3. LIGHTING: the key light, its direction and colour temperature, a rim light or glow, and the shadows.
4. ENVIRONMENT: a foreground, a midground and a background with depth: the surfaces, the props, the haze or reflections.
5. COLOUR AND MOOD: a named palette with ONE accent colour, and the feeling in a few words.
6. CAMERA AND TEXTURE: the lens and aperture (for example an 85mm lens at f/1.8), the depth of field, and tactile surface detail such as brushed metal, glass reflections, fine dust in the light."""


# ---------------------------------------------------------------- never the same post twice in a new colour
CHAT_CARD_COOLDOWN_DAYS = 7      # the designed chat card (bubbles on a dark panel) may appear at most once a week, whatever the accent colour
RECENT_DAYS = 21


def _recent_drafts(date, days=RECENT_DAYS):
    """Drafts of the last `days` days before `date`, oldest first."""
    try:
        today = datetime.date.fromisoformat(str(date))
    except ValueError:
        return []
    out = []
    for f in sorted(pathlib.Path(config.DRAFTS).glob("*.json")):
        d = config.load_json(f, None)
        if not isinstance(d, dict):
            continue
        try:
            age = (today - datetime.date.fromisoformat(str(d.get("date", f.stem)))).days
        except ValueError:
            continue
        if 0 < age <= days:
            out.append((age, d))
    return out


def _norm(text):
    return re.sub(r"[^a-z0-9 ]", "", str(text).lower()).strip()


def chat_card_recently_used(date):
    """True when the designed chat card (the template itself, not its colours) ran in the last CHAT_CARD_COOLDOWN_DAYS days."""
    for age, d in _recent_drafts(date, CHAT_CARD_COOLDOWN_DAYS):
        img = d.get("image") or {}
        if img.get("engine") == "designed_card" and "chat" in (img.get("style"), (img.get("spec") or {}).get("style")):
            return True
    return False


def recent_chat_texts(date):
    """The customer messages shown in recent posts (chat cards and chat bubbles alike), newest last."""
    seen = []
    for _, d in _recent_drafts(date):
        for m in ((d.get("image") or {}).get("spec") or {}).get("chat") or []:
            if m.get("text"):
                seen.append(str(m["text"]).strip())
    return seen


def recent_scenes(date, n=6):
    """The opening of the last few AI picture prompts, so a new one picks a clearly different object, place and angle."""
    out = [" ".join(str((d.get("image") or {}).get("prompt") or "").split()[:22]) for _, d in _recent_drafts(date)]
    return [x for x in out if x][-n:]


def drop_repeated_messages(spec, date):
    """Remove chat messages that already ran recently; with fewer than two left the post is no chat post at all (a plain bold card or picture)."""
    if spec.get("style") != "chat" or not spec.get("chat"):
        return spec
    seen = {_norm(t) for t in recent_chat_texts(date)}
    keep = [m for m in spec["chat"] if m.get("text") and _norm(m["text"]) not in seen]
    if len(keep) == len([m for m in spec["chat"] if m.get("text")]):
        return spec                                   # nothing repeated: leave it exactly as written
    if len(keep) < 2:
        return dict(spec, style="bold", chat=[])
    return dict(spec, chat=keep)


def pick_variant(date):
    """Visual family for this post: never the one used in the last two posts, otherwise the least used so far (so every family gets tested)."""
    vs = [v for v in (style().get("variants") or []) if v.get("id")]
    if not vs:
        return None
    used = []
    for f in sorted(config.DRAFTS.glob("*.json")):
        d = config.load_json(f, None)
        sid = ((d or {}).get("image") or {}).get("style_id") if isinstance(d, dict) and str(d.get("date", "")) < str(date) else None
        if sid:
            used.append(sid)
    pool = [v for v in vs if v["id"] not in used[-2:]] or vs
    return min(pool, key=lambda v: (used.count(v["id"]), vs.index(v)))


def recent_card_styles(date, n=2):
    """Card style ('chat', 'bold', or a picture card) of the last n drafts up to this date (today's old draft counts, so a forced re-run does not repeat it), oldest first."""
    out = []
    for f in sorted(config.DRAFTS.glob("*.json")):
        d = config.load_json(f, None)
        if isinstance(d, dict) and str(d.get("date", "")) <= str(date) and (d.get("image") or {}).get("engine"):
            im = d["image"]
            out.append("chat" if im.get("engine") == "designed_card" and im.get("style") == "chat" else "other")
    return out[-n:]


def look_text(variant, topic=""):
    """The 'Look' paragraph of the picture prompt: shared style DNA + one visual family; at most two of its elements plus ONE new element from the topic."""
    dna = (style().get("style_dna") or "").strip()
    if not variant:
        return "Look: " + (dna or OLD_LOOK)
    return (f"Look (apply to the whole picture): {dna} Today's visual family, {variant['name']}: {variant['look']}. "
            f"Use at most two of these elements: {variant['elements']}. Then add ONE new element that shows today's topic ({topic}), so this picture looks like none of the others. "
            f"Accent colour: {variant['accent']}. Copy no existing artwork.")




def scene_fallback(focus, variant=None):
    """Used when the model's prompt is unusable: the topic's scene plus the family's light, materials and camera, so even the fallback is detailed."""
    scene = SCENES.get((focus or {}).get("id"), "A laptop on a desk beside a cup of tea")
    dna = (style().get("style_dna") or "").strip() or "Premium commercial photography, one strong focal subject, calm and uncluttered in the lower 40%."
    if not variant:
        return enhance(f"{scene}. {dna}")
    bits = [f"{scene}, in the upper two thirds of the frame", variant["look"], f"Lit by {variant['lighting']}" if variant.get("lighting") else "",
            f"with {variant['elements']}", f"Surfaces: {variant['materials']}" if variant.get("materials") else "",
            f"Accent colour: {variant['accent']}", f"Shot with {variant['camera']}" if variant.get("camera") else "",
            "soft, calm, uncluttered space across the lower 40% of the frame"]
    return enhance(". ".join(x[:1].upper() + x[1:] for x in bits if x) + ".")


def _ref_block():
    refs = [r for r in (style().get("slide_reference_prompts") or []) if isinstance(r, str) and r.strip()]
    return ("\nReference prompts to match for richness, structure and lighting (style only, never copy their subjects): " + " || ".join(r.strip()[:380] for r in refs[:3])) if refs else ""


def picture_prompt(plan, focus, spec, guidance="", variant=None, recent=()):
    """Ask Gemma for ONE concrete, topic-specific scene (not an empty abstract background). The headline is added afterwards in real fonts."""
    headline = (spec or {}).get("headline") or plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    look = look_text(variant, plan["topic"])
    refs = _ref_block()
    prompt = f"""Write ONE image-generation prompt (90-125 words) for the PICTURE behind a social media post. The headline is added later as text, so the picture itself contains no text.
Headline: {headline} | Topic: {plan['topic']} | Service: {focus['name']} | Idea: {plan.get('image_idea')}
Strategist note: {guidance}
Scenes used in recent posts (choose a clearly different object, place and camera angle): {' | '.join(recent) or 'none'}

The picture must show ONE concrete, specific scene that makes the headline visible at a glance: a real object in a real situation, for example a phone playing a short animated ad on a cafe counter, a shop owner's phone lighting up with unanswered messages late at night, a laptop showing a clean booking page beside a cup of tea. Generic, not a real brand and not a claim about real client work.
{ANATOMY}
{look}{refs}
Write ONLY what should be visible, in positive wording (do not use the words no, not, without, avoid). Do not mention signs, screens with words, labels, logos, watermarks, text, aspect-ratio flags or style codes. Faces are never shown: use hands, a back view or a silhouette.
ONE subject in ONE scene. NEVER describe a layout: no left/right halves, panels, sections, grids, collages, split screens, diagrams or counts of parts. If the Idea describes a layout, keep only its object and situation.
Return ONLY the final prompt wrapped in <prompt></prompt> tags. No notes, no drafts, no explanation."""
    for attempt in (0, 1):
        ask = prompt if attempt == 0 else prompt + "\nYOUR LAST PROMPT DESCRIBED A LAYOUT OR WAS TOO SHORT. Write 90-125 words covering all six parts: subject, composition, lighting, environment, colour and mood, camera and texture."
        try:
            text = clean_prompt(llm.prompt_writer(ask), 1000)
        except Exception as e:
            print(f"[image] picture prompt failed: {e}")
            break
        if len(text.split()) >= 60 and not LAYOUT_WORDS.search(text):
            return enhance(text)
        print(f"[image] picture prompt rejected (layout or too short): {text[:90]}")
    return scene_fallback(focus, variant)


ENGINE_ORDER = "ideogram,cloudflare,gemini,pollinations"
_AVAILABLE = {      # an engine is used only when its credentials exist
    "ideogram": lambda: bool(os.getenv("IDEOGRAM_API_KEY")),
    "cloudflare": lambda: bool(os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ACCOUNT_ID")),
    "gemini": lambda: bool(os.getenv("GEMINI_API_KEY")),
    "pollinations": lambda: True,
}


def _engines():
    """Engines to try, best first: Ideogram, Cloudflare FLUX, Gemini, Pollinations. IMAGE_ENGINE_ORDER overrides the order; unknown names are ignored.
    Functions are looked up by name at call time, so a test (or a hotfix) that replaces one is honoured."""
    names = [n.strip().lower() for n in (os.getenv("IMAGE_ENGINE_ORDER") or ENGINE_ORDER).split(",")]
    order = [globals()["_" + n] for n in dict.fromkeys(names) if n in _AVAILABLE and _AVAILABLE[n]()]
    return order or [globals()["_pollinations"]]


def _ai_picture(plan, focus, spec, guidance, out_path, errors, variant=None, recent=()):
    """Write an AI picture to out_path with the first engine that works. Returns {prompt, engine}; raises if none does."""
    img_prompt = picture_prompt(plan, focus, spec, guidance, variant, recent)
    for engine in _engines():
        for _ in range(2):
            try:
                engine(img_prompt, out_path)
                return {"prompt": img_prompt, "engine": engine.__name__.strip("_"), "style_id": (variant or {}).get("id")}
            except Exception as e:
                print(f"[image] {engine.__name__} failed: {e}")
                errors.append(f"{engine.__name__.strip('_')}: {str(e)[:110]}")
    raise RuntimeError("no AI image engine worked")


def visuals_enabled():
    return os.getenv("IMAGE_VISUALS", "1") != "0"


def slide_pictures_enabled():
    return visuals_enabled() and os.getenv("SLIDE_PICTURES", "1") != "0"


def slide_scene_prompt(slide, focus, variant=None):
    """Ask Gemma for ONE scene that makes THIS slide's headline visible: a concrete subject doing the thing the headline says, in a rich environment, in today's visual family.
    A problem slide shows the struggle, a solution slide shows the same situation calm and solved. The picture never contains words, so it never labels itself."""
    role = slide.get("role")
    mood = ("the struggle in the headline made visible: someone in the middle of the tedious, messy or stuck situation it describes, with the objects and clutter that go with it"
            if role == "problem" else
            "the relief in the headline made visible: the same kind of situation now calm, organised and working, with a clear glowing sign of progress and a person at ease")
    ref_block = _ref_block()
    look = look_text(variant, slide.get("headline", ""))
    prompt = f"""Write ONE image-generation prompt (100-130 words) for a picture on a swipe-carousel slide. The slide text is added later in real fonts, so the picture contains no text.
Slide headline: {slide.get('headline')} | Slide body: {slide.get('body')} | Service: {focus['name']}

Show {mood}. Describe the foreground subject and its action (hands, objects, devices, a person seen from behind or in silhouette), then the surrounding environment and background, then the light.
So the picture reads at a glance: a viewer should understand the headline from the picture alone, e.g. for "looking up contact details by hand": a freelancer at a laptop surrounded by many open browser windows, a messy spreadsheet and sticky notes, searching listing after listing.
{ANATOMY}
The main subject sits in the upper 55% of the frame; the lower 45% stays calm and dark because a text card goes there.
{look}{ref_block}
Write ONLY what is visible, in positive wording (do not use the words no, not, without, avoid, problem, solution). Do not mention signs, screens with readable words, labels, logos, watermarks or any text. Faces are never shown (hands, back views or silhouettes only), no real brands, no aspect-ratio flags or style codes, no claims about real clients.
NEVER describe a layout: no left/right halves, panels, sections, grids, collages, split screens or diagrams.
Return ONLY the final prompt wrapped in <prompt></prompt> tags."""
    for attempt in (0, 1):
        ask = prompt if attempt == 0 else prompt + "\nYOUR LAST PROMPT WAS A LAYOUT OR TOO SHORT. Write 100-130 words covering subject, composition, lighting, environment, colour and mood, camera and texture."
        try:
            text = clean_prompt(llm.prompt_writer(ask), 1100)
        except Exception as e:
            print(f"[image] slide prompt failed: {e}")
            return None
        if len(text.split()) >= 70 and not LAYOUT_WORDS.search(text):
            return enhance(text)
        print(f"[image] slide prompt rejected (layout or too short): {text[:90]}")
    return None


def slide_picture(slide, focus, variant, out_path, errors):
    """Write a picture for one problem/solution slide to out_path. -> {"prompt", "engine"}, or None when no prompt or engine worked (the slide then keeps the blurred hook background)."""
    img_prompt = slide_scene_prompt(slide, focus, variant)
    if not img_prompt:
        errors.append("slide_prompt: none")
        return None
    for engine in _engines():
        for _ in range(2):
            try:
                engine(img_prompt, out_path)
                return {"prompt": img_prompt, "engine": engine.__name__.strip("_")}
            except Exception as e:
                print(f"[image] slide {engine.__name__} failed: {e}")
                errors.append(f"{engine.__name__.strip('_')}: {str(e)[:110]}")
    return None


def _visual_card(plan, focus, spec, guidance, path, errors, variant=None, recent=()):
    """AI picture + the hook, tag and DM pill in real fonts, 1080x1350, marked as AI-generated."""
    from . import cards
    with tempfile.TemporaryDirectory() as td:
        bg = pathlib.Path(td) / "picture.jpg"
        info = _ai_picture(plan, focus, spec, guidance, bg, errors, variant, recent)
        im = cards.compose_visual(spec, bg)
    _write_jpeg(im, path, ai=True)
    return {"prompt": info["prompt"], "path": str(path.relative_to(config.ROOT)), "engine": "visual:" + info["engine"], "style": "visual",
            "ai_generated": True, "spec": spec, "errors": errors[-4:], "style_id": info.get("style_id")}


def run(plan, focus, date, guidance=""):
    """Today's visual family decides the look of EVERY card type: the AI picture's style and the card's accent colour (highlight, glow, DM button)."""
    from . import cards
    variant = pick_variant(date)
    with cards.accent((variant or {}).get("accent_rgb")):
        return _run(plan, focus, date, guidance, variant)


def _run(plan, focus, date, guidance, variant):
    """1) AI picture + hook text (skipped for chat cards, which are already a specific visual, or when IMAGE_VISUALS=0)
    2) designed card  3) plain AI picture, only if 1 did not already try the engines  4) plain text card."""
    path = config.MEDIA / f"{date}.jpg"
    errors, spec, ai_tried = [], None, False
    recent = recent_scenes(date)
    try:
        from . import cards
        cards.AVOID_CHAT = tuple(recent_chat_texts(date))
        spec = drop_repeated_messages(cards.make_spec(plan, focus, guidance), date)
        if spec.get("style") == "chat" and ("chat" in recent_card_styles(date) or chat_card_recently_used(date)):
            # The chat card ran in the last two posts (a forced re-run counts too) or this week. Never repeat it in another colour:
            # keep the chat idea as a few floating bubbles on a fresh AI scene instead.
            spec["chat_overlay"] = True
    except Exception as e:
        print(f"[image] card copy failed: {e}")
        errors.append(f"card_copy: {str(e)[:110]}")
    if spec and (spec.get("style") != "chat" or spec.get("chat_overlay")) and visuals_enabled():
        ai_tried = True
        try:
            return _visual_card(plan, focus, spec, guidance, path, errors, variant, recent)
        except Exception as e:
            print(f"[image] visual card failed: {e}")
            errors.append(f"visual_card: {str(e)[:110]}")
    if spec:
        try:
            from . import cards
            if spec.pop("chat_overlay", False):          # the AI picture failed: a bold card, still not the chat card again
                spec = dict(spec, style="bold", chat=[])
            cards.render(spec, path)
            return {"prompt": None, "path": str(path.relative_to(config.ROOT)), "engine": "designed_card",
                    "style": spec.get("style"), "ai_generated": False, "spec": spec, "errors": errors[-4:],
                    "style_id": (variant or {}).get("id")}
        except Exception as e:
            print(f"[image] designed card failed: {e}")
            errors.append(f"designed_card: {str(e)[:110]}")
    img_prompt = None
    if not ai_tried:
        try:
            info = _ai_picture(plan, focus, spec, guidance, path, errors, variant, recent)
            return {"prompt": info["prompt"], "path": str(path.relative_to(config.ROOT)), "engine": info["engine"], "errors": errors[-4:], "style_id": info.get("style_id")}
        except Exception as e:
            img_prompt = None
            errors.append(f"ai_picture: {str(e)[:110]}")
    try:
        _card(plan, path)
        return {"prompt": img_prompt, "path": str(path.relative_to(config.ROOT)), "engine": "text_card", "errors": errors[-4:]}
    except Exception as e:
        errors.append(f"text_card: {str(e)[:80]}")
    return {"prompt": img_prompt, "path": None, "errors": errors[-4:]}
