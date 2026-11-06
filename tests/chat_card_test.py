"""Offline test: the chat mock-up card never appears twice in a row (it looked like the same hero image every chatbot day); the prompt cleaner drops tags and labels."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import config
from src.agents import cards, image

tmp = pathlib.Path(tempfile.mkdtemp())
config.DRAFTS = tmp
def draft(date, engine, style=None):
    (tmp / f"{date}.json").write_text(json.dumps({"date": date, "image": {"engine": engine, "style": style}}))
plan = {"hooks": [{"text": "h"}], "chosen_hook": 0, "topic": "t"}
focus = {"id": "chatbot", "name": "Chatbot"}
cards.make_spec = lambda plan, focus, guidance="": {"style": "chat", "headline": "H", "highlight": [], "sub": "", "chat": [{"side": "left", "text": "x"}], "cta": 'DM "BOT"', "tag": "T"}
seen = []
cards.render = lambda spec, path: seen.append("chat-card")
image._visual_card = lambda plan, focus, spec, guidance, path, errors, variant=None: seen.append("ai-picture") or {"engine": "visual:x"}
config.ROOT = tmp; config.MEDIA = tmp / "media"

assert image.recent_card_styles("2026-11-06") == []
image.run(plan, focus, "2026-11-06", ""); assert seen[-1] == "chat-card", "no recent chat card: chat is fine"
draft("2026-11-06", "designed_card", "chat")
image.run(plan, focus, "2026-11-07", ""); assert seen[-1] == "ai-picture", "yesterday was a chat card: use an AI picture"
draft("2026-11-07", "visual:cloudflare", "bold")
image.run(plan, focus, "2026-11-08", ""); assert seen[-1] == "ai-picture", "the chat card was two days ago, still in the window"
draft("2026-11-08", "visual:cloudflare", "bold")
image.run(plan, focus, "2026-11-09", ""); assert seen[-1] == "chat-card", "two picture days in a row: chat card allowed again"

assert image.clean_prompt("<prompt>Subject: a matte laptop. Composition: upper two thirds. Lighting: warm lamp") == "a matte laptop. upper two thirds. warm lamp"
assert "<" not in image.clean_prompt("<prompt>A long scene " + "word " * 300 + "</prompt>", 1000) and len(image.clean_prompt("a " * 600, 1000)) <= 1000
print("chat card test passed: alternates with pictures, window of two drafts, prompt cleaned")
