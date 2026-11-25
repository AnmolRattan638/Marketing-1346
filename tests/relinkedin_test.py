"""LinkedIn-only redo: replaces just the LinkedIn post of the pending draft, gives the draft a NEW id so the earlier Approve button can never post the old text, never touches a draft that is not
pending, leaves everything as it was when the writer cannot produce a safe post, and the workflow is wired in the safe order."""
import json, pathlib, stat, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import yaml
from src import config, process_approvals as pa, relinkedin, scriptlessons as SL, tg

TMP = pathlib.Path(tempfile.mkdtemp())
config.DRAFTS, config.DATA = TMP / "drafts", TMP
config.DRAFTS.mkdir()
SL.STATE = TMP / "script_lessons.json"
OLD = "Many small business ads on Instagram look the same.\n\nI build short animated ads for small businesses.\n\nPayment happens only after you approve. DM ADS and tell me what you sell."
INTRO = ("I am Anmol, and my content system once read “24x7” as “24 times 7.”\n\n"
         "I only noticed because the voiceover sounded strange. The script was fine, but the voice said the symbol the way it was written.\n\n"
         "So I went looking and found more. A price ran into the next word. “4K” became “4 thousand”. A slash turned a short phrase into nonsense.\n\n"
         "I built a pronunciation list from those mistakes, and now every script is checked for words the voice would say wrong before anything is recorded.\n\n"
         "It is a small fix, but it taught me something: a system that talks has to be checked by listening, not only by reading.\n\n"
         "If you build things too, I would like to connect and hear what you got wrong first.")

def draft(status="pending"):
    return {"id": "2026-11-25-abc123", "date": "2026-11-25", "created_at": "2026-11-25T02:40:00+00:00", "status": status, "service": "ads", "topic": "t", "linkedin_format": "text",
            "posts": {"instagram": "IG caption", "linkedin": OLD, "bluesky": "BS post"}, "replies": []}
def put(d): (config.DRAFTS / "2026-11-25.json").write_text(json.dumps(d), encoding="utf-8")
def get(): return json.loads((config.DRAFTS / "2026-11-25.json").read_text(encoding="utf-8"))

# 1. success: only LinkedIn changes, the draft gets a new id, a fresh preview and fresh buttons are sent
put(draft()); sent = []
tg.send = lambda text, buttons=None, reply_to=None: sent.append((text, buttons))
assert relinkedin.redo(ask=lambda p, s: {"post": INTRO, "pitch_sentences": []}) == 0
d = get()
assert "pronunciation list" in d["posts"]["linkedin"] and "DM" not in d["posts"]["linkedin"] and d["status"] == "pending"
assert d["posts"]["instagram"] == "IG caption" and d["posts"]["bluesky"] == "BS post" and d["service"] == "ads" and d["linkedin_format"] == "text", "nothing else changed"
assert d["id"] != "2026-11-25-abc123" and d["id"].startswith("2026-11-25-") and d["created_at"] > "2026-11-25T02:40:00+00:00"
assert d["linkedin_mode"] == "intro" and d["linkedin_topic"] == "who-i-am" and d["linkedin_replaced"] == [OLD]
assert sent[0][0].startswith("[LINKEDIN, NEW POST (intro), replaces the earlier one]") and "pronunciation list" in sent[0][0]
assert sent[1][1] == [{"text": "Approve", "callback_data": f"approve:{d['id']}"}, {"text": "Reject", "callback_data": f"reject:{d['id']}"}] and "no longer works" in sent[1][0]

# 2. THE SAFETY PROPERTY: the earlier message's Approve posts nothing; the new one posts the new text
pa.authorized = lambda chat, sender: True
answers, published = [], []
pa.tg.answer = lambda cb_id, text: answers.append(text)
pa.publish.publish_draft = lambda dr: published.append(json.loads(json.dumps(dr))) or {"linkedin": {"ok": True, "detail": "posted"}}
cb = lambda data: {"id": "1", "message": {"chat": {"id": 1}}, "from": {"id": 1}, "data": data}
pa.handle(cb("approve:2026-11-25-abc123"))
assert not published and "older draft" in answers[-1], (published, answers)
assert get()["status"] == "pending", "the old button changed nothing"
pa.handle(cb(f"approve:{d['id']}"))
assert len(published) == 1 and "pronunciation list" in published[0]["posts"]["linkedin"] and "DM ADS" not in published[0]["posts"]["linkedin"], "the new button posts the NEW text"
assert published[0]["posts"]["instagram"] == "IG caption", "and the rest as before"
assert get()["status"] == "published"

