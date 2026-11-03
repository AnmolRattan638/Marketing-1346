"""The chat card must never come back in a new colour: cooldown on the template, no repeated customer messages, chat ideas become bubbles on a fresh AI scene."""
import datetime, json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from PIL import Image, ImageChops
from src import config
from src.agents import image as im, cards

tmp = pathlib.Path(tempfile.mkdtemp())
config.DRAFTS = tmp
config.MEDIA = tmp / "media"
config.MEDIA.mkdir()
TODAY = datetime.date(2026, 11, 10)


def draft(days_ago, engine, style, chat=(), prompt=None):
    d = TODAY - datetime.timedelta(days=days_ago)
    (tmp / f"{d}.json").write_text(json.dumps({"date": str(d), "image": {"engine": engine, "prompt": prompt, "style_id": "x",
                                               "spec": {"style": style, "chat": [{"text": t} for t in chat]}}}))


def clear():
    for f in tmp.glob("*.json"):
        f.unlink()


# 1) cooldown is about the template, not the palette
clear(); draft(5, "designed_card", "chat", ["Are you open?", "Can I book?"])
assert im.chat_card_recently_used(str(TODAY))
clear(); draft(9, "designed_card", "chat", ["Are you open?", "Can I book?"])
assert not im.chat_card_recently_used(str(TODAY))
clear(); draft(2, "visual:cloudflare", "visual", ["Hello?"])            # a chat OVERLAY on a picture does not restart the cooldown
assert not im.chat_card_recently_used(str(TODAY))

# 2) repeated customer messages are dropped; fewer than two left means no chat post
clear(); draft(12, "designed_card", "chat", ["Hi, are you open today?", "Can I book a slot?"])
spec = {"style": "chat", "headline": "H", "sub": "No reply.", "chat": [{"text": "Hi, are you open today?"}, {"text": "Can I book a slot!"}, {"text": "Price for two?"}]}
assert im.drop_repeated_messages(spec, str(TODAY))["style"] == "bold"
spec["chat"][1]["text"] = "Do you deliver?"
out = im.drop_repeated_messages(spec, str(TODAY))
assert out["style"] == "chat" and [m["text"] for m in out["chat"]] == ["Do you deliver?", "Price for two?"]

# 3) recent scenes reach the picture prompt
clear(); draft(3, "visual:cloudflare", "visual", prompt="A smartphone on a cafe counter at night with unread chat bubbles on its screen glowing softly")
assert "smartphone on a cafe counter" in " ".join(im.recent_scenes(str(TODAY)))

# 4) bubbles are drawn on the picture, and skipped when the headline leaves no room
bg = tmp / "bg.jpg"
Image.new("RGB", (1080, 1350), (20, 30, 60)).save(bg)
base = {"headline": "Busy?", "highlight": [], "sub": "", "cta": 'DM "BOT"', "tag": "T"}
plain = cards.compose_visual(dict(base), bg)
withb = cards.compose_visual(dict(base, chat_overlay=True, chat=[{"text": "Hi, are you open today?", "time": "10:15 AM"}, {"text": "Hello? Anyone there?"}]), bg)
assert ImageChops.difference(plain, withb).getbbox(), "bubbles were not drawn"
long_head = dict(base, headline="Who answers every single WhatsApp message when you are busy with customers all day", chat_overlay=True, chat=[{"text": "Hello?"}])
cards.compose_visual(long_head, bg)                                      # must not crash

# 5) full run: chat card used 3 days ago -> chat idea goes to the AI picture path, and a failed picture gives a bold card, not the chat card
clear(); draft(3, "designed_card", "chat", ["Old message one", "Old message two"])
calls = []
cards.make_spec = lambda plan, focus, guidance="": {"style": "chat", "headline": "H", "highlight": [], "sub": "", "cta": 'DM "X"', "tag": "T",
                                                      "chat": [{"text": "Fresh one"}, {"text": "Fresh two"}]}
im.visuals_enabled = lambda: True
im.pick_variant = lambda date: None
im._visual_card = lambda plan, focus, spec, guidance, path, errors, variant=None, recent=(): calls.append(spec) or {"path": "x", "engine": "visual:test", "spec": spec}
plan = {"topic": "t", "hooks": [{"text": "h"}], "chosen_hook": 0}
focus = {"id": "chatbot", "name": "Chatbot"}
r = im._run(plan, focus, str(TODAY), "", None)
assert calls and calls[0].get("chat_overlay") and r["engine"] == "visual:test"
rendered = []
im._visual_card = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("engines down"))
cards.render = lambda spec, path: rendered.append(spec)
r = im._run(plan, focus, str(TODAY), "", None)
assert rendered and rendered[0]["style"] == "bold" and not rendered[0]["chat"], rendered
# and with no recent chat card the normal designed chat card still runs
clear(); rendered.clear(); calls.clear()
r = im._run(plan, focus, str(TODAY), "", None)
assert not calls and rendered and rendered[0]["style"] == "chat"
print("hook variety test passed: chat-card cooldown, repeated messages dropped, scene avoidance, chat bubbles on AI picture, fallbacks")
