"""Offline test of the service explainer diagrams: only facts from the config and the owner's details are drawn, never a price or payment wording,
lead generation shows no packages, layouts and palettes rotate, and the diagram goes to Telegram as its own image (not the thumbnail, nothing stored)."""
import inspect, os, pathlib, re, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from PIL import Image
from src import config, diagrams, tg

brand = config.services()
by = {s["id"]: s for s in brand["services"]}
det = diagrams.details()
BANNED = re.compile(r"(?i)(₹|\brs\.?\s*\d|\binr\b|\$|\bprice|\bpricing|\bcost|\bpay\b|\bpaid\b|\bpayment|\bfree\b|\bdiscount|\boffer\b|\b\d+\s*hours?\b|\bdelivered\b)")

# ---- 1. which layouts each service may use (real config + the owner's site packages)
for sid in ("website", "chatbot", "reel_scripts", "seo_blogs"):
    assert diagrams.eligible(det[sid]) == ["steps", "path", "tiers"], sid
assert diagrams.eligible(det.get("animated_ads", {})) == ["steps", "path"], "no packages on the site for paid animated ads: no invented ones"
assert diagrams.eligible(det["lead_gen"]) == ["inquiry"], "lead generation has no packages, only how to enquire"
assert [t["name"] for t in diagrams.tiers_of(det["seo_blogs"])] == ["Single Article", "Growth Bundle"], "two SEO packages, as on the site for now"
assert len(diagrams.tiers_of(det["website"])) == 3 and len(diagrams.tiers_of(det["chatbot"])) == 2
assert set(by) <= set(det) | {"animated_ads"}, "every service is either described by the owner or deliberately left to the steps layouts"

# ---- 2. every word that can be drawn is a verified fact: no price, payment, free, discount or delivery-time wording
def drawn(service, layout):
    d = det.get(service["id"], {})
    out = [service["name"], diagrams._short(service, d), d.get("for") or diagrams.FOR_WHOM.get(service["id"], diagrams.DEFAULT_FOR), "DM " + service["dm_keyword"]]
    if layout in ("steps", "path"):
        out += [x for pair in diagrams.steps(service) for x in pair]
    if layout == "tiers":
        out += [t["name"] for t in diagrams.tiers_of(d)] + [i for t in diagrams.tiers_of(d) for i in t["includes"]]
    if layout == "inquiry":
        out += ["Interested? Send a message to enquire.", "Message the word below to start the conversation."]
    return out
for s in brand["services"]:
    for lay in diagrams.eligible(det.get(s["id"], {})):
        bad = [t for t in drawn(s, lay) if BANNED.search(t)]
        assert not bad, (s["id"], lay, bad)
assert "price_text" not in dir(diagrams) and "preview" not in inspect.signature(diagrams.render).parameters and "PLACEHOLDERS" not in dir(diagrams)
assert "Package detail" not in inspect.getsource(diagrams), "no placeholder text can ever be drawn"

# ---- 3. layouts that need details refuse to render without them
for sid, lay in (("lead_gen", "tiers"), ("animated_ads", "tiers"), ("animated_ads", "checklist"), ("animated_ads", "hub")):
    try:
        diagrams.render(by[sid], "/tmp/refused.jpg", brand, layout=lay)
        raise SystemExit(f"{sid}/{lay} should be refused")
    except ValueError:
        pass

# ---- 4. rotation: consecutive days differ in layout and palette, every eligible layout gets used
import datetime as dt
days = [(dt.date(2026, 10, 1) + dt.timedelta(d)).isoformat() for d in range(14)]
picks = [diagrams.choose(x, det["website"]) for x in days]
assert all(a[0] != b[0] and a[1] != b[1] for a, b in zip(picks, picks[1:])), picks
assert {p[0] for p in picks} == {"steps", "path", "tiers"}
lead = [diagrams.choose(x, det["lead_gen"]) for x in days]
assert {p[0] for p in lead} == {"inquiry"} and all(a[1] != b[1] for a, b in zip(lead, lead[1:])), "one layout for lead generation, but a new palette every day"

# ---- 5. everything renders at 1080x1350
tmp = pathlib.Path(tempfile.mkdtemp())
for s in brand["services"]:
    for lay in diagrams.eligible(det.get(s["id"], {})):
        for pal in range(len(diagrams.PALETTES)):
            p = diagrams.render(s, tmp / f"{s['id']}-{lay}-{pal}.jpg", brand, layout=lay, palette=pal)
            im = Image.open(p)
            assert im.size == (1080, 1350) and im.format == "JPEG" and os.path.getsize(p) > 20000, (s["id"], lay, pal)

# ---- 6. Telegram: its own image, labelled, temp file only, nothing stored in the repo
from src import run_daily
photos = []
def send_photo(path, caption=""):
    photos.append((str(path), caption, os.path.exists(path), Image.open(path).size))
tg.send_photo = send_photo
before = sorted(p.name for p in config.MEDIA.glob("*")) if config.MEDIA.exists() else []
info = run_daily.send_explainer(by["seo_blogs"])
path, caption, existed, size = photos[0]
assert existed and size == (1080, 1350) and not os.path.exists(path), "sent from a temp file that is removed afterwards"
assert "[SERVICE EXPLAINER]" in caption and "Not the thumbnail" in caption and "never posted automatically" in caption and info["layout"] in caption
assert info["layout"] in ("steps", "path", "tiers")
assert before == (sorted(p.name for p in config.MEDIA.glob("*")) if config.MEDIA.exists() else []), "nothing is written into the repo"
print("diagrams test passed: facts only, no price/payment wording, lead gen inquiry-only, rotation, all layouts render, separate Telegram image")
