"""Agent 4: make an image prompt and render it (Gemma + free Pollinations endpoint, best effort)."""
import urllib.parse
import requests
from .. import config, llm


def run(plan, focus, date):
    prompt = f"""Write ONE image-generation prompt (max 60 words) for a clean, modern social media square graphic.
Idea: {plan.get('image_idea')} | Topic: {plan['topic']} | Service: {focus['name']}
Style: minimal flat illustration, bold colours, lots of empty space, NO text, NO logos, NO real people's faces.
Return only the prompt."""
    img_prompt = llm.gemma(prompt).strip().strip('"')
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(img_prompt)
           + "?width=1080&height=1080&nologo=true")
    path = config.MEDIA / f"{date}.jpg"
    for _ in range(2):
        try:
            r = requests.get(url, timeout=150)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                path.write_bytes(r.content)
                return {"prompt": img_prompt, "path": str(path.relative_to(config.ROOT))}
        except requests.RequestException:
            pass
    return {"prompt": img_prompt, "path": None}
