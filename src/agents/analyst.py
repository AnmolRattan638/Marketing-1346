"""Agent 0: before every post, analyse the Instagram account's current state and brief the other agents."""
import json
from .. import llm

SYS = ("You are an Instagram growth analyst for a solo freelance web developer in India who markets AI chatbots, "
       "AI animated ads, lead generation and websites. Be honest about thin data. Never suggest buying followers, "
       "engagement pods, spam or fake claims.")


def run(ig, history, metrics, focus, today):
    prompt = f"""Today: {today}. Today's focus service: {focus['name']}.
Live Instagram data: {json.dumps(ig, ensure_ascii=False)[:5000] if ig else 'NOT AVAILABLE (no token). Use posting history only and say so.'}
Our posting history (last 30): {json.dumps(history[-30:], ensure_ascii=False)[:3500]}
Manual metrics: {json.dumps(metrics, ensure_ascii=False)[:1500]}

1) Classify the account stage (e.g. brand new under 100 followers, building trust, growing).
2) Say what the data suggests works or not (be honest if there is too little data).
3) Give each agent one short, concrete instruction for today's post. Posts must stay "developer showing real work", not ads.
4) Give up to 3 manual tips the owner should do himself today (e.g. comment on relevant posts), only safe organic actions.
Return JSON: {{"stage": "...", "followers": <number or null>, "summary": "<=60 words", "instructions": {{"research": "...", "analysis": "...", "writer": "...", "image": "...", "video": "..."}}, "manual_tips": ["..."]}}"""
    return llm.ask_json(llm.strategist_model, prompt, SYS)
