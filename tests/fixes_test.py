"""Offline tests for: merged history, strategist gets brand rules, honest alt text, publisher order, publishing-status guard, sender auth."""
import datetime as dt, json, os, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import config, direct, llm, publish, tg, process_approvals as pa
from src.agents import strategist

tmp = pathlib.Path(tempfile.mkdtemp()); (tmp / "drafts").mkdir()
config.DATA, config.DRAFTS = tmp, tmp / "drafts"
today = dt.date.today().isoformat()
sent = []
tg.send = lambda text, buttons=None: sent.append(text)
tg.answer = lambda *a, **k: None
tg.chat_id = lambda: "1"

# ---- 1. strategist receives the brand rules (and the no-demo / no-niche reminder)
seen = {}
llm.strategist_model = lambda prompt, system="", **k: seen.setdefault("p", prompt) and json.dumps({"stage": "s", "summary": "x", "guidance": "g", "instructions": {}, "manual_tips": []})
strategist.guide([], {}, {"name": "Chatbot"}, today, {"facts_rules": ["NO DEMO CLAIMS unique-marker-123"], "positioning": "freelancer"})
assert "unique-marker-123" in seen["p"] and "free audits" in seen["p"] and "bio" in seen["p"].lower(), "rules missing from strategist prompt"

# ---- 2. history merges drafts that were never recorded in history.json
config.save_json(tmp / "history.json", [{"date": "2026-10-10", "service": "website", "topic": "A", "hook_style": "q", "status": "published"}])
config.save_json(config.DRAFTS / "2026-10-11.json", {"date": "2026-10-11", "service": "chatbot", "topic": "B (rejected by hand)", "status": "rejected"})
config.save_json(config.DRAFTS / "2026-10-10.json", {"date": "2026-10-10", "service": "website", "topic": "A", "hook_style": "q", "status": "published"})
h = config.history()
assert [x["date"] for x in h] == ["2026-10-10", "2026-10-11"] and h[1]["topic"].startswith("B"), h
# a rejected draft replaced the same day: both topics stay 'used'
config.save_json(tmp / "history.json", [{"date": "2026-10-11", "service": "chatbot", "topic": "OLD rejected", "status": "rejected"}])
config.save_json(config.DRAFTS / "2026-10-11.json", {"date": "2026-10-11", "service": "chatbot", "topic": "NEW replacement", "status": "pending"})
topics = [x["topic"] for x in config.history() if x["date"] == "2026-10-11"]
assert "OLD rejected" in topics and "NEW replacement" in topics, topics
from src import run_daily
config.save_json(config.DRAFTS / "2026-10-12.json", {"date": "2026-10-12", "status": "publishing"})
skip, why = run_daily.should_skip(config.DRAFTS / "2026-10-12.json", False)
assert skip and "Check Instagram" in why, (skip, why)
assert run_daily.should_skip(config.DRAFTS / "2026-10-12.json", True)[0] is False       # force still works
(config.DRAFTS / "2026-10-12.json").unlink()
config.save_json(tmp / "history.json", [{"date": "2026-10-10", "service": "website", "topic": "A", "hook_style": "q", "status": "published"}])

# ---- 3. alt text says what the image really is
d = {"hooks": [{"text": "Hook here"}], "chosen_hook": 0, "image": {"ai_generated": False}}
assert publish.image_alt(d) == "Graphic with the text: Hook here"
d["image"]["ai_generated"] = True
assert publish.image_alt(d).startswith("AI-generated") and "Hook here" in publish.image_alt(d)
captured = {}
class FakeResp:
    def __init__(s, j): s._j = j; s.content = b"x"
    def raise_for_status(s): pass
    def json(s): return s._j
def fake_post(url, **kw):
    captured[url.rsplit("/", 1)[-1]] = kw
    return FakeResp({"accessJwt": "t", "did": "d", "blob": {"ref": 1}, "uri": "at://x"})
direct.requests.post = fake_post
os.environ.update(BLUESKY_HANDLE="h", BLUESKY_APP_PASSWORD="p")
img = tmp / "i.jpg"; img.write_bytes(b"\xff\xd8abc")
config.ROOT = tmp
direct.bluesky("hello", "i.jpg", alt="Graphic with the text: Hook here")
alt = captured["com.atproto.repo.createRecord"]["json"]["record"]["embed"]["images"][0]["alt"]
assert alt == "Graphic with the text: Hook here" and "AI-generated" not in alt, alt

# ---- 4. PUBLISHER_ORDER pins tools; unset keeps the daily rotation
class A: name = "a"
class B: name = "b"
class C: name = "c"
os.environ.pop("PUBLISHER_ORDER", None)
r1 = [p.name for p in publish.choose_order([A(), B(), C()], dt.date(2026, 1, 1))]
r2 = [p.name for p in publish.choose_order([A(), B(), C()], dt.date(2026, 1, 2))]
assert sorted(r1) == ["a", "b", "c"] and r1 != r2, (r1, r2)
os.environ["PUBLISHER_ORDER"] = "c, a"
assert [p.name for p in publish.choose_order([A(), B(), C()])] == ["c", "a"]
os.environ["PUBLISHER_ORDER"] = "nonsense"
assert len(publish.choose_order([A(), B(), C()])) == 3          # unknown names fall back to rotation
os.environ.pop("PUBLISHER_ORDER")

# ---- 5. status is 'publishing' on disk BEFORE posting, and a second tap during/after an interrupted run never re-posts
draft = {"id": f"{today}-abc123", "date": today, "status": "pending", "service": "chatbot", "topic": "t",
         "posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}, "image": {"path": None}, "instagram_mode": "manual_reel"}
config.save_json(config.DRAFTS / f"{today}.json", draft)
on_disk = {}
def crashing_publish(dr):
    on_disk["status"] = config.load_json(config.DRAFTS / f"{today}.json", {})["status"]
    raise SystemExit("runner killed mid-publish")
publish.publish_draft = crashing_publish
cb = {"id": "x", "data": f"approve:{today}-abc123", "message": {"chat": {"id": 1}}}
try:
    pa.handle(cb)
except SystemExit:
    pass
assert on_disk["status"] == "publishing", on_disk
posted = []
publish.publish_draft = lambda dr: posted.append(1) or {"linkedin": {"ok": True, "detail": "ok"}}
sent.clear(); pa.handle(cb)
assert not posted and any("posted twice" in s for s in sent), (posted, sent)

# ---- 6. only the owner can approve
config.save_json(config.DRAFTS / f"{today}.json", {**draft, "status": "pending"})
pa.handle({**cb, "from": {"id": 999}})                                      # someone else in a private-chat id mismatch
assert not posted and config.load_json(config.DRAFTS / f"{today}.json", {})["status"] == "pending"
tg.chat_id = lambda: "-100500"                                              # group chat, no allowed user configured
sent.clear(); pa.handle({"id": "x", "data": cb["data"], "message": {"chat": {"id": -100500}}, "from": {"id": 5}})
assert not posted and any("TELEGRAM_ALLOWED_USER_ID" in s for s in sent)
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "5"                                # group chat with the owner configured
pa.handle({"id": "x", "data": cb["data"], "message": {"chat": {"id": -100500}}, "from": {"id": 6}})
assert not posted
pa.handle({"id": "x", "data": cb["data"], "message": {"chat": {"id": -100500}}, "from": {"id": 5}})
assert posted and config.load_json(config.DRAFTS / f"{today}.json", {})["status"] == "published"
print("fixes test passed: strategist rules, merged history, alt text, publisher order, publishing guard, sender auth")
