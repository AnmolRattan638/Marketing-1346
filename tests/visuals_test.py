"""Offline tests: short bold/CAPS captions and the picture pipeline (permanent quality suffix on every engine, picture + real text,
fallback order). No network, no keys."""
import base64, io, json, os, pathlib, sys, tempfile, unicodedata, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from PIL import Image
from src import captions as C, config, llm
from src.agents import cards, image, writer

# ------------------------------------------------------------------ captions: bold letters
assert C.bold("A") == "\U0001D5D4" == "𝗔" and C.bold("a") == "𝗮" and C.bold("5") == "𝟱"
assert C.bold("DM → आप !") == "𝗗𝗠 → आप !", "only A-Z a-z 0-9 change; arrows, Devanagari and punctuation do not"
assert unicodedata.normalize("NFKC", C.bold("Hello 2026")) == "Hello 2026"

raw = "**STOP LOSING LEADS TO SLOW REPLIES**\n\n→ Customers message at 11 pm.\n→ No reply means a **LOST** sale.\n\n\n\nDM **ADS** and tell me what you sell.\n\n#SmallBusinessIndia #Ads"
out = C.finalize(raw, bold_on=True)
assert "**" not in out and out.startswith(C.bold("STOP LOSING LEADS TO SLOW REPLIES")) and C.bold("LOST") in out and "DM " + C.bold("ADS") in out
assert "\n\n\n" not in out and out.endswith("#SmallBusinessIndia #Ads"), "tidy blank lines; hashtags stay plain"
assert C.finalize(out, bold_on=True) == out, "idempotent: running it twice changes nothing"

plain = C.finalize(raw, bold_on=False)
assert "**" not in plain and "STOP LOSING LEADS TO SLOW REPLIES" in plain and not any(0x1D5D4 <= ord(ch) <= 0x1D7FF for ch in plain), "UNICODE_BOLD=0 keeps the CAPITALS, drops the bold"
os.environ["UNICODE_BOLD"] = "0"
assert "**" not in C.finalize("**HOOK** line") and C.bold("HOOK") not in C.finalize("**HOOK** line")
del os.environ["UNICODE_BOLD"]

many = " ".join(f"**W{i}**" for i in range(10))
res = C.finalize(many, bold_on=True)
assert sum(1 for ch in res if 0x1D5D4 <= ord(ch) <= 0x1D7FF) and res.count(C.bold("W0")) == 1 and "W9" in res and C.bold("W9") not in res, "only the first 6 spans are bold, none is dropped"
for inner in ("#tag", "@someone", "https://x.in/a", "x" * 95):
    assert C.bold(inner) not in C.finalize(f"a **{inner}** b", bold_on=True), inner
assert C.finalize("- one\n* two\n• three") == "→ one\n→ two\n→ three"
assert C.finalize("so *this* and a ** stray") == "so this and a  stray" or C.finalize("so *this* and a ** stray").replace("  ", " ") == "so this and a stray"

# ------------------------------------------------------------------ captions: limits
assert C.words("**HOOK** → one two #tag #other") == 3
assert C.over_limit({"instagram": "w " * 55, "linkedin": "w " * 100, "bluesky": "x" * 200}) == ""
assert "instagram caption has 80 words" in C.over_limit({"instagram": "w " * 80})
assert "maximum is 45" in C.over_limit({"instagram": "w " * 60}, ig_mode="manual_reel")
assert "linkedin" in C.over_limit({"linkedin": "w " * 160}) and "bluesky" in C.over_limit({"bluesky": "x" * 290})
fp = C.finalize_posts({"instagram": "**A** b", "linkedin": "**C** d", "bluesky": "**E** " + "x" * 400, "replies": [{"reply": "**keep**"}]})
assert len(fp["bluesky"]) <= 300 and fp["replies"] == [{"reply": "**keep**"}] and fp["instagram"].startswith(C.bold("A"))

# ------------------------------------------------------------------ writer: format in the prompt, one automatic shorten pass
plan = {"hooks": [{"text": "Hook text"}], "chosen_hook": 0, "topic": "t", "angle": "a", "key_points": []}
focus, brand = {"name": "Ads", "dm_keyword": "ADS"}, {"facts_rules": [], "languages": {}}
seen = []
def gemini_long_then_short(prompt, system="", **k):
    seen.append(prompt)
    ig = ("**HOOK** " + "word " * 90) if len(seen) == 1 else "**HOOK**\n\n→ short line\n\nDM **ADS**\n\n#a #b"
    return json.dumps({"instagram": ig, "linkedin": "**L** ok", "bluesky": "**B** ok", "replies": []})
