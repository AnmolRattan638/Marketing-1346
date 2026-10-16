"""Agent: research the audience's real problems for a service (a compact version of the 'audience research' step).
The answers are hypotheses written by a model, not evidence: only posts that get tested against them (src/learning.py) prove anything."""
import json
from .. import llm

SYS = "You study the everyday problems of small-business owners and freelancers in India. You never invent statistics, clients or claims."


def audience(focus):
    if focus.get("id") == "lead_gen":
        return "ANY freelancer, agency or solo service seller who needs clients from local businesses, whatever they sell (never one profession)"
    return "ANY small business owner in India who talks to customers (never one niche, city or industry)"


def run(brand, focus, existing, guidance="", n=6):
    prompt = f"""Service in focus: {json.dumps(focus, ensure_ascii=False)}
Audience: {audience(focus)}
Brand: {brand['positioning']}
Problems already in the bank (do NOT repeat or paraphrase): {json.dumps(existing[-40:], ensure_ascii=False)}
Strategist guidance: {guidance[:600]}

List {n} DIFFERENT, specific problems this audience has that today's service helps with. For each give short fields (max 20 words each):
problem, frustration, desired_outcome, audience_phrase (something they would really say, English or Hinglish), common_mistake, objection (why they hesitate), emotional_reason.
Rules: universal across industries; no statistics, no named clients, no demos or samples, no promises of results; plain words.
Return JSON: {{"problems": [{{"problem": "...", "frustration": "...", "desired_outcome": "...", "audience_phrase": "...", "common_mistake": "...", "objection": "...", "emotional_reason": "..."}}]}}"""
    out = llm.ask_json(llm.gemma, prompt, SYS)
    items = out.get("problems") if isinstance(out, dict) else None
    return [i for i in (items or []) if isinstance(i, dict) and isinstance(i.get("problem"), str)]
