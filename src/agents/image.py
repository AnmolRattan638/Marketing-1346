"""Agent 4: make an image prompt (Gemma), then render it: Cloudflare FLUX first, then Gemini image, then a free fallback."""
import base64, io, os, re, urllib.parse
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


def _save(data, path):
    """Normalise any engine's output to a <900 KB RGB JPEG (Instagram needs JPEG, Bluesky limits size)."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((1080, 1080))
    for q in (90, 80, 70, 60):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, xmp=XMP)
        if buf.tell() < 900_000:
            break
    path.write_bytes(buf.getvalue())


def _cloudflare(img_prompt, path):
    acc, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                      headers={"Authorization": f"Bearer {tok}"}, json={"prompt": img_prompt, "steps": 4}, timeout=120)
    r.raise_for_status()
    _save(base64.b64decode(r.json()["result"]["image"]), path)


def _gemini(img_prompt, path):
    model = os.getenv("GEMINI_IMAGE_MODEL") or "gemini-3.1-flash-image"
    body = {"contents": [{"parts": [{"text": img_prompt}]}], "generationConfig": {"responseModalities": ["IMAGE"]}}
    url = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
    hdr = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    try:
        d = llm._post(url.format(model), hdr, body, tries=1)
    except RuntimeError as e:
        alt = llm._discover_gemini("image") if "HTTP 404" in str(e) else None
        if not alt or alt == model:
            raise
        print(f"[image] {model} unavailable; using {alt}")
        d = llm._post(url.format(alt), hdr, body, tries=1)
    for part in d["candidates"][0]["content"]["parts"]:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            _save(base64.b64decode(inline["data"]), path)
            return
    raise RuntimeError("Gemini returned no image")


def _pollinations(img_prompt, path):
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(img_prompt) + "?width=1080&height=1080&nologo=true"
    r = requests.get(url, timeout=150)
    if not (r.ok and r.headers.get("content-type", "").startswith("image")):
        raise RuntimeError("pollinations failed")
    _save(r.content, path)


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


def run(plan, focus, date, guidance=""):
    prompt = f"""Write ONE image-generation prompt (max 60 words) for a clean, modern social media square graphic.
Idea: {plan.get('image_idea')} | Topic: {plan['topic']} | Service: {focus['name']}
Strategist note: {guidance}
Style: minimal flat illustration, bold colours, lots of empty space, NO text, NO logos, NO real people's faces.
Return ONLY the final prompt wrapped in <prompt></prompt> tags. No notes, no drafts, no explanation."""
    img_prompt = clean_prompt(llm.gemma(prompt))
    path = config.MEDIA / f"{date}.jpg"
    engines = ([_cloudflare] if os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ACCOUNT_ID") else []) + ([_gemini] if os.getenv("GEMINI_API_KEY") else []) + [_pollinations]
    errors = []
    for engine in engines:
        for _ in range(2):
            try:
                engine(img_prompt, path)
                return {"prompt": img_prompt, "path": str(path.relative_to(config.ROOT)), "engine": engine.__name__.strip("_")}
            except Exception as e:
                print(f"[image] {engine.__name__} failed: {e}")
                errors.append(f"{engine.__name__.strip('_')}: {str(e)[:110]}")
    try:
        _card(plan, path)
        return {"prompt": img_prompt, "path": str(path.relative_to(config.ROOT)), "engine": "text_card", "errors": errors[-4:]}
    except Exception as e:
        errors.append(f"text_card: {str(e)[:80]}")
    return {"prompt": img_prompt, "path": None, "errors": errors[-4:]}
