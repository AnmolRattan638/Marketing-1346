"""Automatic restart after a failed script run: it starts AFTER the lessons are saved, waits first, tells you what went wrong, stops at the limit, never loops, and the workflows are wired in that order."""
import os, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import yaml
from src import config, retry, scriptlessons as SL

SL.STATE = pathlib.Path(tempfile.mkdtemp()) / "script_lessons.json"
SL.record(['fix: pronunciation: "SERP" (heard in: "...Ye SERP dekho...") is written in capitals but has no spelling in the pronunciation list'])
assert retry.recent_mistakes() and "SERP" in retry.recent_mistakes()[0], "today's concrete mistake is what the message quotes"

# 1. the decision
assert retry.decide(1, 3) == 2 and retry.decide(2, 3) == 3 and retry.decide(3, 3) is None and retry.decide(5, 3) is None

# 2. the run: wait, then start the SAME workflow with attempt+1, then tell you
log, sent = [], []
class R:
    def __init__(s, code): s.status_code = code
post_ok = lambda url, headers=None, json=None, timeout=0: (log.append(("post", url, headers, json)), R(204))[1]
sleep = lambda sec: log.append(("sleep", sec))
assert retry.run("daily-draft.yml", attempt=1, max_attempts=3, delay=120, token="T", post=post_ok, send=sent.append, sleep=sleep) == 0
assert log[0] == ("sleep", 120), "it waits first"
kind, url, headers, body = log[1]
assert url == f"https://api.github.com/repos/{config.REPO}/actions/workflows/daily-draft.yml/dispatches" and headers["Authorization"] == "Bearer T" and body == {"ref": "main", "inputs": {"attempt": "2"}}, (url, body)
assert "attempt 2 of 3" in sent[0] and "SERP" in sent[0] and "lessons" in sent[0], sent[0]
# 3. the limit: no more starts, you are told, nothing loops
log.clear(); sent.clear()
assert retry.run("daily-draft.yml", attempt=3, max_attempts=3, token="T", post=post_ok, send=sent.append, sleep=sleep) == 0
assert not log and "failed 3 times in a row" in sent[0] and "SERP" in sent[0], (log, sent)
# 4. problems with the restart itself are reported, never silent
sent.clear()
assert retry.run("daily-draft.yml", attempt=1, token="T", post=lambda *a, **k: R(403), send=sent.append, sleep=sleep) == 1 and "HTTP 403" in sent[0]
sent.clear(); log.clear()
for k in ("GITHUB_TOKEN", "GH_TOKEN"):
    os.environ.pop(k, None)
assert retry.run("daily-draft.yml", attempt=1, token="", post=post_ok, send=sent.append, sleep=sleep) == 1 and "no GitHub token" in sent[0] and not log, (sent, log)
def boom(text): raise RuntimeError("telegram down")
assert retry.run("second-reel.yml", attempt=1, delay=0, token="T", post=post_ok, send=boom, sleep=sleep) == 0, "a broken Telegram setup never blocks the restart"

# 5. the workflows: lessons are saved (always) BEFORE the restart, which only fires when the script stage failed
for wf, state_step in (("daily-draft.yml", "Save draft"), ("second-reel.yml", "Save state")):
    d = yaml.safe_load((config.ROOT / ".github" / "workflows" / wf).read_text(encoding="utf-8"))
    steps = next(iter(d["jobs"].values()))["steps"]
    names = [s.get("name", "") for s in steps]
    i_save = next(i for i, n in enumerate(names) if n.startswith(state_step))
    i_alert = next(i for i, n in enumerate(names) if n.startswith("Alert if the run failed"))
    i_retry = next(i for i, n in enumerate(names) if n.startswith("Start again automatically"))
    assert i_save < i_alert < i_retry, (wf, names)
    assert str(steps[i_save].get("if")).strip() == "always()", "lessons are committed even when the run fails"
    st = steps[i_retry]
    assert str(st["if"]).startswith("failure() &&") and "steps.gen.outcome == 'failure'" in st["if"], "needs failure(): GitHub adds success() to an if with no status function"
    assert any(s.get("id") == "gen" for s in steps), "the script step has the id the condition reads"
    assert st["run"].strip() == f"python -m src.retry --workflow {wf}", st["run"]
    assert "inputs.attempt" in st["env"]["RETRY_ATTEMPT"] and "RETRY_MAX" in st["env"] and "RETRY_DELAY" in st["env"] and "github.token" in st["env"]["GITHUB_TOKEN"]
    inp = d[True]["workflow_dispatch"]["inputs"]["attempt"]
    assert inp["default"] == "1" and inp["required"] is False
print("retry ok: waits, restarts after the lessons are saved, tells you why, stops at the limit")
