"""LinkedIn-only copy editor: turns the LinkedIn draft into clear, plain English. Never sees or touches Instagram or Bluesky."""
import json
from .. import captions, llm

SYS = "You are a careful copy editor for LinkedIn posts written by a freelance web developer in India for small-business owners."


def run(post, focus, brand):
    """-> {"post": text to use, "changed": bool, "issues": [...]}. Keeps the original if the model returns anything unusable."""
    kw = focus.get("dm_keyword", "HI")
    prompt = f"""Edit this LinkedIn post so a stranger understands it on the first read.

POST:
{post}

Do this:
- Fix every sentence that is ungrammatical, telegraphic, stuffed with buzzwords or hard to follow (bad example: "One script structure hooks value CTA in split screen example only."). Rewrite it as a clear sentence with the same meaning. If a line cannot be made both clear and true, delete it.
- Plain text only: no ** markers, no bold or fancy Unicode letters, no arrows or bullet symbols, no emoji, no hashtags, no lines or words in CAPITALS (the DM keyword and abbreviations such as SEO are fine).
- First line: a specific hook sentence in normal sentence case, 15 words or fewer. Then short lines (one or two sentences) with a blank line between them. 70-120 words in total.
- Last line: a soft DM invite using exactly the keyword '{kw}'.
- Do NOT add facts, numbers, clients, prices, demos or claims. Do not claim anything was built for a specific business. Brand rules: {json.dumps(brand.get('facts_rules', []), ensure_ascii=False)}
Return JSON: {{"ok": true/false, "issues": ["what was unclear"], "revised": "<the full edited post>"}}. If it is already clear, revised = the same text."""
    out = llm.ask_json(llm.factcheck_model, prompt, SYS)       # a different model from the writer, so it is a real second opinion
    rev = out.get("revised") if isinstance(out, dict) else None
    if not isinstance(rev, str) or not 40 <= captions.words(rev) <= 150:
        return {"post": post, "changed": False, "issues": (out or {}).get("issues", []) if isinstance(out, dict) else []}
    return {"post": rev.strip(), "changed": rev.strip() != (post or "").strip(), "issues": out.get("issues", [])}
