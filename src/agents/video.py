"""Agent 4b: 30-second reel plan as THREE 10-second Google Flow prompts (Flow makes one 10 s clip at a time)."""
from .. import llm

TIMES = ["0-10s", "10-20s", "20-30s"]


def run(plan, focus, posts, guidance=""):
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    prompt = f"""Write a 30-second vertical reel for: {plan['topic']} (service: {focus['name']}).
Hook: {hook}
Strategist note: {guidance}

Google Flow generates ONE 10-second clip per prompt, so write THREE standalone prompts (0-10s, 10-20s, 20-30s). Each prompt must work on its own, because Flow will not remember the previous clip.
- Part 1 (0-10s): the first spoken line is a specific problem or result in 12 words or fewer (no greeting, no brand intro) and the visual payoff appears within 3 seconds.
- Part 2 (10-20s): show how it works or the proof, one idea.
- Part 3 (20-30s): the result plus ONE next step (a DM keyword), spoken naturally.
- Each part's spoken line: 25 words or fewer so it fits in 10 seconds, simple English or light Hinglish.
- "continuity": ONE short block (max 60 words) describing the same fictional presenter (not a real person), outfit, setting, lighting, colour palette and camera style, so the three clips look like one video.
- Each "flow_prompt": 60-110 words: camera, action, what is on screen, and the exact spoken line in quotes. No text overlays inside the video (captions are added later).
Return JSON: {{"hook_first_3s": "spoken line + on-screen text", "continuity": "...", "parts": [{{"time": "0-10s", "voiceover": "...", "flow_prompt": "..."}}, {{"time": "10-20s", "voiceover": "...", "flow_prompt": "..."}}, {{"time": "20-30s", "voiceover": "...", "flow_prompt": "..."}}]}}"""
    out = llm.ask_json(llm.gemma, prompt, "You write short, honest, non-salesy reel scripts for Google Flow.")
    cont = (out.get("continuity") or "").strip()
    parts = out.get("parts") or [{"time": "0-10s", "voiceover": out.get("voiceover", ""), "flow_prompt": out.get("flow_prompt", "")}]
    for i, p in enumerate(parts):
        p["time"] = p.get("time") or TIMES[min(i, 2)]
        fp = (p.get("flow_prompt") or "").strip()
        if cont and cont not in fp:                  # every clip carries the same character/style block
            fp = f"{cont}\n\n{fp}"
        p["flow_prompt"] = fp
    out["parts"] = parts
    out["voiceover"] = " ".join(p.get("voiceover", "") for p in parts).strip()
    return out
