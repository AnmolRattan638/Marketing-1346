"""Planner mistakes -> concrete feedback, remembered for the next run.

When the planner's JSON is rejected, the raw validator text ("scenes/3/graphic/heading: '...' is too long") is turned into a concrete mistake in plain words (which scene, which field, what it
wrote, what the limit is, how to fix it). That text goes back to the planner for the retry, is logged, is raised in the final error, and each mistake is counted in
state/planner_lessons.json. The most frequent ones are written into the next planner prompt as "mistakes you made before", so they are avoided from the first try.
state/ is kept between runs by the workflow's cache step."""
from __future__ import annotations

import json
import re

from .common import ROOT, log
from .schema import PLAN_SCHEMA

STATE = ROOT / "state" / "planner_lessons.json"
# Rules the planner has broken in real runs; always in the prompt, so a fresh cache still starts with them.
SEED = {
    "fx type:type": "`fx` types are only stat, glitch, title, lower_third, shake, quote. Sound effects (whoosh, pop, riser, click) go in `sfx`, never in `fx`.",
    "heading:too-long": "graphic `heading` and `heading2` are at most 30 characters; `step` at most 14; chips at most 24. Count the characters.",
    "beat:order": "Scenes follow the master script's beats in order; do not add a beat it does not have.",
}


def _node(path: list[str]):
    """The schema node for a validator path like scenes/3/graphic/heading (list indexes are skipped)."""
    node = PLAN_SCHEMA
    for part in path:
        if part.isdigit():
            node = node.get("items", node) if isinstance(node, dict) else node
            continue
        node = (node.get("properties", {}) if isinstance(node, dict) else {}).get(part) or (node.get("items", {}).get("properties", {}).get(part) if isinstance(node, dict) else None) or {}
        if node.get("type") == "array" and "items" in node and part not in ("scenes",):
            pass
    return node if isinstance(node, dict) else {}


def explain(problem: str) -> tuple[str, str, str]:
    """-> (key, concrete mistake for this run, general rule for future runs)."""
    if "beats must follow" in problem:
        return ("beat:order", problem, "follow the master script's beats exactly, in order")
    m = re.match(r"^([\w/\-]+): (.*)$", problem, re.S)
    if not m:
        return ("other:" + problem[:30], problem, "")
    path, msg = m.group(1).split("/"), m.group(2)
    nums = [p for p in path if p.isdigit()]
    where = f"scene {int(nums[0]) + 1}" if path and path[0] == "scenes" and nums else "the plan"
    names = [p for p in path if not p.isdigit()]
    field = names[-1] if names else "value"
    if field == "type" and len(names) > 1:
        field = f"{names[-2]} type"                 # e.g. `fx type`, not just `type`
    val = re.match(r"^'(.*?)'? is", msg, re.S)
    val = val.group(1) if val else ""
    node = _node(path)
    if msg.endswith("is too long"):
        lim = node.get("maxLength")
        return (f"{field}:too-long", f"{where}: `{field}` was {len(val)} characters (\"{val}\"), the limit is {lim}. Rewrite it to {lim} characters or fewer.",
                f"`{field}` is at most {lim} characters")
    if "is not one of" in msg:
        allowed = re.search(r"\[(.*)\]", msg)
        allowed = allowed.group(1).replace("'", "") if allowed else ""
        return (f"{field}:type", f"{where}: `{field}` was \"{val}\", which does not exist. Allowed values: {allowed}. Use one of those or leave it out.",
                f"`{field}` must be one of: {allowed}")
    if "is a required property" in msg:
        return (f"{field}:missing", f"{where}: required field {msg.split(' is a required')[0]} was missing.", f"always include {msg.split(' is a required')[0]}")
    if msg.startswith("[] is too short") or msg.startswith("[]"):
        return (f"{field}:empty", f"{where}: `{field}` was empty. It needs at least one entry.", f"`{field}` must not be empty")
    if "too short" in msg:
        return (f"{field}:too-short", f"{where}: `{field}` was too short (\"{val}\"). Give it real content or leave it out.", f"`{field}` must not be blank or tiny")
    if "beats must follow" in msg:
        return ("beat:order", f"{where}: {msg}", "follow the master script's beats exactly, in order")
    return (f"{field}:other", f"{where}: `{field}` {msg}", "")


def load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def record(problems: list[str]) -> list[str]:
    """Count these mistakes for future runs; returns their concrete descriptions."""
    texts, data = [], load()
    for p in problems:
        key, concrete, rule = explain(p)
        texts.append(concrete)
        row = data.setdefault(key, {"count": 0})
        row["count"] += 1
        if rule:
            row["rule"] = rule
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        log(f"lessons not saved ({e})")
    return texts


def prompt_block(limit: int = 8) -> str:
    rules = list(SEED.values())
    for _, row in sorted(load().items(), key=lambda kv: -kv[1].get("count", 0)):
        if row.get("rule") and row["rule"] not in rules and len(rules) < limit + len(SEED):
            rules.append(f"{row['rule']} (broken {row['count']}x before)")
    return "MISTAKES YOU HAVE MADE BEFORE (a rejected plan costs the whole video; check each before answering):\n- " + "\n- ".join(rules) + "\n"
