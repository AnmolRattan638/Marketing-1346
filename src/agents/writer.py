"""Agent 3: write the final per-platform posts (Gemini)."""
import json
from .. import config, llm

SYS = "You write social posts in the author's own voice. Follow the voice guide strictly."


def run(plan, focus, brand, voice, guidance, rewrite_notes=""):
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    prompt = f"""VOICE GUIDE:
{voice}

Brand rules: {json.dumps(brand['facts_rules'])}
Focus service: {json.dumps(focus, ensure_ascii=False)}
Topic: {plan['topic']} | Angle: {plan['angle']} | Key points: {plan['key_points']}
Opening hook (use as first line, you may polish): {hook}
Strategist guidance: {guidance}
{('REWRITE NOTES (fix these): ' + rewrite_notes) if rewrite_notes else ''}

Write one post per platform:
- instagram: caption, 80-160 words, ends with a soft DM invite (vary the wording), 3-5 hashtags at the end
- linkedin: 120-200 words, short paragraphs, ends with a soft DM invite
- bluesky: ONE thought under 280 characters, soft nudge to DM
Mention a price only for website/chatbot/animated ads and only copy it from price_note; never for lead gen.
Also write 3 reply drafts for likely comments/DMs (e.g. "how much?", "do you do this for my kind of business?").
Return JSON: {{"instagram": "...", "linkedin": "...", "bluesky": "...", "replies": [{{"if_they_say": "...", "reply": "..."}}]}}"""
    out = llm.ask_json(llm.gemini, prompt, SYS)
    out["bluesky"] = out["bluesky"][:300]
    return out
