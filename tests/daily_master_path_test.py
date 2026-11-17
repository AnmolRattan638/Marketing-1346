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


import copy
from src import run_daily, web_research
from src.agents import factsheet, scriptwriter, carousel as car_agent
SHEET = {"ok": True, "facts": [{"id": "f1", "claim": "Firms replying within 5 minutes win 21 times more leads", "figure": "21x", "source": "a.com", "url": "https://a.com/1", "verdict": "verified"}] * 3}
web_research.enabled = lambda: True
web_research.evidence_for = lambda plan, focus: [{"title": "t", "url": "https://a.com/1", "domain": "a.com", "snippet": "s"}]
factsheet.build = lambda *a, **k: SHEET
MASTER = {"style": "myth-bust", "hook": "h", "hooks": [], "cta": "c", "beats": [{"beat": "pain", "line": "Raat 11 baje customer ne message kiya", "screen": "x y", "visual": "v", "facts": []}, {"beat": "cta", "line": "Comment KEYWORD likho", "screen": "x", "visual": "v", "facts": []}], "facts": []}
for mode in ("master_ok", "master_fails", "carousel_none"):
    for k in list(config.DRAFTS.glob("*.json")):
        k.unlink()
    sent.clear()
    run_daily.WARNINGS.clear()
    if mode == "master_fails":
        def boom(*a, **k): raise ValueError("no valid script after targeted repairs - x")
        scriptwriter.run = boom
    else:
        scriptwriter.run = lambda sheet, focus, sty: copy.deepcopy(MASTER)
    slides = [{"role": "hook", "headline": "H", "body": "b"}, {"role": "cta", "headline": "DM X", "body": "b"}]
    car_agent.build = (lambda *a, **k: (None, "none")) if mode == "carousel_none" else (lambda *a, **k: ({"slides": slides, "checked": True}, ""))
    run_daily.main()
    draft = config.load_json(config.DRAFTS / f"{run_daily.today}.json", None)
    assert draft and draft["status"] == "pending", (mode, draft)
    assert sent and sent[-1][1][0]["callback_data"].startswith("approve:"), mode
    if mode == "master_fails":
        assert any("scriptwriter" in w for w in run_daily.WARNINGS), run_daily.WARNINGS
print("daily master-path test passed")

# ---- reel starts in PARALLEL: the master script is handed over the moment it exists
import types, tempfile as _tf, pathlib as _pl
assert run_daily.hand_off_to_video(MASTER, {"id": "chatbot"}) is False      # outside GitHub Actions nothing happens
os.environ.update(GITHUB_ACTIONS="true", GITHUB_TOKEN="t", GITHUB_OUTPUT=str(_pl.Path(_tf.mkdtemp()) / "out"))
config.DATA = _pl.Path(_tf.mkdtemp())
calls = []
run_daily.subprocess.run = lambda cmd, **k: calls.append(("git", cmd)) or types.SimpleNamespace(returncode=0)
run_daily.requests.post = lambda url, **k: calls.append(("post", url, k["json"])) or types.SimpleNamespace(status_code=204)
_r = run_daily.hand_off_to_video(MASTER, {"id": "chatbot"}); assert _r is True, (run_daily.WARNINGS, calls)
assert (config.DATA / "master" / f"{run_daily.today}.json").exists()
assert calls[0][0] == "git" and calls[1][0] == "post" and calls[1][1].endswith("/workflows/video-agent.yml/dispatches"), calls
assert "reel_started=1" in open(os.environ["GITHUB_OUTPUT"]).read()
run_daily.requests.post = lambda url, **k: types.SimpleNamespace(status_code=500)
assert run_daily.hand_off_to_video(MASTER, {"id": "chatbot"}) is False and any("reel handoff" in w for w in run_daily.WARNINGS)
sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import master_script as ms
ms.EARLY = _pl.Path(_tf.mkdtemp()); ms.DRAFTS = _pl.Path(_tf.mkdtemp())
assert ms.load(today="2099-01-01") is None
(ms.EARLY / "2099-01-01.json").write_text(json.dumps({"master_script": MASTER, "service": "chatbot"}))
m = ms.load(today="2099-01-01")
assert m and m["beats"][0]["beat"] == "pain" and m["service"] == "chatbot", "video reads the early script before any draft exists"
print("parallel hand-off test passed")
