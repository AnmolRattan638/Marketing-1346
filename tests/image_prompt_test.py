"""Offline test: image prompts that describe a layout (the grey 'four sections' panel of 2026-10-15) are rejected; a concrete scene is used instead."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import llm
from src.agents import image

bad = ("Left: laptop open on reclaimed wood table in the upper left, blank clean page, ceramic mug, warm window light, shallow depth of field, yellow rim highlighted. "
       "Right: narrow vertical panel divided into four equal sections, minimalist grid, lower 40% calm uncluttered, warm tone, premium photography style.")
good = ("A laptop on a wooden desk showing a bright city map with glowing yellow location pins over small shopfronts, a ceramic mug beside it, "
        "warm window light, shallow depth of field, calm lower area")
assert image.LAYOUT_WORDS.search(bad) and not image.LAYOUT_WORDS.search(good)
for ok in ("A phone on a cafe counter at night lit by unread chat bubbles, warm lamp light, shallow depth of field, calm uncluttered lower area",
           "Laptop in the upper left of the frame beside a mug, warm light, shallow depth of field, calm lower area on a wooden table"):
    assert not image.LAYOUT_WORDS.search(ok), ok          # 'upper left' as a position is fine, only layouts are rejected

plan = {"hooks": [{"text": "Stop hunting leads. Start spotting them."}], "chosen_hook": 0, "topic": "3 places to find businesses", "image_idea": "split screen with four panels"}
focus = {"id": "lead_gen", "name": "Lead generation (LocalSignal)"}
calls = []

def ask(*replies):
    calls.clear(); it = iter(replies)
    def gemma(prompt, system="", **k):
        calls.append(prompt)
        r = next(it)
        if isinstance(r, Exception): raise r
        return f"<prompt>{r}</prompt>"
    llm.gemma = gemma

ask(good)                                              # good first time: one call, kept
p = image.picture_prompt(plan, focus, {}, "")
assert len(calls) == 1 and p.startswith(good) and "Ultra-sharp 4K" in p
assert "NEVER describe a layout" in calls[0]           # the instruction is in the request

ask(bad, good)                                         # layout first, usable second: retried once with a correction
p = image.picture_prompt(plan, focus, {}, "")
assert len(calls) == 2 and "DESCRIBED A LAYOUT" in calls[1] and p.startswith(good)

ask(bad, bad)                                          # unusable twice: concrete lead-gen scene, never a layout
p = image.picture_prompt(plan, focus, {}, "")
assert len(calls) == 2 and "city map" in p and "pins" in p and "Ultra-sharp 4K" in p and not image.LAYOUT_WORDS.search(p.split("Ultra-sharp")[0]), p

ask(RuntimeError("model down"))                        # the prompt model fails: still a real picture, not a plain card
p = image.picture_prompt(plan, {"id": "chatbot", "name": "Chatbot"}, {}, "")
assert "smartphone" in p and "chat bubbles" in p
ask(bad, bad)
assert "laptop" in image.picture_prompt(plan, {"id": "unknown", "name": "X"}, {}, "").lower()
print("image prompt test passed: layout prompts rejected, one retry, concrete scene fallback per service")
