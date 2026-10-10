"""Agent 2: pick the best topic and write high-retention hooks (GPT-OSS 120B)."""
import json
from .. import llm

SYS = "You are a sharp content strategist who writes scroll-stopping but honest hooks."


def run(topics, focus, guidance, history):
    last_styles = [h.get("hook_style") for h in history[-5:]]
    prompt = f"""Candidate topics: {json.dumps(topics, ensure_ascii=False)}
Focus service: {focus['name']}
Guidance: {guidance}
Hook styles used in the last posts: {last_styles}

Pick the single best topic. Write 3 hooks, each in a DIFFERENT style, each 12 words or fewer, specific, readable in 3 seconds, and worth forwarding to a friend (e.g. question, mistake-callout, specific-observation, myth-bust), first line only, no clickbait lies.
Return JSON: {{"topic": "...", "angle": "...", "key_points": ["3-4 short points"], "hooks": [{{"style": "...", "text": "..."}}], "chosen_hook": 0, "image_idea": "one-sentence visual idea"}}
chosen_hook is the index of the best hook; prefer a style not used recently."""
    return llm.ask_json(llm.groq, prompt, SYS)
