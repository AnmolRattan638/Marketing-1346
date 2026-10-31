"""Offline test of the carousel feature: the fixed order hook -> problem -> solution -> CTA, the rotating tastes, the facts rule for the 'X said' taste, slide rendering,
multi-image publishing with a single-image fallback, the Telegram album, and a full daily run."""
import copy, json, os, pathlib, re, shutil, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from PIL import Image
from src import buffer, carousel, config, direct, learning, llm, publish, tg
from src.agents import carousel as ca, cards

ROOT = config.ROOT
brand = config.services()
by = {s["id"]: s for s in brand["services"]}
bot, seo = by["chatbot"], by["seo_blogs"]
tmp = pathlib.Path(tempfile.mkdtemp())
config.DRAFTS = tmp / "drafts"; config.DRAFTS.mkdir()

GOOD = [{"role": "hook", "headline": "Your phone buzzes at 11 PM.", "body": "Most owners ignore it."},
        {"role": "problem", "headline": "Something small slips away.", "body": "A question goes unanswered and the customer moves on."},
        {"role": "problem", "headline": "Unanswered messages.", "body": "An unanswered message is an enquiry that may not return."},
        {"role": "solution", "headline": "Answer common questions automatically.", "body": "A chatbot replies to everyday questions at any hour."},
        {"role": "solution", "headline": "Keep your own time.", "body": "You step in only when a conversation needs you."},
        {"role": "cta", "headline": "anything", "body": "Interested? Send a message to enquire."}]
plan = {"topic": "Late replies", "angle": "a", "key_points": ["p"], "hooks": [{"style": "q", "text": "Hook?"}], "chosen_hook": 0}

# ---- 1. the tastes: complete, honest, and the 'X said' taste is gated by verified facts
fl = ca.flavors()
assert len(fl) >= 8 and len({f["id"] for f in fl}) == len(fl)
for f in fl:
    assert all(f.get(k) for k in ("id", "name", "taste", "hook", "problem", "solution", "cta")), f["id"]
    assert not ca.BANNED.search(" ".join(str(f[k]) for k in ("taste", "hook", "problem", "solution", "cta"))), f["id"]
assert [f["id"] for f in fl if f.get("needs_fact")] == ["factual-source"]
assert ca.facts_for("chatbot") == [], "no facts are shipped: a model never makes up who said what"

# ---- 2. rotation: never one of the last two, every usable taste used, balanced; the fact taste only when a fact exists
def save(date, flavor, fact_id=None):
    config.save_json(config.DRAFTS / f"{date}.json", {"date": date, "carousel": {"flavor": flavor, "fact_id": fact_id}})
seq = []
for d in range(1, 19):
    date = f"2026-11-{d:02d}"
    taste, fact = ca.pick_flavor(date, "chatbot")
    assert fact is None and not taste.get("needs_fact")
    seq.append(taste["id"]); save(date, taste["id"])
usable = [f["id"] for f in fl if not f.get("needs_fact")]
assert all(a != b for a, b in zip(seq, seq[1:])) and all(seq[i] not in seq[max(0, i - 2):i] for i in range(len(seq))), seq
assert set(seq[:len(usable)]) == set(usable) and max(seq.count(u) for u in usable) - min(seq.count(u) for u in usable) <= 1
FACT = {"id": "f1", "claim": "chatbots can answer routine questions", "source_name": "Example Source", "source_url": "https://example.com", "services": ["chatbot"]}
real_facts = ca.facts_for
ca.facts_for = lambda sid: [FACT] if sid == "chatbot" else []
picked = {ca.pick_flavor(f"2027-01-{d:02d}", "chatbot")[0]["id"] for d in range(1, 12)}      # fresh dates: rotation without drafts
assert ca.pick_flavor("2026-10-01", "chatbot")[0] is not None
shutil.rmtree(config.DRAFTS); config.DRAFTS.mkdir()
seen_fact = False
for d in range(1, 15):
    date = f"2026-12-{d:02d}"
    taste, fact = ca.pick_flavor(date, "chatbot")
    if taste.get("needs_fact"):
        assert fact == FACT; seen_fact = True
    save(date, taste["id"], fact["id"] if fact else None)
