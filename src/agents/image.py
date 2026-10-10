"""Agent 4: make an image prompt (Gemma), then render it: Cloudflare FLUX first, then Gemini image, then a free fallback."""
import base64, io, os, urllib.parse
import requests
from PIL import Image
from .. import config, llm


XMP = ('<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/">'
       '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" '
       'xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-12/" '
       'Iptc4xmpExt:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"/>'
       '</rdf:RDF></x:xmpmeta><?xpacket end="w"?>').encode("utf-8")   # IPTC "AI generated" marker platforms can read


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
    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    d = llm._post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                  {"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                  {"contents": [{"parts": [{"text": img_prompt}]}], "generationConfig": {"responseModalities": ["IMAGE"]}},
                  tries=1)
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


def run(plan, focus, date, guidance=""):
    prompt = f"""Write ONE image-generation prompt (max 60 words) for a clean, modern social media square graphic.
Idea: {plan.get('image_idea')} | Topic: {plan['topic']} | Service: {focus['name']}
Strategist note: {guidance}
Style: minimal flat illustration, bold colours, lots of empty space, NO text, NO logos, NO real people's faces.
Return only the prompt."""
    img_prompt = llm.gemma(prompt).strip().strip('"')
    path = config.MEDIA / f"{date}.jpg"
    engines = ([_cloudflare] if os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ACCOUNT_ID") else []) + ([_gemini] if os.getenv("GEMINI_API_KEY") else []) + [_pollinations]
    for engine in engines:
        for _ in range(2):
            try:
                engine(img_prompt, path)
                return {"prompt": img_prompt, "path": str(path.relative_to(config.ROOT)), "engine": engine.__name__.strip("_")}
            except Exception as e:
                print(f"[image] {engine.__name__} failed: {e}")
    return {"prompt": img_prompt, "path": None}