llm.gemini = gemini_long_then_short
out = writer.run(plan, focus, brand, "VOICE", "g")
assert len(seen) == 2 and "TOO LONG" in seen[1] and C.words(out["instagram"]) < 10, (len(seen), out["instagram"][:60])
p = seen[0]
assert "CAPTION FORMAT" in p and "CAPITAL" in p and "DM **ADS**" in p and "35-60 words" in p and "NO paragraphs" in p and "80-140" not in p
assert "**" in out["instagram"], "the writer keeps markers; bold is applied last, after fact-check"
seen.clear(); llm.gemini = lambda prompt, system="", **k: seen.append(prompt) or json.dumps({"instagram": "**H** ok", "linkedin": "**L**", "bluesky": "**B**", "replies": []})
writer.run(plan, focus, brand, "VOICE", "g", ig_mode="manual_reel")
assert len(seen) == 1 and "25-45 words" in seen[0], "a caption within limits costs no extra call; reels get the shorter limit"

# ------------------------------------------------------------------ images: the permanent quality suffix
SUFFIX = image.DEFAULT_SUFFIX
assert image.enhance("A phone on a counter.") == f"A phone on a counter. {SUFFIX}"
assert image.enhance(image.enhance("A phone")) == image.enhance("A phone"), "never doubled"
assert image.enhance("").endswith(SUFFIX)
image.style = lambda: {"quality_suffix": "MY CUSTOM SUFFIX"}
assert image.enhance("x") == "x. MY CUSTOM SUFFIX", "editable in config/image_style.json"
image.style = lambda: {}
assert json.loads((pathlib.Path(__file__).resolve().parent.parent / "config" / "image_style.json").read_text())["quality_suffix"].startswith("Ultra-sharp 4K")

buf = io.BytesIO(); Image.new("RGB", (1024, 1024), (200, 120, 40)).save(buf, "PNG"); PNG = buf.getvalue()
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ.update(CLOUDFLARE_ACCOUNT_ID="acc", CLOUDFLARE_API_TOKEN="tok", GEMINI_API_KEY="gk")

class R:
    def __init__(self, status=200, j=None, content=b"", ctype="image/png"):
        self.status_code, self._j, self.content, self.headers, self.ok = status, j, content, {"content-type": ctype}, status < 400
    def json(self): return self._j
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(f"HTTP {self.status_code}")

cf_calls = []
def cf_post(url, headers=None, json=None, timeout=None):
    cf_calls.append(json)
    return R(400) if json["steps"] == 8 else R(200, {"result": {"image": base64.b64encode(PNG).decode()}})
image.requests.post = cf_post
image._cloudflare("A phone on a counter", tmp / "cf.jpg")
assert [c["steps"] for c in cf_calls] == [8, 4], "steps=8 first, 4 if the account rejects it"
assert all(c["prompt"].endswith(SUFFIX) for c in cf_calls), "the suffix is on the Cloudflare prompt"
assert (tmp / "cf.jpg").stat().st_size < 900_000 and Image.open(tmp / "cf.jpg").size == (1024, 1024)

