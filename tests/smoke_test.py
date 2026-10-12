"""Offline smoke test: stubs every LLM/Telegram/Buffer call and runs the whole daily + approval flow."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import os
os.environ.update(BUFFER_API_KEY='x', ZERNIO_API_KEY='y')
from src import config, llm, tg, buffer, publish

tmp = pathlib.Path(tempfile.mkdtemp())
for n in ("drafts", "media"):
    (tmp / n).mkdir()
config.DATA, config.DRAFTS, config.MEDIA = tmp, tmp / "drafts", tmp / "media"

sent = []
tg.send = lambda text, buttons=None: sent.append((text, buttons))
tg.send_photo = lambda *a, **k: sent.append(("photo", None))
tg.chat_id = lambda: "1"
llm.groq = lambda p, s="", **k: json.dumps(
    {"topic": "t", "angle": "a", "key_points": ["x"], "hooks": [{"style": "q", "text": "Hook?"}], "chosen_hook": 0,
     "image_idea": "i", "ok": True, "issues": [], "revised": {}, "ad_score": 3, "notes": ""}) if "JSON" in p else "guidance"
llm.gemma = lambda p, s="", **k: json.dumps({"topics": [{"topic": "t", "angle": "a", "why_it_matters": "w"}],
                                              "voiceover": "v", "shots": ["s"], "flow_prompt": "f"}) if "JSON" in p else "img prompt"
llm.gemini = lambda p, s="", **k: json.dumps({"instagram": "ig", "linkedin": "li", "bluesky": "bs" * 400, "replies": []})
import src.agents.image as image_mod
image_mod.run = lambda plan, focus, date, guidance="": {"prompt": "p", "path": None}

from src import run_daily
run_daily.main()
draft = config.load_json(config.DRAFTS / f"{run_daily.today}.json", None)
assert draft and draft["status"] == "pending" and len(draft["posts"]["bluesky"]) <= 300, draft
assert sent[-1][1][0]["callback_data"] == f"approve:{draft['id']}"
assert draft["instagram_mode"] in ("manual_reel", "auto_image")
draft["instagram_mode"] = "manual_reel"      # make the rest of this test independent of the weekday
config.save_json(config.DRAFTS / f"{run_daily.today}.json", draft)

buffer.channel_map = lambda: {"linkedin": "c1"}   # bluesky missing in Buffer -> must fall back to Zernio
publish.Zernio.post = lambda self, p, t, u, i: "zernio ok"
buffer.create_post = lambda cid, text, url=None: {"id": cid, "dueAt": "soon"}
from src import process_approvals
process_approvals.handle({"id": "x", "data": f"approve:{draft['id']}", "message": {"chat": {"id": 1}}})
d = config.load_json(config.DRAFTS / f"{run_daily.today}.json", {})
assert d["status"] == "published", d["status"]   # Instagram is a manual reel, so only LinkedIn + Bluesky are auto-posted
assert d["results"]["bluesky"]["ok"] and ("zernio" in d["results"]["bluesky"]["detail"] or "buffer" in d["results"]["bluesky"]["detail"])
print("smoke test passed:", d["results"])
