"""Offline test: Ideogram is the default image engine, Cloudflare FLUX (then Gemini, Pollinations) is the fallback chain. Network is mocked."""
import io, os, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
for k in ("IDEOGRAM_API_KEY", "IDEOGRAM_RENDERING_SPEED", "IDEOGRAM_MAGIC_PROMPT", "IDEOGRAM_STYLE", "IMAGE_ENGINE_ORDER",
          "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "GEMINI_API_KEY"):
    os.environ.pop(k, None)
from PIL import Image
from src.agents import image

buf = io.BytesIO(); Image.new("RGB", (1024, 1280), (30, 60, 90)).save(buf, "PNG"); PNG = buf.getvalue()
tmp = pathlib.Path(tempfile.mkdtemp())
names = lambda: [e.__name__.strip("_") for e in image._engines()]

# 1. order: Ideogram first, then Cloudflare FLUX, Gemini, Pollinations; a missing key skips that engine
assert names() == ["pollinations"], "no keys: only the free engine"
os.environ.update(CLOUDFLARE_ACCOUNT_ID="acc", CLOUDFLARE_API_TOKEN="tok", GEMINI_API_KEY="gk")
assert names() == ["cloudflare", "gemini", "pollinations"], "no Ideogram key: exactly the old order"
os.environ["IDEOGRAM_API_KEY"] = "ik"
assert names() == ["ideogram", "cloudflare", "gemini", "pollinations"]
os.environ["IMAGE_ENGINE_ORDER"] = "cloudflare, ideogram, nonsense"
assert names() == ["cloudflare", "ideogram"], "the order can be changed; unknown names are ignored"
os.environ["IMAGE_ENGINE_ORDER"] = "nonsense"
assert names() == ["pollinations"], "nothing usable in the list: the free engine, never an empty chain"
os.environ["IMAGE_ENGINE_ORDER"] = ""
assert names() == ["ideogram", "cloudflare", "gemini", "pollinations"], "an empty variable means the default"
os.environ.pop("IMAGE_ENGINE_ORDER")


class R:
    def __init__(self, status=200, j=None, content=b""):
        self.status_code, self._j, self.content = status, j, content
    def json(self): return self._j
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


# 2. the Ideogram request: multipart, Api-Key header, 4:5, the quality suffix, no text in the picture, the link downloaded
posts, gets = [], []
def post(url, headers=None, files=None, timeout=None, json=None):
    posts.append((url, headers, {k: v[1] for k, v in files.items()}))
    return R(200, {"data": [{"url": "https://ideogram.ai/api/images/ephemeral/x.png", "is_image_safe": True, "prompt": "p"}]})
def get(url, timeout=None):
    gets.append(url)
    return R(200, content=PNG)
image.requests.post, image.requests.get = post, get
out = tmp / "ig.jpg"
image._ideogram("A phone on a cafe counter", out)
url, headers, form = posts[0]
assert url == "https://api.ideogram.ai/v1/ideogram-v3/generate" and headers == {"Api-Key": "ik"}
assert form["prompt"].startswith("A phone on a cafe counter.") and form["prompt"].endswith(image.DEFAULT_SUFFIX), "the permanent quality suffix is on the prompt"
assert form["aspect_ratio"] == "4x5" and form["rendering_speed"] == "DEFAULT" and form["magic_prompt"] == "OFF" and form["num_images"] == "1" and "style_type" not in form
assert "text" in form["negative_prompt"] and "watermark" in form["negative_prompt"]
assert gets == ["https://ideogram.ai/api/images/ephemeral/x.png"], "the expiring link is downloaded"
assert out.stat().st_size < 900_000 and Image.open(out).size == (1024, 1280) and b"trainedAlgorithmicMedia" in out.read_bytes(), "saved as an AI-marked JPEG"
os.environ.update(IDEOGRAM_RENDERING_SPEED="turbo", IDEOGRAM_MAGIC_PROMPT="auto", IDEOGRAM_STYLE="realistic")
image._ideogram("A phone", out)
assert posts[-1][2]["rendering_speed"] == "TURBO" and posts[-1][2]["magic_prompt"] == "AUTO" and posts[-1][2]["style_type"] == "REALISTIC"
for k in ("IDEOGRAM_RENDERING_SPEED", "IDEOGRAM_MAGIC_PROMPT", "IDEOGRAM_STYLE"):
    os.environ.pop(k)

# 3. an account that rejects 4:5 gets the nearest ratio, then none; other errors are raised so the next engine takes over
ratios = []
def post_ratio(url, headers=None, files=None, timeout=None):
    ratios.append(files.get("aspect_ratio", (None, None))[1])
    return R(400) if len(ratios) < 3 else R(200, {"data": [{"url": "https://i/x.png", "is_image_safe": True}]})
image.requests.post = post_ratio
image._ideogram("A phone", out)
assert ratios == ["4x5", "3x4", None], ratios
for bad, msg in ((R(401), "HTTP 401"), (R(200, {"data": []}), "no image"), (R(200, {"data": [{"url": ""}]}), "no image"),
                 (R(200, {"data": [{"url": "https://i/x.png", "is_image_safe": False}]}), "unsafe")):
    image.requests.post = lambda url, headers=None, files=None, timeout=None, r=bad: r
    try:
        image._ideogram("A phone", out)
        raise SystemExit("should have raised: " + msg)
    except RuntimeError as e:
        assert msg in str(e), (msg, str(e))

# 4. the fallback chain in the real picture loop: Ideogram down -> Cloudflare FLUX takes over
image.picture_prompt = lambda *a, **k: "A phone on a cafe counter"
calls = []
def ideogram_down(p, path):
    calls.append("ideogram"); raise RuntimeError("Ideogram is down")
def cloudflare_ok(p, path):
    calls.append("cloudflare"); image._save(PNG, path, max_side=1350)
ideogram_down.__name__, cloudflare_ok.__name__ = "_ideogram", "_cloudflare"      # the engine name is recorded from the function name
image._ideogram, image._cloudflare = ideogram_down, cloudflare_ok
errors = []
info = image._ai_picture({}, {"id": "chatbot", "name": "Chatbot"}, None, "g", tmp / "chain.jpg", errors)
assert info["engine"] == "cloudflare" and calls == ["ideogram", "ideogram", "cloudflare"], calls      # two tries on Ideogram, then FLUX
assert errors and errors[0].startswith("ideogram: Ideogram is down") and (tmp / "chain.jpg").exists()
calls.clear()
def ideogram_ok(p, path):
    calls.append("ideogram"); image._save(PNG, path, max_side=1350)
ideogram_ok.__name__ = "_ideogram"
image._ideogram = ideogram_ok
info = image._ai_picture({}, {"id": "chatbot", "name": "Chatbot"}, None, "g", tmp / "first.jpg", [])
assert info["engine"] == "ideogram" and calls == ["ideogram"], "Ideogram is the default: when it works nothing else is called"
print("image engines test passed: Ideogram default, FLUX/Gemini/Pollinations fallback, order override, request shape, errors")