gem_bodies = []
def gem_post(url, headers, body, tries=3, timeout=120):
    gem_bodies.append(json.loads(json_dumps(body)))
    if "imageConfig" in body["generationConfig"] and len(gem_bodies) == 1:
        raise RuntimeError("HTTP 400 from generativelanguage.googleapis.com: aspect ratio not supported")
    return {"candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(PNG).decode()}}]}}]}
json_dumps = json.dumps
image.llm._post = gem_post
image._gemini("A phone on a counter", tmp / "gem.jpg")
assert "imageConfig" in gem_bodies[0]["generationConfig"] and gem_bodies[0]["generationConfig"]["imageConfig"]["aspectRatio"] == "4:5"
assert "imageConfig" not in gem_bodies[1]["generationConfig"], "retried without the aspect ratio when the model rejects it"
assert all(b["contents"][0]["parts"][0]["text"].endswith(SUFFIX) for b in gem_bodies), "the suffix is on the Gemini prompt"

urls = []
def poll_get(url, timeout=None):
    urls.append(url)
    return R(200, content=PNG)
image.requests.get = poll_get
image._pollinations("A phone on a counter", tmp / "pol.jpg")
assert urllib.parse.quote(SUFFIX) in urls[0] and "width=1080&height=1350" in urls[0] and "enhance=false" in urls[0]

# ------------------------------------------------------------------ images: the picture prompt is concrete, not 'empty space, no text'
gemma_prompts = []
SPEC_BOLD = json.dumps({"style": "bold", "headline": "While you hustle, motion works", "highlight": ["motion"], "sub": "Motion adds visibility fast"})
SPEC_CHAT = json.dumps({"style": "chat", "headline": "Customer messages at 11 pm", "highlight": ["11"], "sub": "No reply by morning.",
                        "chat": [{"side": "left", "text": "Are you open?", "time": "11:02 PM"}]})
def gemma(prompt, system="", **k):
    gemma_prompts.append(prompt)
    return SPEC["json"] if "Design copy" in prompt else "<prompt>A phone playing a short animated ad on a cafe counter, warm light</prompt>"
SPEC = {"json": SPEC_BOLD}
llm.gemma = gemma
config.ROOT = tmp; config.MEDIA = tmp / "data" / "media"; config.MEDIA.mkdir(parents=True)
pp = image.picture_prompt(plan, {"name": "Animated ads"}, json.loads(SPEC_BOLD), "g")
req = gemma_prompts[-1]
assert pp.endswith(SUFFIX) and "cafe counter" in pp
assert "empty space" not in req and "ONE concrete, specific scene" in req and "While you hustle" in req and "the headline goes there" in req

# ------------------------------------------------------------------ images: fallback order
eng = {"n": 0, "fail": False, "prompts": []}
def fake_engine(img_prompt, path):
    eng["n"] += 1; eng["prompts"].append(img_prompt)
    if eng["fail"]:
        raise RuntimeError("engine down")
    image._save(PNG, path, max_side=1350)
fake_engine.__name__ = "_fake"
image._engines = lambda: [fake_engine]
fc = {"id": "animated_ads", "name": "Animated ads", "dm_keyword": "ADS"}

res = image.run(plan, fc, "2026-10-14")                                                    # 1. the normal case: picture + real text
assert res["engine"] == "visual:fake" and res["style"] == "visual" and res["ai_generated"] is True, res
assert res["prompt"].endswith(SUFFIX) and eng["prompts"][0].endswith(SUFFIX)
out_path = config.ROOT / res["path"]
im = Image.open(out_path); assert im.size == (1080, 1350) and out_path.stat().st_size < 900_000
assert b"trainedAlgorithmicMedia" in out_path.read_bytes(), "picture cards carry the IPTC AI-generated marker"

eng.update(n=0); SPEC["json"] = SPEC_CHAT                                                  # 2. chat cards are already a specific visual: no AI call
res = image.run(plan, fc, "2026-10-15")
assert res["engine"] == "designed_card" and res["style"] == "chat" and eng["n"] == 0, res

SPEC["json"] = SPEC_BOLD; os.environ["IMAGE_VISUALS"] = "0"                                # 3. switch off
res = image.run(plan, fc, "2026-10-16")
assert res["engine"] == "designed_card" and eng["n"] == 0
del os.environ["IMAGE_VISUALS"]

eng.update(n=0, fail=True)                                                                 # 4. every engine fails: designed card, engines tried once (x2 retries), not again
res = image.run(plan, fc, "2026-10-17")
assert res["engine"] == "designed_card" and eng["n"] == 2 and any(e.startswith("visual_card") for e in res["errors"]), (res["engine"], eng["n"], res["errors"])
assert (config.ROOT / res["path"]).exists()

real_render = cards.render
cards.render = lambda spec, path: (_ for _ in ()).throw(RuntimeError("render broke"))      # 5. card also fails: plain text card, no third round of engine retries
eng["n"] = 0
res = image.run(plan, fc, "2026-10-18")
assert res["engine"] == "text_card" and eng["n"] == 2 and (config.ROOT / res["path"]).exists(), (res["engine"], eng["n"])

eng.update(n=0, fail=False); SPEC["json"] = SPEC_CHAT                                      # 6. chat card breaks: a plain AI picture still rescues the post
res = image.run(plan, fc, "2026-10-19")
assert res["engine"] == "fake" and eng["n"] == 1 and (config.ROOT / res["path"]).exists(), res
cards.render = real_render
print("visuals test passed: bold/CAPS captions, limits, writer retry, suffix on every engine, picture+text card, fallback order")
