"""Agent 1: research topics for today's post (Gemma)."""
import json
from .. import llm

SYS = "You research content ideas for a freelance web developer who markets to small businesses across all of India."


def run(brand, focus, history_topics, guidance, today, ideas=""):
    prompt = f"""Today: {today}
Brand: {brand['positioning']}
Today's focus service: {json.dumps(focus, ensure_ascii=False)}
Strategist guidance:
{guidance}

Topics already used recently (do NOT repeat or paraphrase): {json.dumps(history_topics[-30:], ensure_ascii=False)}

{('IDEA BANK (hook formats adapted from vidIQ public guidance on what stops the scroll). When it is not empty, at least 2 of your 5 topics should adapt an idea from it, keeping every rule in this prompt (universal for any small business, no demos or samples, no invented statistics, clients or testimonials); give the idea back as idea_id. Skip an idea that conflicts with a rule:' + chr(10) + ideas + chr(10)) if ideas else ''}Propose 5 post topics tied to the focus service. Each must be useful to ANY small business owner in India, whatever the industry (or, for lead gen, a freelancer/agency). Use universal situations, not one niche, and never propose topics that rely on having built a demo or sample for a specific business type, based on well-known facts or practical advice. No invented statistics, clients or testimonials.
Return JSON: {{"topics": [{{"topic": "...", "angle": "...", "why_it_matters": "...", "idea_id": "id from the idea bank, or omit"}}]}}"""
    return llm.ask_json(llm.gemma, prompt, SYS)["topics"]
