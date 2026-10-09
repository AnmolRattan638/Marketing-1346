"""Agent 7: reads performance + history, guides the other agents, and checks posts don't sound like ads."""
import json
from .. import config, llm

SYS = "You are the marketing strategist for a solo freelance web developer. Be concrete and brief."


def guide(history, metrics):
    recent = history[-14:]
    prompt = f"""Recent posts (topic, service, hook style, status):
{json.dumps(recent, ensure_ascii=False)[:4000]}

Performance data (may be empty early on):
{json.dumps(metrics, ensure_ascii=False)[:2000]}

Write guidance (max 180 words, markdown bullets) for tomorrow's research, hook and writing agents:
- what seems to work / not work (say 'not enough data yet' if so)
- which hook style to try next (rotate styles so we can compare)
- topics or phrasings to avoid because they were repeated
- one reminder: posts must teach first and never read like an ad."""
    return llm.strategist_model(prompt, SYS).strip()


def review(posts):
    prompt = f"""Score how much each draft sounds like an advertisement (1 = genuine helpful human, 10 = pure ad).
Drafts: {json.dumps(posts, ensure_ascii=False)}
Return JSON: {{"ad_score": <1-10 worst of the three>, "notes": "<specific rewrite instructions, empty if fine>"}}"""
    return llm.ask_json(llm.strategist_model, prompt, SYS)