assert seen_fact, "with a verified fact the factual taste joins the rotation"
assert all(not ca.pick_flavor(f"2027-02-{d:02d}", "seo_blogs")[0].get("needs_fact") for d in range(1, 6)), "a fact for another service is not used"
ca.facts_for = real_facts
shutil.rmtree(config.DRAFTS); config.DRAFTS.mkdir()

# ---- 3. validation: the order and counts are never negotiable
norm = lambda s: ca.normalize(copy.deepcopy(s), bot)
ok = norm(GOOD)
assert ok[-1]["headline"] == "DM BOT", "the CTA headline always carries the real DM keyword"
assert ca.validate(ok, bot, fl[0], None) == []
def broken(mutate):
    s = norm(GOOD); mutate(s); return ca.validate(s, bot, fl[0], None)
assert any("order" in p for p in broken(lambda s: s.insert(1, s.pop(3))))                       # a solution before a problem
assert any("order" in p for p in broken(lambda s: s.insert(0, s.pop())))                         # cta first
assert any("'hook'" in p for p in broken(lambda s: s.insert(1, dict(s[0]))))                      # two hooks
assert any("'solution'" in p for p in broken(lambda s: s.__delitem__(3)))                         # one solution only
assert any("'problem'" in p for p in broken(lambda s: s.__delitem__(slice(1, 3))))                # no problem
assert any("at most 7" in p for p in broken(lambda s: [s.insert(5, {"role": "solution", "headline": "x", "body": "y"}) for _ in range(2)]))
assert any("one of" in p for p in broken(lambda s: s[1].update(role="intro")))
assert any("over 14 words" in p for p in broken(lambda s: s[1].update(headline=" ".join(["word"] * 15))))
assert any("too long" in p for p in broken(lambda s: s[1].update(body=" ".join(["word"] * 41))))
assert any("too long" in p for p in broken(lambda s: s[0].update(body=" ".join(["word"] * 15))))
for bad in ("Only INR 999", "It is free", "Save 40% today", "Get 10x leads", "Delivered in 24 hours", "We guarantee it", "Pay after approval", "A proven method", "The price is low", "No cost"):
    assert any("not allowed" in p for p in broken(lambda s: s[1].update(body=bad))), bad
for bad in ("According to a study, owners lose leads", "A survey found this", "Experts say chatbots help", "Research shows it works", "As reported last week"):
    assert any("verified source" in p for p in broken(lambda s: s[1].update(body=bad))), bad
assert ca.validate(norm(GOOD), bot, fl[0], None) == [] and not [p for p in broken(lambda s: s[1].update(body="Imagine a customer messaging at night."))]
# the factual taste: the hook names the source and slides 1-2 quote the claim exactly
fs = norm(GOOD)
assert len(ca.validate(fs, bot, fl[1], FACT)) == 2
fs[0].update(headline="Example Source says chatbots can answer routine questions.", body="Here is why.")
assert ca.validate(fs, bot, fl[1], FACT) == [], ca.validate(fs, bot, fl[1], FACT)
fs[0]["headline"] = "A source says chatbots can answer routine questions."
assert any("names" in p or "source" in p for p in ca.validate(fs, bot, fl[1], FACT))

# ---- 4. the planner: retry once with the problems, fail closed on repeated violations, never block on a failing fact-check
prompts, replies = [], []
def gemini(p, s="", **k):
    prompts.append(p)
    return json.dumps({"slides": replies.pop(0)})
llm.gemini = gemini
verdicts = []
def checker(p, s="", **k):
    v = verdicts.pop(0)
    if isinstance(v, Exception):
        raise v
    return json.dumps(v)
