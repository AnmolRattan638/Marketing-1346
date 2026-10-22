"""Service-fit guard: a post must sell the service in focus. A topic or hook that is really about ANOTHER service (a chatbot pain with a
blog button, for example) is caught before it becomes an image. A second model reads the post the way a reader would and says which service
it expects; only a confident mismatch counts, and any failure of this check lets the post through (it never blocks the pipeline)."""
import json
from .. import llm

SYS = "You match social media posts to the service they would sell. Answer with JSON only."


def check(plan, focus, brand):
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    services = [{"id": s["id"], "name": s["name"], "what": s["pitch"][:130]} for s in brand["services"]]
    prompt = f"""A social media post says:
Topic: {plan['topic']} | Hook: {hook} | Angle: {plan.get('angle', '')}

A reader sees this post and then a button to enquire. Which ONE of these services would they expect it to be selling?
{json.dumps(services, ensure_ascii=False)}
Think about the PROBLEM the post talks about and which service solves exactly that problem.
Return JSON: {{"service_id": "<id>", "confidence": "high|low"}}"""
    out = llm.ask_json(llm.factcheck_model, prompt, SYS)
    out = out if isinstance(out, dict) else {}
    picked = out.get("service_id") if out.get("service_id") in {s["id"] for s in services} else None
    return {"fits": not (picked and picked != focus["id"] and out.get("confidence") == "high"), "picked": picked}
