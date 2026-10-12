"""Offline test: the wait loop must publish as soon as the Approve tap arrives, then stop."""
import datetime as dt, json, pathlib, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import config, tg, publish, process_approvals as pa

tmp = pathlib.Path(tempfile.mkdtemp()); (tmp / "drafts").mkdir()
config.DATA, config.DRAFTS = tmp, tmp / "drafts"
today = dt.date.today().isoformat()
config.save_json(config.DRAFTS / f"{today}.json", {"date": today, "status": "pending", "service": "chatbot", "topic": "t",
                 "posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}, "image": {"path": None}})
sent, calls = [], {"n": 0}
tg.send = lambda text, buttons=None: sent.append(text)
tg.answer = lambda *a, **k: None
tg.chat_id = lambda: "1"
def fake_updates(offset, timeout=0):
    calls["n"] += 1
    if calls["n"] < 3:
        return []                                   # no tap yet
    return [{"update_id": 7, "callback_query": {"id": "x", "data": f"approve:{today}", "message": {"chat": {"id": 1}}}}]
tg.get_updates = fake_updates
publish.publish_draft = lambda d: {"linkedin": {"ok": True, "detail": "ok"}, "bluesky": {"ok": True, "detail": "ok"}}
t0 = time.time(); pa.wait(60)
d = config.load_json(config.DRAFTS / f"{today}.json", {})
assert d["status"] == "published", d["status"]
assert time.time() - t0 < 10 and calls["n"] == 3, (time.time() - t0, calls)
assert config.load_json(tmp / "tg_state.json", {})["offset"] == 8
assert any("Publish result" in s for s in sent)
print("wait test passed: published after", calls["n"], "polls")

# ---- image sent to the bot becomes today's post image
import io
from PIL import Image
from src.agents import image as image_mod
tmp2 = pathlib.Path(tempfile.mkdtemp()); (tmp2 / "drafts").mkdir(); (tmp2 / "data" / "media").mkdir(parents=True)
config.ROOT, config.DATA, config.DRAFTS, config.MEDIA = tmp2, tmp2 / "data", tmp2 / "drafts", tmp2 / "data" / "media"
config.save_json(config.DRAFTS / f"{today}.json", {"date": today, "status": "pending", "service": "chatbot", "topic": "t",
                 "posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}, "image": {"path": None}})
buf = io.BytesIO(); Image.new("RGBA", (1500, 1500), (200, 30, 30, 255)).save(buf, "PNG")
tg.download_file = lambda fid: buf.getvalue()
commits, sent2 = [], []
pa._commit = lambda m: commits.append(m)
tg.send = lambda text, buttons=None: sent2.append(text)
pa.handle_message({"chat": {"id": 1}, "photo": [{"file_id": "small"}, {"file_id": "big"}], "caption": "design from Adobe"})
d = config.load_json(config.DRAFTS / f"{today}.json", {})
assert d["image"]["engine"] == "user_upload" and d["image"]["ai_generated"] is False, d["image"]
raw = (config.ROOT / d["image"]["path"]).read_bytes()
assert raw[:2] == b"\xff\xd8" and b"trainedAlgorithmicMedia" not in raw and Image.open(io.BytesIO(raw)).size[0] <= 1080
assert commits and any("Image received" in s for s in sent2)
pa.handle_message({"chat": {"id": 1}, "document": {"mime_type": "image/png", "file_id": "f"}, "caption": "ai"})
d = config.load_json(config.DRAFTS / f"{today}.json", {})
assert d["image"]["ai_generated"] is True and b"trainedAlgorithmicMedia" in (config.ROOT / d["image"]["path"]).read_bytes()
pa.handle_message({"chat": {"id": 999}, "photo": [{"file_id": "x"}]})        # other chats are ignored
pa.handle_message({"chat": {"id": 1}, "text": "hello"})                          # plain text is ignored
print("upload test passed: photo -> today's image (not AI-marked), caption 'ai' -> AI-marked")

# ---- a stale button (older message / legacy date-only data) must not approve a newer draft
config.save_json(config.DRAFTS / f"{today}.json", {"id": f"{today}-abc123", "date": today, "status": "pending", "service": "chatbot", "topic": "t",
                 "posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}, "image": {"path": None}, "instagram_mode": "manual_reel"})
calls2 = []
publish.publish_draft = lambda d: calls2.append(1) or {"linkedin": {"ok": True, "detail": "ok"}}
answers = []
tg.answer = lambda cid, text: answers.append(text)
pa.handle({"id": "x", "data": f"approve:{today}", "message": {"chat": {"id": 1}}})          # old format
pa.handle({"id": "x", "data": f"approve:{today}-zzz999", "message": {"chat": {"id": 1}}})    # other draft id
assert not calls2 and config.load_json(config.DRAFTS / f"{today}.json", {})["status"] == "pending" and len(answers) == 2, (calls2, answers)
pa.handle({"id": "x", "data": f"approve:{today}-abc123", "message": {"chat": {"id": 1}}})    # the right one
assert calls2 and config.load_json(config.DRAFTS / f"{today}.json", {})["status"] == "published"
print("stale-button test passed: old taps ignored, matching id publishes")
