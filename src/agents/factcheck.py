"""Agent 5: fact-check the drafts against the brand facts (GPT-OSS 120B)."""
import json
from .. import llm

SYS = "You are a strict fact-checker for small-business marketing copy."


def run(posts, focus, brand):
    prompt = f"""Brand facts and rules: {json.dumps(brand, ensure_ascii=False)}
Drafts: {json.dumps({k: posts[k] for k in ('instagram', 'linkedin', 'bluesky')}, ensure_ascii=False)}

Check for: invented clients/testimonials/results/statistics, prices not in price_note, guaranteed outcomes, false general claims, misleading wording.
If anything is wrong, fix it minimally in "revised" (keep voice and length; Bluesky stays under 300 chars). If all fine, revised = same text.
Return JSON: {{"ok": true/false, "issues": ["..."], "revised": {{"instagram": "...", "linkedin": "...", "bluesky": "..."}}}}"""
    return llm.ask_json(llm.groq, prompt, SYS)
