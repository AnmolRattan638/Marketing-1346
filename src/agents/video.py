"""Agent 4b: reel script + Google Flow prompt. Flow has no public API, so you generate the clip manually."""
import json
from .. import llm


def run(plan, focus, posts, guidance=""):
    prompt = f"""Write a 15-30 second vertical reel plan (about 40-80 spoken words) for: {plan['topic']} (service: {focus['name']}).
Hook: {plan['hooks'][plan.get('chosen_hook', 0)]['text']}
Strategist note: {guidance}
Retention rules (our reels lost 64-75% of viewers in the first seconds): the first spoken line is a specific problem or result in 12 words or fewer; no greeting, no brand intro; the visual payoff appears in the first 3 seconds; payoff by second 10; one next step at the end.
Return JSON: {{"hook_first_3s": "spoken line + on-screen text", "voiceover": "spoken script, simple English/light Hinglish", "shots": ["3-5 short shot descriptions with timings"], "flow_prompt": "one paragraph prompt to paste into Google Flow"}}"""
    return llm.ask_json(llm.gemma, prompt, "You write short, honest, non-salesy reel scripts.")
