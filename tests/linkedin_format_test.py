"""Offline tests: LinkedIn alternates a text-only post and an image post. The picker flips the last LinkedIn post that really went out,
the publisher leaves the picture off LinkedIn only (Instagram and Bluesky keep it), the writer knows a text day has no picture, the daily run
records and announces the format, and the learning loop / analytics label LinkedIn posts with the format we chose."""
import json, os, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ.update(BUFFER_API_KEY="x", ZERNIO_API_KEY="y")
os.environ.pop("LINKEDIN_FORMAT", None)
from src import analytics, config, formats, learning, llm, publish, tg

tmp = pathlib.Path(tempfile.mkdtemp())
for n in ("drafts", "media"):
    (tmp / n).mkdir()
config.DATA, config.DRAFTS, config.MEDIA = tmp, tmp / "drafts", tmp / "media"


def put(date, status="published", fmt=None, image=True, li_ok=True):
    d = {"date": date, "status": status, "image": {"path": "data/media/x.jpg" if image else None}, "results": {"linkedin": {"ok": li_ok}},
         "posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}}
    if fmt:
        d["linkedin_format"] = fmt
    config.save_json(config.DRAFTS / f"{date}.json", d)


def clear():
    for f in config.DRAFTS.glob("*.json"):
        f.unlink()


# ------------------------------------------------------------------ the picker
assert formats.linkedin_format() == "text", "nothing sent yet: start with text"
put("2026-10-10", image=False)                                                  # legacy draft, no field, no picture -> it was a text post
assert formats.of_draft(json.load(open(config.DRAFTS / "2026-10-10.json"))) == "text" and formats.linkedin_format() == "image"
put("2026-10-12", image=True)                                                   # legacy draft with a picture -> it was an image post
assert formats.linkedin_format() == "text"
put("2026-10-14", fmt="text", image=True)                                       # the recorded field wins over the picture
assert formats.linkedin_format() == "image"
put("2026-10-15", status="pending", fmt="image")                                # not sent yet: ignored
put("2026-10-16", status="rejected", fmt="image")
put("2026-10-17", status="published", fmt="image", li_ok=False)                 # LinkedIn failed that day: it did not go out, so it does not count
assert formats.linkedin_format() == "image", "only posts that really reached LinkedIn flip the format"
put("2026-10-18", status="partial", fmt="image")                                # partial with LinkedIn ok counts
assert formats.linkedin_format() == "text"
assert formats.linkedin_format(today="2026-10-18") == "image", "a redo today ignores today's own draft, so the decision stays stable"
os.environ["LINKEDIN_FORMAT"] = "image"
assert formats.linkedin_format() == "image"
os.environ["LINKEDIN_FORMAT"] = "TEXT"
assert formats.linkedin_format() == "text"
os.environ["LINKEDIN_FORMAT"] = "nonsense"
assert formats.linkedin_format() == "text", "an unknown value falls back to alternating"
os.environ.pop("LINKEDIN_FORMAT")

clear()                                                                         # six days in a row alternate
seq = []
for day in range(1, 7):
    f = formats.linkedin_format()
    seq.append(f)
    put(f"2026-11-0{day}", fmt=f, image=(f == "image"))
assert seq == ["text", "image", "text", "image", "text", "image"], seq

# ------------------------------------------------------------------ the publisher
calls = []
class Fake:
    name, secrets, platforms = "fake", [], ("instagram", "linkedin", "bluesky")
    alt = None
    def post(self, platform, text, image_url, image_path):
        calls.append((platform, bool(image_url), image_path))
        return "ok"
publish.PROVIDERS = [Fake]
publish.choose_order = lambda provs, today=None: provs
def publish_with(fmt):
    calls.clear()
    d = {"posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}, "image": {"path": "data/media/x.jpg"}, "hooks": [{"text": "h"}], "chosen_hook": 0}
    if fmt:
        d["linkedin_format"] = fmt
    res = publish.publish_draft(d)
    assert all(r["ok"] for r in res.values()), res
    return {p: (u, path) for p, u, path in calls}
c = publish_with("text")
assert c["linkedin"] == (False, None), "text day: no picture goes to LinkedIn"
assert c["instagram"] == (True, "data/media/x.jpg") and c["bluesky"] == (True, "data/media/x.jpg"), "Instagram and Bluesky keep the picture"
c = publish_with("image")
assert all(v == (True, "data/media/x.jpg") for v in c.values()), c
c = publish_with(None)
assert c["linkedin"] == (True, "data/media/x.jpg"), "older drafts without the field behave as before"

# ------------------------------------------------------------------ the writer prompt
from src.agents import writer
seen = []
llm.gemini = lambda p, s="", **k: seen.append(p) or json.dumps({"instagram": "**H** ok", "linkedin": "A hook sentence.", "bluesky": "**B**", "replies": []})
plan = {"hooks": [{"text": "Hook text"}], "chosen_hook": 0, "topic": "t", "angle": "a", "key_points": []}
focus, brand = {"name": "Ads", "dm_keyword": "ADS"}, {"facts_rules": [], "languages": {}}
writer.run(plan, focus, brand, "VOICE", "g", linkedin_format="text")
writer.run(plan, focus, brand, "VOICE", "g", linkedin_format="image")
writer.run(plan, focus, brand, "VOICE", "g")
assert "NO PICTURE" in seen[0] and "see more" in seen[0] and "never refer to an image" in seen[0]
assert "NO PICTURE" not in seen[1] and "NO PICTURE" not in seen[2], "image days and older callers are unchanged"

# ------------------------------------------------------------------ a full daily run records and announces the format
clear()
sent = []
tg.send = lambda text, buttons=None: sent.append(text)
tg.send_photo = lambda *a, **k: None
tg.chat_id = lambda: "1"
def plan_json(**k):
    return json.dumps({"idea_id": None, "topic": "t", "angle": "a", "key_points": ["x"], "hooks": [{"style": "comparison", "text": "Hook?"}], "chosen_hook": 0,
                       "image_idea": "i", "ok": True, "issues": [], "revised": {}, "ad_score": 3, "notes": "", "post": "A calm LinkedIn post.", "topics": [{"topic": "t", "angle": "a", "why_it_matters": "w"}]})
llm.groq = lambda p, s="", **k: plan_json() if "JSON" in p else "guidance"
llm.gemma = lambda p, s="", **k: plan_json() if "JSON" in p else "img prompt"
writer_prompts = []
llm.gemini = lambda p, s="", **k: writer_prompts.append(p) or json.dumps({"instagram": "ig", "linkedin": "li", "bluesky": "bs", "replies": []})
import src.agents.image as image_mod
image_mod.run = lambda plan, focus, date, guidance="": {"prompt": "p", "path": None}
from src import run_daily
run_daily.pick_focus = lambda brand, history: next(s for s in brand["services"] if s["id"] == "chatbot")
run_daily.main()
draft = config.load_json(config.DRAFTS / f"{run_daily.today}.json", None)
assert draft["linkedin_format"] == "text", draft.get("linkedin_format")
assert any("LinkedIn today: TEXT ONLY (no image)" in m for m in sent), "the Telegram message tells the owner"
assert any("NO PICTURE" in p for p in writer_prompts)

# the next day: today's draft was sent to LinkedIn as text, so the following one is an image post
config.save_json(config.DRAFTS / "2026-10-20.json", {**draft, "date": "2026-10-20", "status": "published", "results": {"linkedin": {"ok": True}}})
(config.DRAFTS / f"{run_daily.today}.json").unlink()
sent.clear(); writer_prompts.clear()
run_daily.main()
draft2 = config.load_json(config.DRAFTS / f"{run_daily.today}.json", None)
assert draft2["linkedin_format"] == "image" and any("LinkedIn today: with the image" in m for m in sent)
assert not any("NO PICTURE" in p for p in writer_prompts)

# ------------------------------------------------------------------ learning loop and analytics use the format we chose
assert learning.row_format({"linkedin_format": "text"}, "linkedin", "image") == "text"
assert learning.row_format({"linkedin_format": "text"}, "instagram", "reel") == "reel", "only LinkedIn is affected"
assert learning.row_format({}, "linkedin", "image") == "image", "older drafts keep the reported format"
row = {"platform": "linkedin", "id": "1", "published_at": "2026-10-10T08:00:00+00:00", "format": "image",
       "text": "Google Maps gets you discovered, but a missing website loses trust."}
bd = {"date": "2026-10-10", "status": "published", "service": "website", "topic": "T", "hook_style": "Q", "linkedin_format": "text",
      "posts": {"linkedin": "Google Maps gets you discovered, but a missing website loses trust.\n\nMore lines."}}
assert analytics.match_drafts([row], [bd])[0]["format"] == "text", "the digest compares text posts with text posts"
print("linkedin format test passed: alternation, publisher, writer prompt, daily run, learning and analytics labels")
