"""Agent 4: make an image prompt (Gemma), then render it with Cloudflare Workers AI (FLUX), else a free fallback."""
import base64, os, urllib.parse
import requests
from .. import config, llm


def _cloudflare(img_prompt, path):
    acc, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                      headers={"Authorization": f"Bearer {tok}"}, json={"prompt": img_prompt, "steps": 4}, timeout=120)
    r.raise_for_status()
    path.write_bytes(base64.b64decode(r.json()["result"]["image"]))   # JPEG, 1024x1024


def _pollinations(img_prompt, path):
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(img_prompt) + "?width=1080&height=1080&nologo=true"
    r = requests.get(url, timeout=150)
    if not (r.ok and r.headers.get("content-type", "").startswith("image")):
        raise RuntimeError("pollinations failed")
    path.write_bytes(r.content)


def run(plan, focus, date):
    prompt = f"""Write ONE image-generation prompt (max 60 words) for a clean, modern social media square graphic.
Idea: {plan.get('image_idea')} | Topic: {plan['topic']} | Service: {focus['name']}
Style: minimal flat illustration, bold colours, lots of empty space, NO text, NO logos, NO real people's faces.
Return only the prompt."""
    img_prompt = llm.gemma(prompt).strip().strip('"')
    path = config.MEDIA / f"{date}.jpg"
    engines = ([_cloudflare] if os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ACCOUNT_ID") else []) + [_pollinations]
    for engine in engines:
        for _ in range(2):
            try:
                engine(img_prompt, path)
                return {"prompt": img_prompt, "path": str(path.relative_to(config.ROOT)), "engine": engine.__name__.strip("_")}
            except Exception as e:
                print(f"[image] {engine.__name__} failed: {e}")
    return {"prompt": img_prompt, "path": None}