llm.factcheck_model = checker
G = lambda: copy.deepcopy(GOOD)
replies[:] = [G()]; verdicts[:] = [{"ok": True, "issues": []}]
car, why = ca.build(plan, bot, brand, "g", "2026-11-30")
assert why is None and car["checked"] is True and len(car["slides"]) == 6 and car["slides"][-1]["headline"] == "DM BOT" and car["flavor"] in usable and car["fact_id"] is None
q = prompts[-1]
assert "STRICT ORDER" in q and "1 hook slide, then 1-2 problem slides, then 2-3 solution slides, then 1 cta slide" in q and "DM BOT" in q and json.dumps(brand["facts_rules"], ensure_ascii=False)[:60] in q

bad = G(); bad[1]["body"] = "Only INR 999 today"                                            # a price: rejected before any fact-check, then repaired
replies[:] = [bad, G()]; verdicts[:] = [{"ok": True, "issues": []}]; prompts.clear()
car, why = ca.build(plan, bot, brand, "g", "2026-11-30")
assert car and len(prompts) == 2 and "FIX THESE PROBLEMS" in prompts[1] and "not allowed" in prompts[1]

replies[:] = [bad, bad]; prompts.clear()
car, why = ca.build(plan, bot, brand, "g", "2026-11-30")
assert car is None and "not allowed" in why and len(prompts) == 2, "two failures: no carousel, the post goes out as a single image"

replies[:] = [G(), G()]; verdicts[:] = [{"ok": False, "issues": ["slide 3: invents a client"]}, {"ok": True, "issues": []}]; prompts.clear()
car, why = ca.build(plan, bot, brand, "g", "2026-11-30")
assert car and "slide 3: invents a client" in prompts[1], "the second model's issues go back to the planner"

replies[:] = [G()]; verdicts[:] = [RuntimeError("model down")]
car, why = ca.build(plan, bot, brand, "g", "2026-11-30")
assert car and car["checked"] is False, "a down fact-checker never blocks; the draft says it was not machine-checked"
replies[:] = [[]] * 2
assert ca.build(plan, bot, brand, "g", "2026-11-30")[0] is None

# the factual taste: a model-made attribution can never pass, the fact is quoted exactly
ca.facts_for = lambda sid: [FACT]
for d in range(1, 15):
    save(f"2027-03-{d:02d}", "myth-bust")
fact_slides = G(); fact_slides[0].update(headline="Example Source says chatbots can answer routine questions.", body="Here is why.")
replies[:] = [fact_slides]; verdicts[:] = [{"ok": True, "issues": []}]; prompts.clear()
found = None
for date in [f"2027-04-{d:02d}" for d in range(1, 13)]:
    taste, fact = ca.pick_flavor(date, "chatbot")
    if taste["id"] == "factual-source":
        found = (date, taste, fact); break
    save(date, taste["id"])
assert found and found[2] == FACT
car, why = ca.build(plan, bot, brand, "g", found[0])
assert car and car["fact_id"] == "f1" and "FACT (verified by the owner" in prompts[0] and FACT["claim"] in prompts[0]
ca.facts_for = real_facts
shutil.rmtree(config.DRAFTS); config.DRAFTS.mkdir()

# ---- 5. slides: drawn at 1080x1350 in the day's family colour; hook, problem, solution, (diagram), CTA; Bluesky gets 4
media = ROOT / "data" / "media" / "_carousel_test"
shutil.rmtree(media, ignore_errors=True); media.mkdir(parents=True)
real_media = config.MEDIA
config.MEDIA = media
def hook(date):
    with cards.accent((0, 212, 255)):
        cards.render({"style": "bold", "headline": "Your phone buzzes at 11 PM.", "highlight": [], "sub": "x", "chat": [], "cta": 'DM "BOT"', "tag": "T"}, media / f"{date}.jpg")
    return str((media / f"{date}.jpg").relative_to(ROOT))
