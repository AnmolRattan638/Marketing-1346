"""Agent 3: write the final per-platform posts (Gemini)."""
import json
from .. import config, llm

SYS = "You write social posts in the author's own voice. Follow the voice guide strictly."


def run(plan, focus, brand, voice, guidance, rewrite_notes="", ig_mode="auto_image"):
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    prompt = f"""VOICE GUIDE:
{voice}

Brand rules: {json.dumps(brand['facts_rules'])}
Focus service: {json.dumps(focus, ensure_ascii=False)}
Topic: {plan['topic']} | Angle: {plan['angle']} | Key points: {plan['key_points']}
Opening hook (use as first line, you may polish): {hook}
Strategist guidance: {guidance}
{('REWRITE NOTES (fix these): ' + rewrite_notes) if rewrite_notes else ''}

Languages: {json.dumps(brand.get('languages', {}))}. Adapt the opening hook into the platform's language (Instagram = Hinglish).
HARD RULES: write for ANY small business (no single niche; at most 2-3 example business types in one line). NEVER claim you built, configured or prepared a demo, sample or prototype for anyone, never mention a demo link, never say 'test it yourself', never offer a personalised demo. Explain how the thing works in general; an illustrative conversation must be labelled as an example. The only offer is pay-after-approval and a conversation via DM. The DM keyword for today's service is '{focus.get('dm_keyword', 'HI')}' (the image shows it too); use exactly that keyword in the DM invite. Frame every post as a web developer SHOWING real thinking: one concrete thing built, fixed or noticed, with a specific detail. Call demo projects "sample" or "demo". It must NOT read like an advertisement.
Write one post per platform:
- instagram: {'caption for a REEL, 40-100 words' if ig_mode == 'manual_reel' else 'caption for an IMAGE post (a graphic with the hook), 80-140 words'}, first line is the hook, ends with ONE soft DM invite (vary the wording), 3-5 hashtags at the end
- linkedin: 120-200 words, short paragraphs, ends with a soft DM invite
- bluesky: ONE thought under 280 characters, soft nudge to DM
Audience is all of India: no city-specific assumptions; use broad hashtags like #SmallBusinessIndia, not city tags. Mention a price only for website/chatbot/animated ads and only copy it from price_note; never for lead gen.
Also write 3 reply drafts for likely comments/DMs (e.g. "how much?", "do you do this for my kind of business?").
Return JSON: {{"instagram": "...", "linkedin": "...", "bluesky": "...", "replies": [{{"if_they_say": "...", "reply": "..."}}]}}"""
    out = llm.ask_json(llm.gemini, prompt, SYS)
    out["bluesky"] = out["bluesky"][:300]
    return out