# 3. the writer cannot produce a safe post: the draft is byte for byte untouched, the earlier buttons still work, you are told why
put(draft()); before = (config.DRAFTS / "2026-11-25.json").read_text(encoding="utf-8"); sent.clear()
assert relinkedin.redo(ask=lambda p, s: {"post": "Small businesses need DM ADS now!"}) == 2
assert (config.DRAFTS / "2026-11-25.json").read_text(encoding="utf-8") == before
assert len(sent) == 1 and "changed nothing" in sent[0][0] and "still work" in sent[0][0] and sent[0][1] is None and "linkedin[" in sent[0][0], sent
# 4. a draft that is not pending is never touched
for status in ("published", "publishing", "rejected", "partial", "failed"):
    put(draft(status)); before = (config.DRAFTS / "2026-11-25.json").read_text(encoding="utf-8"); sent.clear()
    assert relinkedin.redo(ask=lambda p, s: {"post": INTRO}) == relinkedin.NOT_PENDING, status
    assert (config.DRAFTS / "2026-11-25.json").read_text(encoding="utf-8") == before and status in sent[0][0] and "nothing to redo" in sent[0][0]
(config.DRAFTS / "2026-11-25.json").unlink(); sent.clear()
assert relinkedin.redo(ask=lambda p, s: {"post": INTRO}) == relinkedin.NOT_PENDING and "no saved draft" in sent[0][0]
# 5. --check
put(draft()); sent.clear(); sys.argv = ["x", "--check"]
relinkedin.main(); assert not sent
put(draft("published"))
try:
    relinkedin.main(); assert False
except SystemExit as e:
    assert e.code == relinkedin.NOT_PENDING and "published" in sent[0][0]

# 6. the workflow: check -> stop old listeners -> pull -> write -> save -> fresh listener, with its own concurrency group
root = config.ROOT
wf = yaml.safe_load((root / ".github" / "workflows" / "linkedin-redo.yml").read_text(encoding="utf-8"))
job = wf["jobs"]["redo"]; steps = job["steps"]; names = [s.get("name", "") for s in steps]
assert list(wf[True]) == ["workflow_dispatch"] and wf["permissions"]["actions"] == "write" and wf["permissions"]["contents"] == "write"
assert wf["concurrency"]["group"] == "linkedin-redo", "must not share the 'approvals' group: a listener holds it for hours"
order = [next(i for i, n in enumerate(names) if n.startswith(p)) for p in ("Is there a pending", "Stop the runs", "Get the newest", "Write the new", "Save", "Start a fresh listener")]
assert order == sorted(order), names
runs = {n.split(" (")[0]: s.get("run", "") for n, s in zip(names, steps)}
assert "src.relinkedin --check" in runs["Is there a pending draft to redo?"] and "stop_listeners.sh" in runs["Stop the runs still waiting with the old draft"]
assert "git pull --rebase" in runs["Get the newest saved state"] and runs["Write the new LinkedIn post and send the new Approve message"].strip() == "python -m src.relinkedin"
assert "commit_state.sh" in runs["Save"] and "gh workflow run approve-publish.yml" in runs["Start a fresh listener"] and "stop_listeners.sh" in runs["Start a fresh listener"]
for n in ("Save", "Start a fresh listener"):
    s = steps[names.index(next(x for x in names if x.startswith(n)))]
    assert s["if"].startswith("always()") and "steps.check.outcome == 'success'" in s["if"], "runs even if the redo failed, but only after the check passed"
env = job["env"]
assert {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GEMINI_API_KEY", "GH_TOKEN"} <= set(env)
sh = root / "scripts" / "stop_listeners.sh"; body = sh.read_text(encoding="utf-8")
assert sh.stat().st_mode & stat.S_IXUSR and "daily-draft.yml" in body and "approve-publish.yml" in body and "gh run cancel" in body and "in_progress" in body and "linkedin-redo" not in body
print("relinkedin test passed: only LinkedIn changes, old buttons are dead, nothing touched unless pending, safe workflow order")