car6 = {"flavor": "myth-bust", "fact_id": None, "checked": True, "diagram": False, "slides": norm(GOOD)}
res = carousel.render(car6, bot, "2026-11-30", hook("2026-11-30"), style_id="glass-ui")
assert res["roles"] == ["hook", "problem", "problem", "solution", "solution", "cta"] and res["bluesky"] == [0, 1, 3, 5] and len(res["paths"]) == len(res["alts"]) == 6
for rel in res["paths"]:
    assert Image.open(ROOT / rel).size == (1080, 1350) and os.path.getsize(ROOT / rel) > 15000, rel
assert res["alts"][1].startswith("Slide 2 of 6:") and res["slides"][-1]["headline"] == "DM BOT"
def count(path, rgb, tol=14):
    im = Image.open(path).convert("RGB")
    return sum(1 for px in im.getdata() if all(abs(px[i] - rgb[i]) <= tol for i in range(3)))
assert count(ROOT / res["paths"][1], (0, 212, 255)) > 800, "content slides use the family colour"
res_plain = carousel.render(car6, bot, "2026-11-29", hook("2026-11-29"), style_id=None)
assert count(ROOT / res_plain["paths"][1], (255, 214, 10)) > 800 and count(ROOT / res_plain["paths"][1], (0, 212, 255)) < 50
car7 = dict(car6, flavor="how-it-works", diagram=True)
res7 = carousel.render(car7, bot, "2026-11-28", hook("2026-11-28"), style_id="glass-ui")
assert res7["roles"] == ["hook", "problem", "problem", "solution", "solution", "diagram", "cta"] and res7["bluesky"] == [0, 1, 3, 6] and len(res7["paths"]) == 7
assert res7["alts"][5].startswith("Slide 6 of 7:") and "DM BOT" in res7["alts"][5]
car5 = dict(car6, slides=norm([GOOD[0], GOOD[1], GOOD[3], GOOD[4], GOOD[5]]))
res5 = carousel.render(car5, bot, "2026-11-27", hook("2026-11-27"), style_id="glass-ui")
assert res5["roles"] == ["hook", "problem", "solution", "solution", "cta"] and res5["bluesky"] == [0, 1, 2, 4]

# ---- 6. media pruning: old files go, files a pending draft uses stay
old = ["2026-09-01.jpg", "2026-09-01-s2.jpg", "2026-09-02.jpg"]
for n in old:
    (media / n).write_bytes(b"x")
config.save_json(config.DRAFTS / "2026-09-02.json", {"date": "2026-09-02", "status": "pending", "image": {"path": "data/media/_carousel_test/2026-09-02.jpg"}, "carousel": {"paths": []}})
removed = carousel.prune_media("2026-11-30")
assert removed == 2 and not (media / "2026-09-01.jpg").exists() and (media / "2026-09-02.jpg").exists() and (media / "2026-11-28.jpg").exists()
shutil.rmtree(config.DRAFTS); config.DRAFTS.mkdir()

# ---- 7. publishing adapters
queries = []
buffer._gql = lambda q: queries.append(q) or {"createPost": {"post": {"id": "p", "dueAt": "now"}}}
buffer.create_post("c", "t", ["https://x/1.jpg", "https://x/2.jpg", "https://x/3.jpg"])
a = re.findall(r'url: "([^"]+)"', queries[-1])
assert a == ["https://x/1.jpg", "https://x/2.jpg", "https://x/3.jpg"] and "mode: shareNow" in queries[-1], queries[-1]
buffer.create_post("c", "t", "https://x/one.jpg")
assert re.findall(r'url: "([^"]+)"', queries[-1]) == ["https://x/one.jpg"]

sent = {}
class R:
    ok, status_code, text = True, 200, ""
    def __init__(self, j=None): self._j = j or {}
    def json(self): return self._j
    def raise_for_status(self): pass
