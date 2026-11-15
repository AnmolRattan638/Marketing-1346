"""A video (or Drive link) sent to the bot starts the Re-edit workflow with your words."""
import os, sys, pathlib, subprocess, types
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ["TELEGRAM_CHAT_ID"] = "42"
from src import process_approvals as pa, tg

sent, ran = [], []
tg.send = lambda text, buttons=None, reply_to=None: sent.append(text)
subprocess.run = lambda cmd, **k: (ran.append(cmd), types.SimpleNamespace(returncode=0, stdout="", stderr=""))[1]
chat = {"id": 42}
def msg(**kw): return {"chat": chat, "from": {"id": 42}, "message_id": 7, **kw}

# caption = instructions: starts at once
pa.STATE = {}
pa.handle_message(msg(video={"file_id": "F1", "file_size": 5_000_000}, caption="explain 3 steps at 12 s"))
cmd = ran[-1]
assert "re-edit.yml" in cmd and "video_url=telegram:F1" in cmd and "instructions=explain 3 steps at 12 s" in cmd and "Editing now" in sent[-1]

# no caption: bot asks, the next plain message is the instructions
ran.clear(); pa.handle_message(msg(video={"file_id": "F2", "file_size": 1000}))
assert not ran and "send what to change" in sent[-1] and pa.STATE["edit_video"]["file_id"] == "F2"
pa.handle_message(msg(text="zoom in on the phone number"))
assert "video_url=telegram:F2" in ran[-1] and "edit_video" not in pa.STATE
ran.clear(); pa.handle_message(msg(text="hello there"))          # ordinary chatter does nothing
assert not ran

# too big for a bot, a Drive link instead, a stranger ignored, a stale pending video ignored
pa.handle_message(msg(video={"file_id": "F3", "file_size": 30_000_000}, caption="x")); assert not ran and "20 MB" in sent[-1]
pa.handle_message(msg(text="https://drive.google.com/file/d/abc/view add a title at 3 s"))
assert "video_url=https://drive.google.com/file/d/abc/view" in ran[-1] and "instructions=add a title at 3 s" in ran[-1]
ran.clear(); pa.handle_message({"chat": {"id": 999}, "from": {"id": 1}, "video": {"file_id": "X"}, "caption": "hack"}); assert not ran
pa.STATE["edit_video"] = {"file_id": "OLD", "at": 0}; pa.handle_message(msg(text="late")); assert not ran

# the agent side understands telegram:<file_id>
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import reedit
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
try: reedit.fetch("telegram:F1", pathlib.Path("/tmp/x/o.mp4")); assert False
except RuntimeError as e: assert "TELEGRAM_BOT_TOKEN" in str(e)
print("telegram reedit ok")
