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
