"""Agent 1: research topics for today's post (Gemma)."""
import json
from .. import llm

SYS = "You research content ideas for a freelance web developer who markets to small businesses across all of India."


def run(brand, focus, history_topics, guidance, today):
    prompt = f"""Today: {today}
Brand: {brand['positioning']}
Today's focus service: {json.dumps(focus, ensure_ascii=False)}
Strategist guidance:
{guidance}

Topics already used recently (do NOT repeat or paraphrase): {json.dumps(history_topics[-30:], ensure_ascii=False)}

Propose 5 post topics tied to the focus service. Each must be useful to a small business owner anywhere in India, in any industry (or, for lead gen, a freelancer/agency), based on well-known facts or practical advice. No invented statistics, clients or testimonials.
Return JSON: {{"topics": [{{"topic": "...", "angle": "...", "why_it_matters": "..."}}]}}"""
    return llm.ask_json(llm.gemma, prompt, SYS)["topics"]
