"""Offline test of the 'tap after the reminder does nothing' fix: GitHub runs scheduled workflows only every few hours, so a chain of follow-up runs now keeps
listening for the tap. The reminder no longer promises a timing, and a draft counts as waiting only while Telegram still delivers its button."""
import datetime as dt, json, pathlib, re, shutil, sys, tempfile, types
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import yaml
from src import config, process_approvals as pa

ROOT = config.ROOT
UTC = dt.timezone.utc
now = dt.datetime.now(UTC)
tmp = pathlib.Path(tempfile.mkdtemp())
config.DATA, config.DRAFTS = tmp, tmp / "drafts"

def drafts(*items):
    shutil.rmtree(config.DRAFTS, ignore_errors=True)
    config.DRAFTS.mkdir(parents=True)
    for date, status, created in items:
        d = {"id": f"{date}-x", "date": date, "status": status}
        if created is not None:
            d["created_at"] = created.isoformat(timespec="seconds")
        config.save_json(config.DRAFTS / f"{date}.json", d)

# ---- 1. a draft is "waiting" only while Telegram still delivers its tap (24 hours), whatever the date says
ago = lambda h: now - dt.timedelta(hours=h)
drafts(("2026-10-20", "pending", ago(1)));                     assert pa.pending_recent() is True
drafts(("2026-10-20", "pending", ago(23)));                    assert pa.pending_recent() is True, "still inside the window, even after midnight UTC"
drafts(("2026-10-20", "pending", ago(24)));                    assert pa.pending_recent() is False, "Telegram no longer delivers the old Approve button"
for status in ("published", "rejected", "publishing", "partial"):
    drafts(("2026-10-20", status, ago(1)));                    assert pa.pending_recent() is False, status
drafts(("2026-10-20", "pending", None));                       assert pa.pending_recent() is False, "an old draft without created_at counts from 03:00 UTC on its date"
drafts((now.date().isoformat(), "pending", None));             assert pa.pending_recent() is True
drafts();                                                      assert pa.pending_recent() is False
drafts(("2026-10-01", "pending", ago(2)), ("2026-10-02", "published", ago(1)), ("2026-10-03", "published", ago(1)), ("2026-10-04", "published", ago(1)))
assert pa.pending_recent() is False, "only the latest drafts are looked at"

# ---- 2. --still-pending: the exit code that decides whether another follow-up run is started
def code(*argv):
    sys.argv = ["x", *argv]
    try:
        pa.main()
    except SystemExit as e:
        return e.code
    raise AssertionError("main should have exited")
drafts(("2026-10-20", "pending", ago(2)));                     assert code("--still-pending") == 0
drafts(("2026-10-20", "published", ago(2)));                   assert code("--still-pending") == 1

# ---- 3. the reminder: no timing promise; the follow-up runs stay quiet
notes, ticks = [], iter([0.0] + [1e9] * 50)
pa._notify = notes.append
pa.poll = lambda state, t: None
pa.time = types.SimpleNamespace(time=lambda: next(ticks), sleep=lambda s: None)
def run_wait(seconds, **kw):
    global ticks
    ticks = iter([0.0] + [1e9] * 50)
    notes.clear()
    pa.wait(seconds, **kw)
    return list(notes)
drafts(("2026-10-20", "pending", ago(5)))
assert run_wait(18000) == ["No decision on today's draft after 5h 0m. It stays saved: tap Approve within 24 hours."]
assert run_wait(19800)[0].startswith("No decision on today's draft after 5h 30m.")
assert run_wait(19800, quiet=True) == [], "follow-up runs 1-3 do not repeat the reminder"
drafts(("2026-10-20", "published", ago(5)))
assert run_wait(18000) == [], "no reminder once the draft is decided"
for text in ("minutes", "within about", "10 min"):
    assert text not in "No decision on today's draft after 5h 0m. It stays saved: tap Approve within 24 hours."

# ---- 4. no old timing claim anywhere
files = [*ROOT.glob("src/**/*.py"), ROOT / "README.md", *ROOT.glob(".github/workflows/*.yml")]
for f in files:
    assert not re.search(r"(?i)within about 10 min|every 10 minutes|checks every 10|about 10 minutes", f.read_text()), f

# ---- 5. the workflow chain
ap = yaml.safe_load((ROOT / ".github/workflows/approve-publish.yml").read_text())
dd = yaml.safe_load((ROOT / ".github/workflows/daily-draft.yml").read_text())
ap_text, dd_text = (ROOT / ".github/workflows/approve-publish.yml").read_text(), (ROOT / ".github/workflows/daily-draft.yml").read_text()
on = ap.get("on") or ap.get(True)
assert on["workflow_dispatch"]["inputs"]["hop"]["default"] == "0"
assert ap["permissions"]["actions"] == "write" and dd["permissions"]["actions"] == "write", "needed to start the next follow-up run"
job = ap["jobs"]["approvals"]
assert job["timeout-minutes"] >= 340, "a follow-up run waits 5.5 hours"
names = [s.get("name") for s in job["steps"]]
assert names.index("Keep listening (next follow-up run)") > names.index("Commit state") > names.index("Process approvals and publish")
chain = next(s for s in job["steps"] if s.get("name") == "Keep listening (next follow-up run)")
assert chain["continue-on-error"] is True and "workflow_dispatch" in chain["if"] and "always()" in chain["if"]
assert "--still-pending" in chain["run"] and "gh workflow run approve-publish.yml" in chain["run"] and "hop=$((HOP + 1))" in chain["run"]
proc = next(s for s in job["steps"] if s.get("name") == "Process approvals and publish")
assert "--wait 19800" in proc["run"] and "--quiet" in proc["run"] and "workflow_dispatch" in proc["run"], "only dispatched (follow-up) runs wait; the schedule just polls"
gate = next(s for s in job["steps"] if s.get("id") == "gate")
assert "sleep 10" in gate["run"] and 'github.event_name }}" != "workflow_dispatch"' in gate["run"], "a follow-up started while Daily draft is finishing waits for it instead of skipping"
dstep = next(s for s in dd["jobs"]["draft"]["steps"] if s.get("name") == "Keep listening for your tap (follow-up run)")
dnames = [s.get("name") for s in dd["jobs"]["draft"]["steps"]]
assert dnames.index("Keep listening for your tap (follow-up run)") > dnames.index("Save result")
assert dstep["continue-on-error"] is True and "steps.gen.outcome == 'success'" in dstep["if"] and "-f hop=1" in dstep["run"] and "--still-pending" in dstep["run"]
assert next(s for s in dd["jobs"]["draft"]["steps"] if s.get("name") == "Alert if the run failed")["if"] == "failure()", "a failed hand-over never raises the scary 'do not trust the button' alert"
first = int(re.search(r"--wait (\d+)", dd_text).group(1))
follow, cap = int(re.search(r"--wait (\d+)", ap_text).group(1)), int(re.search(r'"\$\{HOP\}" -lt (\d+)', ap_text).group(1))
assert (first + follow * cap) / 3600 > 24, "the chain covers Telegram's whole 24-hour window"
assert (first + follow) / 3600 < 24 and cap == 4

# ---- 6. drafts are stamped, so the chain stops when Telegram stops delivering
assert '"created_at": dt.datetime.now(dt.timezone.utc)' in (ROOT / "src/run_daily.py").read_text()
print("relay test passed: waiting window by created_at, exit codes, reminder without a timing promise, chain structure covers 24 hours")