os.environ["ZERNIO_API_KEY"] = "k"
publish.requests.get = lambda *a, **k: R({"accounts": [{"platform": "instagram", "_id": "a1"}]})
publish.requests.post = lambda url, **k: sent.update(body=k["json"]) or R({"post": {"_id": "z"}})
imgs = [{"url": f"https://x/{i}.jpg", "path": f"p{i}.jpg", "alt": f"alt{i}"} for i in range(5)]
publish.Zernio().post("instagram", "t", "https://x/0.jpg", "p0.jpg", images=imgs)
assert [m["url"] for m in sent["body"]["mediaItems"]] == [i["url"] for i in imgs], "the order of mediaItems is the slide order"
publish.Zernio().post("instagram", "t", "https://x/0.jpg", "p0.jpg")
assert sent["body"]["mediaItems"] == [{"url": "https://x/0.jpg", "type": "image"}]

posted = []
def bsky_post(url, **k):
    if url.endswith("createSession"): return R({"accessJwt": "j", "did": "d"})
    if url.endswith("uploadBlob"): posted.append(("blob", len(k["data"]))); return R({"blob": {"ref": len(posted)}})
    if url.endswith("createRecord"): sent["record"] = k["json"]["record"]; return R({"uri": "at://x"})
direct.requests.post = bsky_post
os.environ.update(BLUESKY_HANDLE="h", BLUESKY_APP_PASSWORD="p")
files = []
for i in range(6):
    f = tmp / f"s{i}.jpg"; Image.new("RGB", (1080, 1350), (i * 30, 90, 160)).save(f, "JPEG", quality=90); files.append(str(f))
direct.bluesky("hello", files[0], alt="a", images=[{"path": p, "alt": f"alt {i}"} for i, p in enumerate(files)])
emb = sent["record"]["embed"]["images"]
assert len(emb) == 4 and [e["alt"] for e in emb] == ["alt 0", "alt 1", "alt 2", "alt 3"] and len([b for b in posted if b[0] == "blob"]) == 4, "Bluesky's maximum is 4 images"
posted.clear(); direct.bluesky("hello", files[0], alt="solo")
assert len(sent["record"]["embed"]["images"]) == 1 and sent["record"]["embed"]["images"][0]["alt"] == "solo"
assert direct._blob(files[0]) and len(direct._blob(files[0])) < 950_000

# ---- 8. publish_draft: every slide to Instagram and LinkedIn, 4 to Bluesky, only tools that can, single image as the fallback
calls = []
def make(name, multi, fail_multi=False, platforms=None):
    class P:
        secrets = []
        def post(self, platform, text, image_url, image_path, images=None):
            calls.append((name, platform, [i["url"] for i in images] if images else None, image_url))
            if images and fail_multi:
                raise RuntimeError("carousel rejected")
            return "ok"
    P.name, P.multi_image = name, multi
    if platforms: P.platforms = platforms
    return P
class Plain:                                       # an adapter written before carousels: no `images` parameter at all
    secrets, name = [], "plain"
    def post(self, platform, text, image_url, image_path):
        calls.append(("plain", platform, None, image_url)); return "ok"
paths = [f"data/media/2026-11-30{'' if i == 0 else f'-s{i + 1}'}.jpg" for i in range(6)]
draft = {"posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}, "image": {"path": paths[0]}, "hooks": [{"text": "h"}], "linkedin_format": "image",
         "carousel": {"paths": paths, "alts": [f"alt{i}" for i in range(6)], "bluesky": [0, 1, 3, 5]}}
publish.choose_order = lambda provs, today=None: list(provs)
publish.choose_linkedin_order = lambda provs, general: list(general)
def run(classes, d=draft):
    calls.clear(); publish.PROVIDERS = classes
    return publish.publish_draft(d)
