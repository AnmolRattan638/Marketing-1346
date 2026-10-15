"""Idea bank: hook patterns, reel rules and post ideas (config/ideas.json, adapted from vidIQ's public guidance) for the research,
analysis and reel-script agents. An idea counts as used once a draft carries its idea_id."""
from . import config


def bank():
    b = config.load_json(config.ROOT / "config" / "ideas.json", {})
    return {"hook_library": b.get("hook_library", []), "reel_rules": b.get("reel_rules", []), "ideas": b.get("ideas", [])}


def used_ids(history):
    return {h["idea_id"] for h in history if h.get("idea_id")}


def for_service(service_id, used, limit=4):
    """Unused ideas for today's service (or any service), in file order."""
    return [i for i in bank()["ideas"] if i.get("service") in (service_id, "any") and i.get("id") not in used][:limit]


def valid_id(idea_id):
    return idea_id if idea_id and any(i.get("id") == idea_id for i in bank()["ideas"]) else None


def ideas_text(pool):
    return "\n".join(f"- id={i['id']} | {i['format']} | {i['hook_style']} | hook: {i['hook']} | topic: {i['topic']} | angle: {i['angle']}" for i in pool)


def hooks_text():
    return "\n".join(f"- {h['style']}: {h['pattern']} ({h['note']})" for h in bank()["hook_library"])


def rules_text():
    return "\n".join(f"- {r}" for r in bank()["reel_rules"])
