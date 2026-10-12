"""Agent 7: reads performance + history, guides the other agents, and checks posts don't sound like ads."""
import json
from .. import llm

SYS = ("You are the marketing strategist for a solo freelance web developer in India who markets AI chatbots, AI animated ads, "
       "lead generation and websites. Be concrete, brief and honest about thin data.")


def guide(history, metrics, focus, today, brand=None):
    """Before each post: judge the Instagram account's current state from our history and manual stats, and brief every agent.
    Returns {"stage", "followers", "summary", "guidance", "instructions": {agent: text}, "manual_tips": [...]}."""
    rules = json.dumps((brand or {}).get("facts_rules", []), ensure_ascii=False)
    prompt = f"""Today: {today}. Today's focus service: {focus['name']}.
BRAND RULES (binding: nothing you write, including the agent instructions and the manual tips, may break any of them. If a rule forbids something, do not suggest it, not even as an example): {rules}
Audience and positioning: {(brand or {}).get('positioning', '')}
Live Instagram data is NOT available. Judge the account's state from the posting history and the manual stats below, and say how thin the data is.
Recent posts (topic, service, hook style, status): {json.dumps(history[-14:], ensure_ascii=False)[:3500]}
Manual account/performance stats entered by the owner (followers, likes, posts, comments; may be empty): {json.dumps(metrics, ensure_ascii=False)[:4000]}

1) Classify the account stage (e.g. brand new under 100 followers, building trust, growing).
2) Say what the data suggests works or not (be honest if there is too little data).
3) Write general guidance (max 150 words, markdown bullets). Use skip rate, average watch time, shares, comments and view sources if present: a high skip rate means the first 3 seconds fail. Cover: hook style to try next (rotate styles), topics/phrasings to avoid because repeated, and a reminder that posts show a developer's real work and never read like an ad.
4) Give each agent one short, concrete instruction for today's post.
5) Give up to 3 manual tips the owner should do himself today (only safe organic actions, e.g. commenting on relevant posts).
Never suggest buying followers, engagement pods, spam or fake claims. Never suggest demos, free audits, free samples or screen recordings of work that is not listed in the brand rules, never invent timeframes or results, and never target one niche or region.
If the Instagram bio in the manual stats conflicts with the brand rules (a niche or region, a timeframe, a free offer outside website posts), say so in "summary" and add a manual tip to fix the bio.
Return JSON: {{"stage": "...", "followers": <number or null>, "summary": "<=60 words", "guidance": "...", "instructions": {{"research": "...", "analysis": "...", "writer": "...", "image": "...", "video": "..."}}, "manual_tips": ["..."]}}"""
    return llm.ask_json(llm.strategist_model, prompt, SYS)


def review(posts):
    prompt = f"""Score how much each draft sounds like an advertisement (1 = a developer genuinely showing real work, 10 = pure ad). Score 7+ if it does not show a specific, concrete piece of work or reads like a sales pitch.
Drafts: {json.dumps(posts, ensure_ascii=False)}
Return JSON: {{"ad_score": <1-10 worst of the three>, "notes": "<specific rewrite instructions, empty if fine>"}}"""
    return llm.ask_json(llm.strategist_model, prompt, SYS)
