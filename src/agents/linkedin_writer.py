"""Agent: the LinkedIn post. A person talking, written only from config/about_me.json, checked by the gate in src/linkedin_story.py, and never an Instagram caption made longer.

Each rejected draft is recorded as a lesson (the exact mistake) and shown to the next attempt; after three failed attempts there is NO LinkedIn post that day rather than a bad one."""
from __future__ import annotations

import json
import re

from .. import linkedin_story as story, llm, scriptlessons

SYS = ("You write LinkedIn posts in the first person for Anmol Rattan, a young builder in India. Plain, warm, specific and curious. You use only the facts you are given and never invent anything: "
       "no clients, no results, no numbers, no names that are not in the facts. You do not sound like an advertisement.")

BRIEF = {
    "story": "Tell ONE true moment and what it taught you. Start inside the moment (what happened), not with a lesson. End with what you do differently now, or what you are still working out.",
    "build": "Show ONE thing you built: what it does in plain words, how it works, and its honest limit. Teach; do not sell. Write it like telling a friend who builds things too.",
    "question": "Share the real situation you are in and ask the readers one genuine question. The post must END with that question. Do not answer it yourself.",
    "intro": "Introduce yourself the way you would at a meetup: who you are, what you have built so far, and that you want to meet people who build things. Warm and plain, no CV list.",
    "pitch": "Write a story or build post as above, PLUS one short paragraph (at most 30% of the post, usually 1 to 2 sentences) saying what you can do for others, using the OFFER below. Calm and plain: no price, no DM, no 'pay after approval', no urgency. List those offer sentences exactly in pitch_sentences.",
}

HOOKS = ("HOOK (the first line only; 18 words or fewer; sentence case): make a reader curious about something TRUE that the post then explains. Good shapes: a specific odd detail "
         "('My content system once read “24x7” as “24 times 7.”'), an honest admission ('I keep making the same mistake with warm leads.'), a real question ('How do you know a lead is real before you message it?'). "
         "Never open with 'Small businesses...', 'Many owners...', 'Are you...', 'Did you know' or a greeting. Never promise something the post does not deliver.")


def prompt(fx: dict, mode: str, topic_id: str, notes: str = "", recent_posts=(), text_only: bool = True) -> str:
    about = {"who": fx["who"], "client_work": fx["client_work"], "goals": fx["goals"]}
    firsts = [p.strip().splitlines()[0] for p in recent_posts if p and p.strip()][-4:]
    avoid = ("\nRECENT FIRST LINES (do not reuse their wording or shape):\n- " + "\n- ".join(firsts) + "\n") if firsts else ""
    pic = ("TODAY THE POST HAS NO PICTURE (text only): it must stand on its words alone; never refer to an image, card, screenshot or 'above'. LinkedIn shows only the first 2-3 lines before 'see more', "
           "so the first line carries the hook and the second gives the reason to keep reading.\n") if text_only else ""
    offer = f"\nOFFER (the only thing you may offer, and only today): {fx['offer']}\n" if mode == "pitch" else ""
    return f"""ABOUT ANMOL (the only facts you may use about him; add nothing):
{json.dumps(about, ensure_ascii=False)}

TODAY'S POST: mode = {mode}. {BRIEF[mode]}
TOPIC FACTS (the heart of the post; use them and add nothing that is not here):
{json.dumps(story.topic_facts(fx, topic_id), ensure_ascii=False)}
{offer}
{HOOKS}
{pic}
SHAPE: {story.MIN_WORDS} to {story.MAX_WORDS} words. First line = the hook. Then 3 to 5 short paragraphs (1 to 3 sentences each), a blank line between them. First person ("I", "my"). Plain English, short sentences, concrete detail.
End with a calm line that invites people who build things to connect, or with the question. No hashtags, no links, no exclamation marks, no percentages, at most one emoji.
BANNED: DM, prices, 'pay after approval', discounts, urgency, 'game changer', hire-me language, client names, any number or count that is not in the facts above, claims about results.
{scriptlessons.prompt_block(scope="linkedin")}{avoid}{notes}
Return JSON: {{"post": "the full post text", "pitch_sentences": [{'"each offer sentence, copied exactly from the post"' if mode == 'pitch' else ''}]}}"""


def clean(text) -> str:
    return re.sub(r"\n{3,}", "\n\n", str(text or "").replace("\r", "")).strip()


def run(mode: str, topic_id: str, fx: dict | None = None, ask=None, recent_posts=(), tries: int = 3, text_only: bool = True) -> dict:
    """-> {"post": text or "", "mode", "topic", "attempts", "problems"}. `ask(prompt, system)` returns the model's JSON as a dict (tests pass a fake)."""
    fx = fx or story.facts()
    ask = ask or (lambda p, s: llm.ask_json(llm.gemini, p, s))
    notes, bad = "", []
    for attempt in range(1, tries + 1):
        data = ask(prompt(fx, mode, topic_id, notes, recent_posts, text_only), SYS) or {}
        text = clean(data.get("post"))
        bad = story.problems(text, mode, fx, data.get("pitch_sentences") or [])
        if not bad:
            return {"post": text, "mode": mode, "topic": topic_id, "attempts": attempt, "problems": []}
        if text:                                          # an empty or missing reply is an outage, not a writing mistake: it is retried but never becomes a lesson
            scriptlessons.record(bad)
        notes = "\nYOUR LAST DRAFT WAS REJECTED. Fix exactly these and change nothing else:\n- " + "\n- ".join(bad) + "\n"
    return {"post": "", "mode": mode, "topic": topic_id, "attempts": tries, "problems": bad}
