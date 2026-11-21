"""Hook formulas: every formula has a working Hinglish example for every service, detection, rotation, prompt block, and the script writer uses them."""
import datetime, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import hooks
from src.agents import scriptwriter as sw

SERVICES = ["website", "chatbot", "animated_ads", "lead_gen", "reel_scripts", "seo_blogs"]
fs = hooks.formulas()
assert len(fs) == 9 and len({f["id"] for f in fs}) == 9
for f in fs:
    assert set(f["examples"]) == set(SERVICES), f["id"]
    for svc, ex in f["examples"].items():
        n = len(ex.split())
        assert sw.HOOK_WORDS[0] <= n <= sw.HOOK_WORDS[1], (f["id"], svc, n, ex)               # fits the hook length rules
        assert hooks.formula_of(ex) == f["id"], (f["id"], svc, ex, hooks.formula_of(ex))      # the detector recognises its own example
        assert not sw.BAD_OPEN.search(ex) and not sw.GENERIC.search(ex) and not sw.PROMISE.search(ex), ex
        assert not re.search(r"\d", ex) and ex.endswith("…"), ex                               # no digits (no fake stats), open loop
assert hooks.formula_of("Aaj ka plan batata hoon") == ""

# rotation: three per day, different from the next day, all nine used within three days, second reel differs from the first
d = datetime.date(2026, 11, 21)
today = [f["id"] for f in hooks.pick("chatbot", d)]
assert len(today) == 3 and today != [f["id"] for f in hooks.pick("chatbot", d + datetime.timedelta(days=1))]
assert len({f["id"] for k in range(3) for f in hooks.pick("chatbot", d + datetime.timedelta(days=k))}) == 9
assert set(today) != {f["id"] for f in hooks.pick("chatbot", d, slot=1)}
assert all(f["example"] for f in hooks.pick("website", d))

b = hooks.block("chatbot", d)
assert "OPEN LOOP" in b and today and all(hooks.formulas()[0]["english"] in b or True for _ in [0]) and all(f["english"] in b for f in hooks.pick("chatbot", d))
assert hooks.block("nonexistent", d)                                                          # an unknown service still gets the formulas (without an example)

# script writer: the prompt carries the block, a formula hook wins the pick and is labelled
import json, tempfile
from src import scriptlessons as SL
SL.STATE = pathlib.Path(tempfile.mkdtemp()) / "l.json"
sw.problems = lambda *a, **k: []
sheet = {"date": "2026-11-21", "keyword": "BOT", "topic": "chatbot", "facts": [{"id": "f1", "claim": "x", "source": "y"}]}
focus = {"id": "chatbot", "name": "WhatsApp chatbot", "dm_keyword": "BOT"}
style = {"id": "x", "name": "n", "how": "h", "beats": ["pain", "cta"]}
data = {"hooks": ["Raat ko customer message karta hai aur koi jawab nahi deta", "Bohot kam business raat ke messages ka ye jawab dete hain..."],
        "beats": [{"beat": "pain", "line": "x", "screen": "Raat ke messages ka kya", "facts": []}, {"beat": "cta", "line": "Comment BOT likho, main checklist DM mein bhejunga", "screen": "Comment BOT", "facts": []}], "cta": "Comment BOT"}
seen = []
script = sw.run(sheet, focus, style, ask=lambda p, *a, **k: seen.append(p) or json.dumps(data), max_tries=1)
assert "PROVEN HOOK FORMULAS" in seen[0], "the writer prompt carries the formulas"
assert script["hook_formula"] == "nobody" and script["hook"].startswith("Bohot kam"), (script["hook"], script["hook_formula"])
print("hook formulas test passed")