raw = lambda rel: f"https://raw.githubusercontent.com/{config.REPO}/{config.BRANCH}/{rel}"
res = run([Plain, make("multi", True)])
byp = {c[1]: c for c in calls}
assert all(r["ok"] for r in res.values()) and "(6 slides)" in res["instagram"]["detail"] and "(4 slides)" in res["bluesky"]["detail"]
assert byp["instagram"][2] == [raw(p) for p in paths] and byp["linkedin"][2] == [raw(p) for p in paths], "every slide, in order"
assert byp["bluesky"][2] == [raw(paths[i]) for i in (0, 1, 3, 5)], "Bluesky: hook, first problem, first solution, CTA"
assert not any(c[0] == "plain" for c in calls), "a tool that cannot post several images is skipped for a carousel"
res = run([make("multi", True, fail_multi=True), Plain])
assert all(r["ok"] for r in res.values()) and "single image; carousel failed: multi: carousel rejected" in res["instagram"]["detail"]
ig = [c for c in calls if c[1] == "instagram"]
assert ig[0][2] == [raw(p) for p in paths] and ig[1][2] is None and ig[1][3] == raw(paths[0]), "the carousel is tried first, then the hook image goes out on its own"
res = run([Plain])
assert all(r["ok"] for r in res.values()) and "carousel failed" in res["instagram"]["detail"]
d2 = dict(draft, linkedin_format="text")                                  # LinkedIn text-only day: no images at all
res = run([make("multi", True)], d2)
assert [c for c in calls if c[1] == "linkedin"][0][2:] == (None, None)
d3 = dict(draft, instagram_mode="manual_reel")                            # Wednesday: Instagram is the manual reel
run([make("multi", True)], d3)
assert "instagram" not in {c[1] for c in calls}
d4 = {k: v for k, v in draft.items() if k != "carousel"}                  # no carousel: exactly the old behaviour, old adapter signature included
res = run([Plain], d4)
assert all(r["ok"] for r in res.values()) and all(c[2] is None for c in calls)
res = run([make("multi", True)], dict(draft, carousel={"paths": paths[:1]}))   # one slide is not a carousel
assert all(c[2] is None for c in calls)

# ---- 9. Telegram album
api = []
tg._api = lambda method, **k: api.append((method, k)) or {"ok": True}
tg.chat_id = lambda: "1"
tg.send_media_group([str(tmp / f"s{i}.jpg") for i in range(6)] + [str(tmp / "s0.jpg")] * 6, "A" * 2000)
method, kw = api[-1]
media_items = json.loads(kw["data"]["media"])
assert method == "sendMediaGroup" and len(media_items) == 10 and len(kw["files"]) == 10, "Telegram albums hold at most 10"
assert media_items[0]["caption"] == "A" * 1000 and all("caption" not in m for m in media_items[1:]) and media_items[3]["media"] == "attach://f3"
assert all(f.closed for f in kw["files"].values())

# ---- 10. a full daily run: planned after the service check, hook shared, slides drawn, album before Approve, single-image fallback, kill switch
from src import run_daily
config.DATA, config.MEDIA = tmp, media
seen, events, WARN = [], [], run_daily.WARNINGS
fit_ok = lambda p: {"service_id": "chatbot", "confidence": "high"}
def groq(p, s="", **k):
    if "Hook library" in p:
        return json.dumps({"idea_id": None, "problem_id": None, "angle_type": "story", "topic": "Late replies", "angle": "a", "key_points": ["x"], "hooks": [{"style": "question", "text": "Original hook?"}],
                           "chosen_hook": 0, "image_idea": "i"})
    return json.dumps({"ok": True, "issues": [], "revised": {}, "ad_score": 3, "notes": ""}) if "JSON" in p else "guidance"
def gemma(p, s="", **k):
    if "List 6 DIFFERENT" in p:
        return json.dumps({"problems": []})
    return json.dumps({"topics": [{"topic": "t", "angle": "a", "why_it_matters": "w"}]}) if "JSON" in p else "img prompt"
state = {"carousel": "good", "pid": 0}
def gem(p, s="", **k):
    seen.append(p)
    if "STRICT ORDER" in p:
        return json.dumps({"slides": GOOD if state["carousel"] == "good" else []})
    return json.dumps({"instagram": "ig", "linkedin": "li", "bluesky": "bs", "replies": []})
