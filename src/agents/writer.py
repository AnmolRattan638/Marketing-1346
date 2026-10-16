"""Agent 3: write the final per-platform posts (Gemini). Output keeps **bold** markers; captions.finalize_posts turns them into real bold last."""
import json
from .. import captions, llm

SYS = "You write social posts in the author's own voice. Follow the voice guide strictly."


def run(plan, focus, brand, voice, guidance, rewrite_notes="", ig_mode="auto_image", linkedin_format="image"):
    li_block = ""
    if linkedin_format == "text":
        li_block = ("- TODAY THE LINKEDIN POST HAS NO PICTURE (text only). It must stand on its words alone: never refer to an image, card, screenshot or 'above'. "
                    "LinkedIn shows only the first 2-3 lines before 'see more', so the first line carries the whole hook and the second gives the reason to keep reading. "
                    "Prefer one concrete observation or common mistake, then what the owner can do about it.\n")
    lead_gen_block = ""
    if focus.get("id") == "lead_gen":     # only the lead-gen service has this audience; other services are untouched
        lead_gen_block = (
            "LEAD GEN AUDIENCE (this post only; it overrides any narrower habit): the reader is ANY freelancer, agency or solo service seller "
            "who needs clients from local businesses: marketing, design, video editing, SEO, ads, web, software, photography, accounting, consulting, "
            "coaching, anything. Never address one profession (do not call the reader a web developer, developer, coder or website designer) and do not "
            "use 'businesses with no website' as the main example. Start with 'Freelancers', 'Agencies' or 'Anyone selling a service' (in Hinglish on Instagram), "
            "and say 'whatever you sell' somewhere. Describe the sheet only as local businesses found through Google Places, with contact details, review counts "
            "and website checks, including newly opened ones. Instagram hashtags: only broad ones such as #FreelanceIndia #Freelancers #LeadGeneration "
            "#GetClients #SmallBusinessIndia; never #WebDeveloper, #WebDesign or #AgencyLife.\n")
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    prompt = f"""VOICE GUIDE:
{voice}

Brand rules: {json.dumps(brand['facts_rules'])}
Focus service: {json.dumps(focus, ensure_ascii=False)}
Topic: {plan['topic']} | Angle: {plan['angle']} | Key points: {plan['key_points']}
Opening hook (use as first line, you may polish, written in CAPITALS): {hook}
Strategist guidance: {guidance}
{('REWRITE NOTES (fix these): ' + rewrite_notes) if rewrite_notes else ''}

Languages: {json.dumps(brand.get('languages', {}))}. Adapt the opening hook into the platform's language (Instagram = Hinglish).
HARD RULES: write for ANY small business (no single niche; at most 2-3 example business types in one line). NEVER claim you built, configured or prepared a demo, sample or prototype for anyone, never mention a demo link, never say 'test it yourself', never offer a personalised demo. Explain how the thing works in general; an illustrative conversation must be labelled as an example. The only offer is pay-after-approval and a conversation via DM. The DM keyword for today's service is '{focus.get('dm_keyword', 'HI')}' (the image shows it too); use exactly that keyword in the DM invite. Frame every post as a web developer SHOWING real thinking: one concrete thing built, fixed or noticed, with a specific detail. Call demo projects "sample" or "demo". It must NOT read like an advertisement.
CAPTION FORMAT for instagram and bluesky (mandatory; it overrides any longer or paragraph style in the voice guide; LinkedIn does NOT use it, see LINKEDIN FORMAT below):
- Short and scannable. NO paragraphs. One short line per idea, a blank line between blocks.
- Line 1 = the HOOK IN CAPITAL LETTERS, wrapped in **double asterisks**, 12 words max.
- Then 2-3 short lines, 12 words max each, each starting with "→". Specific and concrete, plain words, no filler.
- Wrap 2-4 KEY WORDS in **double asterisks** and write them in CAPITALS (6 bold spans in total at most; never bold hashtags). Do not write other whole sentences in capitals.
- One soft DM line with the keyword bold, for example: DM **{focus.get('dm_keyword', 'HI')}** and tell me what you sell. Vary the wording.
LINKEDIN FORMAT (linkedin only; plain text, written like a person talking to a business owner):
- Plain text only: no ** markers, no bold or fancy letters, no arrows or bullet symbols, no emoji, no hashtags, no lines or words in CAPITALS (the DM keyword and abbreviations such as SEO are the only exceptions).
- 70-120 words, in complete grammatical sentences that a stranger understands on the first read. No telegraphic fragments, no stacked buzzwords.
- First line: one specific hook sentence in normal sentence case, 15 words or fewer (something you noticed, fixed or built, or a problem every owner recognises).
- Then 3-5 short lines, one or two sentences each with a blank line between them. Each adds one concrete detail, reason or example; one of them says what the owner can do about it.
- Last line: a soft DM invite using exactly the keyword '{focus.get('dm_keyword', 'HI')}', for example: DM {focus.get('dm_keyword', 'HI')} and tell me what you sell. Vary the wording.
- All the HARD RULES above still apply (no demo claims, no invented numbers, no single niche, not an advertisement).
{li_block}{lead_gen_block}Write one post per platform:
- instagram: {'REEL caption, 25-45 words in total' if ig_mode == 'manual_reel' else 'IMAGE caption, 35-60 words in total'} (hashtags not counted), in the format above, then a blank line and 3-5 hashtags
- linkedin: follow the LINKEDIN FORMAT below
- bluesky: ONE punchy thought under 260 characters, may start with a **CAPITAL WORD OR TWO**, soft nudge to DM
Audience is all of India: no city-specific assumptions; use broad hashtags like #SmallBusinessIndia, not city tags. Mention a price only for website/chatbot/animated ads and only copy it from price_note; never for lead gen.
Also write 3 reply drafts for likely comments/DMs (e.g. "how much?", "do you do this for my kind of business?").
Return JSON: {{"instagram": "...", "linkedin": "...", "bluesky": "...", "replies": [{{"if_they_say": "...", "reply": "..."}}]}}"""
    out = llm.ask_json(llm.gemini, prompt, SYS)
    notes = captions.over_limit(out, ig_mode)
    if notes:                                                          # one automatic shorten pass; never loops
        again = llm.ask_json(llm.gemini, prompt + f"\nTOO LONG, FIX THIS: {notes}. Keep the format.", SYS)
        if not captions.over_limit(again, ig_mode) or captions.words(again.get("instagram", "")) < captions.words(out.get("instagram", "")):
            out = again
    out["bluesky"] = out["bluesky"][:300]
    return out
