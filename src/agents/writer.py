"""Agent 3: write the final per-platform posts (Gemini). Output keeps **bold** markers; captions.finalize_posts turns them into real bold last."""
import json
from .. import captions, config, llm

SYS = "You write social posts in the author's own voice. Follow the voice guide strictly."


def service_facts(focus, brand):
    """What the LinkedIn post may state about the service. Built from config/service_details.json and the brand file, so the long post explains real things and invents no features."""
    det = config.load_json(config.ROOT / "config/service_details.json", {}).get(focus.get("id")) or {}
    tiers = [f"{t['name']}: " + "; ".join(t.get("includes", [])) for t in det.get("tiers", []) if t.get("name")]
    steps = ("HOW WORK HAPPENS (true for every service; use these facts for 'how it works'): the owner tells me what the business sells and what customers keep asking; I build it; the owner reviews it and asks for changes; "
             + (brand.get("offers", {}).get("pay_after_approval") or "the client pays only after approving the work"))
    what = f"WHAT IT IS: {focus.get('pitch', '')}"
    inc = ("INCLUDED (the only features you may name): " + " | ".join(tiers)) if tiers else "INCLUDED: nothing beyond the description above is known, so do not name features, counts or timelines; explain the idea and the process in general, honest terms."
    return f"SERVICE FACTS (everything the long LinkedIn post may say about the service)\n{what}\n{inc}\n{steps}"


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
    facts_block = service_facts(focus, brand) + "\n"
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
LINKEDIN FORMAT (linkedin only; a LONG, plain-text explainer written like a developer talking to a business owner; it teaches, it does not sell):
- 300-380 words, never fewer than 300. Plain text only: no ** markers, no bold or fancy letters, no arrows, bullets or numbered lists, no emoji, no hashtags, no lines or words in CAPITALS (the DM keyword and abbreviations such as SEO are the only exceptions). Complete, clear sentences a stranger understands on the first read.
- Seven short paragraphs, a blank line between each, in this order:
  1. HOOK (one sentence, 18 words or fewer, sentence case): a specific, true observation about how small businesses handle this problem today.
  2. THE SITUATION: what this looks like in an ordinary working day of an owner (two or three concrete details; a café, a gym or a clinic may appear, no single niche).
  3. WHAT I BUILD: explain the service in plain words as if to a friend who has never heard of it: what it is and what it is not. Use WHAT IT IS and INCLUDED from the SERVICE FACTS.
  4. HOW IT WORKS: the process in plain prose (first, then, after that), from the owner's first message to the finished work, using only HOW WORK HAPPENS and INCLUDED.
  5. HOW IT HELPS: what changes in the owner's week, in practical terms (fewer repeated replies, answers available at night, less time spent searching). Describe the effect, never promise results, rankings, revenue or numbers.
  6. AN HONEST LIMIT: who it suits and what it does not do or fix by itself (for example: it will not replace a personal reply on complicated questions).
  7. CLOSE: one calm sentence that you are happy to talk it through; mention in one plain sentence that payment happens only after the owner approves the work; end with a soft DM invite using exactly the keyword '{focus.get('dm_keyword', 'HI')}' (for example: DM {focus.get('dm_keyword', 'HI')} and tell me what you sell). Vary the wording.
- Teach first, sell last: at least two thirds of the post is explanation that is useful even if the reader never writes to me. Never sound like an ad: no exclamation marks, no 'game-changer', 'unlock', 'transform', 'boost', no urgency or scarcity, no slogans, no repeated calls to action. Never mention a price on LinkedIn.
- Every sentence must carry information: if you cannot add concrete detail from the SERVICE FACTS or from ordinary working life, write fewer details, but still reach 300 words by explaining the reasoning behind the design (why it is built this way).
- All the HARD RULES above still apply (no demo claims, no invented numbers, no single niche, not an advertisement).
{li_block}{lead_gen_block}{facts_block}Write one post per platform:
- instagram: {'REEL caption, 25-45 words in total' if ig_mode == 'manual_reel' else 'IMAGE caption, 35-60 words in total'} (hashtags not counted), in the format above, then a blank line and 3-5 hashtags
- linkedin: follow the LINKEDIN FORMAT below
- bluesky: ONE plain thought under 260 characters (Bluesky allows 300 per post, so it cannot carry the long explanation): a specific observation from the developer's desk in natural sentence case, no bold markers, no slogans, no hashtag stack (at most one), no 'pay after approval' line; an optional soft nudge to DM the keyword. It must read like a person, not an ad.
Audience is all of India: no city-specific assumptions; use broad hashtags like #SmallBusinessIndia, not city tags. Mention a price only for website/chatbot/animated ads and only copy it from price_note; never for lead gen.
Also write 3 reply drafts for likely comments/DMs (e.g. "how much?", "do you do this for my kind of business?").
Return JSON: {{"instagram": "...", "linkedin": "...", "bluesky": "...", "replies": [{{"if_they_say": "...", "reply": "..."}}]}}"""
    out = llm.ask_json(llm.gemini, prompt, SYS)
    notes = captions.over_limit(out, ig_mode)
    for _ in range(2):                                                 # at most two automatic fix passes (too long, or LinkedIn under 300 words); never loops further
        if not notes:
            break
        again = llm.ask_json(llm.gemini, prompt + f"\nFIX THIS (keep every format rule): {notes}.", SYS)
        again_notes = captions.over_limit(again, ig_mode)
        if len(again_notes.split("; ")) <= len(notes.split("; ")) and isinstance(again.get("linkedin"), str) and isinstance(again.get("instagram"), str):
            out, notes = again, again_notes
        else:
            break
    out["bluesky"] = out["bluesky"][:300]
    return out
