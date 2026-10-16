"""Agent 2: pick the best topic and write high-retention hooks (GPT-OSS 120B)."""
import json
from .. import ideas, learning, llm

SYS = "You are a sharp content strategist who writes scroll-stopping but honest hooks."


def run(topics, focus, guidance, history):
    last_styles = [h.get("hook_style") for h in history[-5:]]
    prompt = f"""Candidate topics: {json.dumps(topics, ensure_ascii=False)}
Focus service: {focus['name']}
Guidance: {guidance}
Hook styles used in the last posts: {last_styles}
Hook library (patterns that stop the scroll, adapted from vidIQ; use them as starting points, not templates, and keep every hook honest):
{ideas.hooks_text()}

Pick the single best topic. It and its hooks must be universal: any small business that talks to customers should relate, never one niche. No hook may imply a demo, sample or prototype exists. Write 3 hooks, each in a DIFFERENT style, each 12 words or fewer, specific, readable in 3 seconds, and worth forwarding to a friend (e.g. question, mistake-callout, specific-observation, myth-bust), first line only, no clickbait lies.
If the topic you pick came with an idea_id, return it. If the guidance contains an EXPERIMENT block, the topic you pick MUST address its problem: return that problem's id as problem_id and use the angle type and hook style it names (make chosen_hook point at a hook of that style). Otherwise problem_id is null and angle_type is the best fit from: {', '.join(learning.ANGLE_TYPES)}. Think of three different angles for the topic and keep the strongest. A hook states ONE specific promise and who it is for in its first words (people decide in about a second).
Return JSON: {{"idea_id": "from the picked topic, or null", "problem_id": "id from the EXPERIMENT block, or null", "angle_type": "one allowed angle type", "topic": "...", "angle": "...", "key_points": ["3-4 short points"], "hooks": [{{"style": "...", "text": "..."}}], "chosen_hook": 0, "image_idea": "ONE real object in ONE real place, as a single scene (never a layout: no split screen, panels, sections, grids, collages or counts of parts)"}}
chosen_hook is the index of the best hook; prefer a style not used recently."""
    return llm.ask_json(llm.groq, prompt, SYS)
