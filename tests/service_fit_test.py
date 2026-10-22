"""Offline test: a post must sell the service in focus (today's SEO-blog draft read like a chatbot ad), a chat mock-up appears only for the chatbot
service, and the day's visual family colours every card type, including the designed chat card."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from PIL import Image
from src import config, llm
from src.agents import cards, fit, image
from src import run_daily

brand = config.services()
by = {s["id"]: s for s in brand["services"]}
seo, bot = by["seo_blogs"], by["chatbot"]

def plan(topic, hook):
    return {"topic": topic, "angle": "a", "hooks": [{"style": "q", "text": hook}], "chosen_hook": 0, "key_points": [], "image_idea": "i"}
drifted = plan("Turning repeat customer questions into automated answers", "Too busy answering repeat questions?")
good = plan("Turning repeat customer questions into blog posts", "Questions customers type into Google about your business")

# ---- 1. the check: only a CONFIDENT mismatch counts; any odd answer lets the post through
def says(**out):
    llm.factcheck_model = lambda p, s="", **k: json.dumps(out)
says(service_id="chatbot", confidence="high")
r = fit.check(drifted, seo, brand)
assert r == {"fits": False, "picked": "chatbot"}, r
assert fit.check(drifted, bot, brand)["fits"] is True, "the same post is fine for the chatbot service"
says(service_id="seo_blogs", confidence="high");  assert fit.check(good, seo, brand)["fits"] is True
says(service_id="chatbot", confidence="low");     assert fit.check(drifted, seo, brand)["fits"] is True, "unsure: not blocked"
says(service_id="made-up", confidence="high");    assert fit.check(drifted, seo, brand)["fits"] is True and fit.check(drifted, seo, brand)["picked"] is None
llm.factcheck_model = lambda p, s="", **k: "[]";  assert fit.check(drifted, seo, brand)["fits"] is True

# ---- 2. the guard in the daily run: retry once, then the curated idea, then a visible warning
calls, verdicts = [], []
fit_agent = run_daily.fit_agent
def fake_check(p, focus, brand):
    v = verdicts.pop(0)
    if isinstance(v, Exception):
        raise v
    return v
fit_agent.check = fake_check
run_daily.analysis.run = lambda topics, focus, guidance, history: (calls.append((topics, guidance)) or plan_for[len(calls)])
MISS, OK = {"fits": False, "picked": "chatbot"}, {"fits": True, "picked": "seo_blogs"}
topics, hist = [{"topic": "t"}], []

plan_for = {}
verdicts[:] = [OK]; run_daily.WARNINGS.clear(); calls.clear()
assert run_daily.ensure_fit(drifted, topics, seo, brand, "G", hist) is drifted and not calls, "a fitting post is untouched"

plan_for = {1: good}
verdicts[:] = [MISS, OK]; calls.clear()
assert run_daily.ensure_fit(drifted, topics, seo, brand, "G", hist) is good and len(calls) == 1
assert "SERVICE FIT" in calls[0][1] and "AI chatbot development" in calls[0][1] and "SEO blog writing" in calls[0][1] and calls[0][0] == topics, calls[0][1]

plan_for = {1: dict(drifted), 2: good}
verdicts[:] = [MISS, MISS, OK]; calls.clear()
assert run_daily.ensure_fit(drifted, topics, seo, brand, "G", hist) is good and len(calls) == 2
only = calls[1][0]
assert len(only) == 1 and only[0]["idea_id"] and only[0]["topic"] == "Turning repeat customer questions into blog posts", "second try uses the curated idea for this service"

plan_for = {1: dict(drifted), 2: dict(drifted)}
verdicts[:] = [MISS, MISS, MISS]; calls.clear(); run_daily.WARNINGS.clear()
out = run_daily.ensure_fit(drifted, topics, seo, brand, "G", hist)
assert out["topic"] == drifted["topic"] and any("service fit" in w and "Check the headline" in w for w in run_daily.WARNINGS), "a post that still drifts is flagged, not hidden"

verdicts[:] = [RuntimeError("model down")]; calls.clear(); run_daily.WARNINGS.clear()
assert run_daily.ensure_fit(drifted, topics, seo, brand, "G", hist) is drifted and not calls, "a failing check never blocks the pipeline"

# ---- 3. a chat mock-up only for the chatbot service
chat_json = json.dumps({"style": "chat", "headline": "Too busy answering repeat questions?", "highlight": ["busy"], "sub": "x",
                        "chat": [{"side": "left", "text": "What are your opening hours?", "time": "10:05 AM"}]})
llm.gemma = lambda p, s="", **k: chat_json
spec = cards.make_spec(drifted, seo, "")
assert spec["style"] == "bold" and spec["chat"] == [] and spec["cta"] == 'DM "BLOG"', spec
spec = cards.make_spec(drifted, bot, "")
assert spec["style"] == "chat" and len(spec["chat"]) == 1 and spec["cta"] == 'DM "BOT"'

# ---- 4. the accent colour: set for the render, always restored, and really used by the designed chat card
default = cards.ACCENT
with cards.accent((1, 2, 3)):
    assert cards.ACCENT == (1, 2, 3)
assert cards.ACCENT == default
try:
    with cards.accent((9, 9, 9)):
        raise RuntimeError("boom")
except RuntimeError:
    pass
assert cards.ACCENT == default, "restored even when the render fails"
with cards.accent(None):
    assert cards.ACCENT == default
tmp = pathlib.Path(tempfile.mkdtemp())
def count(path, rgb, tol=12):
    im = Image.open(path).convert("RGB")
    return sum(1 for px in im.getdata() if all(abs(px[i] - rgb[i]) <= tol for i in range(3)))
with cards.accent((0, 212, 255)):
    cards.render(cards.make_spec(drifted, bot, ""), tmp / "cyan.jpg")
cards.render(cards.make_spec(drifted, bot, ""), tmp / "yellow.jpg")
assert count(tmp / "cyan.jpg", (0, 212, 255)) > 1500 and count(tmp / "cyan.jpg", (255, 214, 10)) < 50, "chat card follows the family colour"
assert count(tmp / "yellow.jpg", (255, 214, 10)) > 1500

# ---- 5. image.run: every card type is rendered inside the day's family colour, and the family is recorded
seen = []
cards.make_spec = lambda plan, focus, guidance="": {"style": "chat" if focus["id"] == "chatbot" else "bold", "headline": "H", "highlight": [], "sub": "", "chat": [], "cta": 'DM "X"', "tag": "T"}
cards.render = lambda spec, path: seen.append(("designed", cards.ACCENT))
image._visual_card = lambda plan, focus, spec, guidance, path, errors, variant=None: seen.append(("visual", cards.ACCENT)) or {"engine": "visual:x", "style_id": variant["id"]}
cfg = json.load(open(config.ROOT / "config/image_style.json"))
v = image.pick_variant("2026-10-22")
assert v["accent_rgb"] and len(v["accent_rgb"]) == 3 and all(0 <= c <= 255 for c in v["accent_rgb"])
r1 = image.run(drifted, bot, "2026-10-22", "")
r2 = image.run(drifted, seo, "2026-10-22", "")
assert seen[0] == ("designed", tuple(v["accent_rgb"])) and seen[1] == ("visual", tuple(v["accent_rgb"])), seen
assert r1["style_id"] == v["id"] and r1["engine"] == "designed_card" and r2["style_id"] == v["id"], "the designed chat card records its family too"
assert cards.ACCENT == default
print("service fit test passed: confident mismatch only, retry then curated idea then warning, chat mock-up only for the chatbot, family colour on every card, family recorded")
