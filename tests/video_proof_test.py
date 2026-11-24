"""Offline test: real proof screenshots. Only what the screenshot shows may be claimed, stale or unknown proofs are never used, and the images are blurred."""
import json, pathlib, sys
from datetime import date
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video-agent"))
from agent import graphics, proof

idx = json.loads((proof.DIR / "index.json").read_text())["proofs"]
assert {p["business_type"] for p in idx} >= {"gym", "restaurant", "cafe", "hotel", "chatbot"}
for p in idx:
    assert (proof.DIR / p["file"]).exists() and ("no reply" in p["status"] or p.get("kind") == "ai_reply") and p["checked"] and p["sent"]
    assert not any(c.isdigit() for c in p["id"]), "ids carry no phone numbers"
    text = json.dumps(p).lower()
    assert "+91" not in text and "pirates" not in text and "zoca" not in text and "kake" not in text and "aesthetic" not in text and "aayojan" not in text and "bhubaneswar" not in text, "no business names or numbers in the index"

# freshness: a proof is only used while its check is recent
today = date(2026, 11, 24)
assert proof.entry("gym", today) and proof.entry("restaurant", today)
assert proof.entry("gym", date(2027, 3, 1)) is None, "a stale check is not used"
assert proof.entry("bank", today) is None and proof.entry("", today) is None

class _Day(date):                       # pin "today" so the test does not age out with the check date
    @classmethod
    def today(cls):
        return cls(2026, 11, 24)
proof.date = _Day

# the card claims only what the screenshot shows
t = proof.tag(proof.entry("gym", today))
assert t.startswith("REAL") and "sent 29 Jun" in t and "no reply by 23 Nov" in t and "%" not in t

tai = proof.tag(proof.entry("chatbot", today))
assert tai == "REAL · sent 30 Oct, 2:08 pm · AI replied by 2:09 pm" and "convert" not in tai.lower() and "%" not in tai

# resolver: a usable proof becomes a mock with the tag, the staged image and its ratio; an unknown one falls back, never a fake
W = [{"text": w, "start": 0.2 + i * 0.4, "end": 0.55 + i * 0.4} for i, w in enumerate("maine ek gym ko message kiya koi reply nahi aaya".split())]
r = graphics.resolve_graphic({"graphic": {"layout": "step", "heading": "No reply", "mock": {"type": "proof", "items": ["gym"]}}}, W, 5.0)
assert r["mock"]["type"] == "proof" and r["mock"]["items"][0].startswith("REAL") and r["mock"]["items"][1].endswith("gym.jpg") and float(r["mock"]["items"][2]) > 0.5
assert (proof.WORK / "proof" / "gym.jpg").exists(), "staged next to the reel's assets"
r2 = graphics.resolve_graphic({"graphic": {"layout": "step", "heading": "x", "mock": {"type": "proof", "items": ["bank"]}}}, W, 5.0)
assert r2["layout"] == "title" and not r2.get("mock"), "unknown proof: no mock"

# the images are blurred: the header strip and the business-name box carry no sharp detail
from PIL import Image, ImageFilter, ImageChops
def sharp(im, box):
    c = im.crop(box).convert("L"); return sum(ImageChops.difference(c, c.filter(ImageFilter.GaussianBlur(2))).getdata()) / (c.width * c.height)
for p in idx:
    if p["id"] == "chatbot":
        continue                                             # different layout: checked by eye (name box + status bar blurred)
    im = Image.open(proof.DIR / p["file"])
    head = sharp(im, (0, 0, im.width, 100))
    body = sharp(im, (90, 120, 640, 260))                      # the sharp encryption notice and date
    assert head < body / 3, (p["id"], head, body)
schema = (ROOT / "video-agent/agent/schema.py").read_text()
assert '"proof"]' in schema and "proof" in (ROOT / "video-agent/template/src/graphics/MockHost.tsx").read_text()
print("proof ok")
