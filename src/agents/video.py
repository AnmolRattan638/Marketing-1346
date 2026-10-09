"""Agent 4b: reel script + Google Flow prompt. Flow has no public API, so you generate the clip manually."""
import json
from .. import llm


def run(plan, focus, posts):
    prompt = f"""Write a 20-30 second vertical reel plan for: {plan['topic']} (service: {focus['name']}).
Hook: {plan['hooks'][plan.get('chosen_hook', 0)]['text']}
Return JSON: {{"voiceover": "spoken script, simple English/light Hinglish", "shots": ["3-5 short shot descriptions"], "flow_prompt": "one paragraph prompt to paste into Google Flow"}}"""
    return llm.ask_json(llm.gemma, prompt, "You write short, honest, non-salesy reel scripts.")