def fcm(p, s="", **k):
    if '"service_id"' in p: return json.dumps({"service_id": "chatbot", "confidence": "high"})
    if "Fact-check this carousel" in p: return json.dumps({"ok": True, "issues": []})
    return json.dumps({"ok": True, "issues": [], "revised": {}})
llm.groq, llm.gemma, llm.gemini, llm.factcheck_model = groq, gemma, gem, fcm
tg.send = lambda text, buttons=None, reply_to=None: events.append(("text", text))
tg.send_photo = lambda path, caption="": events.append(("photo", str(path), caption))
tg.send_media_group = lambda paths, caption="": events.append(("album", [str(p) for p in paths], caption))
import src.agents.image as image_mod
def fake_image(plan, focus, date, guidance=""):
    p = media / f"{date}.jpg"
    with cards.accent((0, 212, 255)):
        cards.render({"style": "bold", "headline": plan["hooks"][plan.get("chosen_hook", 0)]["text"], "highlight": [], "sub": "", "chat": [], "cta": 'DM "BOT"', "tag": "T"}, p)
    return {"prompt": "hook prompt", "path": str(p.relative_to(ROOT)), "engine": "visual:x", "style_id": "glass-ui"}
image_mod.run = fake_image
run_daily.pick_focus = lambda brand, history: bot
dpath = config.DRAFTS / f"{run_daily.today}.json"

WARN.clear(); events.clear(); seen.clear()
run_daily.main()
dr = config.load_json(dpath, {})
c = dr["carousel"]
assert c["flavor"] in usable and len(c["paths"]) == 6 and c["roles"] == ["hook", "problem", "problem", "solution", "solution", "cta"] and c["bluesky"] == [0, 1, 3, 5]
assert all((ROOT / p).exists() for p in c["paths"]) and dr["image"]["path"] == c["paths"][0]
assert dr["hooks"][0]["text"] == GOOD[0]["headline"], "the carousel's hook is the post's hook, so the captions and the first slide agree"
assert [e for e in events if e[0] == "album"][0][1] == [str(ROOT / p) for p in c["paths"]] and "[CAROUSEL, 6 slides | taste:" in [e for e in events if e[0] == "album"][0][2]
assert events[-1][0] == "text" and "Approve" in events[-1][1] and events[-2][0] == "photo" and events[-2][2].startswith("[SERVICE EXPLAINER]"), "no diagram slide in this taste, so the separate explainer still follows"
assert not [w for w in WARN if "carousel" in w] and not any(e[0] == "photo" and e[2] == "hook prompt" for e in events)
assert learning._attrs(dr, "instagram", "image")["carousel_flavor"] == c["flavor"] and learning._attrs(dr, "instagram", "image")["slides"] == 6

dpath.unlink(); WARN.clear(); events.clear()                              # the planner fails twice: a single image, and it says why
state["carousel"] = "bad"
run_daily.main()
dr = config.load_json(dpath, {})
assert dr["carousel"] is None and any("carousel skipped (single image instead)" in w for w in WARN)
assert set((dr.get("virality") or {}).get("platforms", {})) == set(config.PLATFORMS) and not any(w.startswith("virality") for w in WARN)     # the advisory hint is saved on every draft
assert any(e[0] == "photo" and e[2] == "hook prompt" for e in events) and not any(e[0] == "album" for e in events)
assert learning._attrs(dr, "instagram", "image")["slides"] == 1

dpath.unlink(); WARN.clear(); events.clear(); seen.clear()                # the kill switch: CAROUSEL=0 never calls the planner
config.CAROUSEL = False
run_daily.main()
assert not any("STRICT ORDER" in p for p in seen) and config.load_json(dpath, {})["carousel"] is None and not any(e[0] == "album" for e in events) and not [w for w in WARN if "carousel" in w]
config.CAROUSEL = True
config.MEDIA = real_media
shutil.rmtree(media, ignore_errors=True)
print("carousel test passed: fixed order, rotating tastes, facts-only 'X said', slides + Bluesky subset, multi-image publishing with fallback, Telegram album, full daily run, kill switch")
