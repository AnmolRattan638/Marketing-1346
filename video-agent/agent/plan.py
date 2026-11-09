"""Groq planner: loads a few skill files, asks for a scene plan, validates, retries once."""
from __future__ import annotations

import json
import os
import re

import requests

from .common import ROOT, SKILLS, log
from .schema import validate_plan

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_SKILLS = 3  # every skill costs prompt tokens; free-tier rate limits are tight


def read_skill(rel: str, max_chars: int) -> str:
    """Read skills/<rel>. A directory means its SKILL.md. Frontmatter is stripped."""
    path = SKILLS / rel
    if path.is_dir():
        path = path / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[... truncated to save tokens]"
    return text


def build_system_prompt(cfg: dict) -> str:
    p = cfg["planner"]
    names = (p["skills"] + p.get("extra_skills", []))[:MAX_SKILLS]
    parts = []
    for n in names:
        parts.append(f"## Reference: {n}\n\n{read_skill(n, p['max_skill_chars'])}")
    log(f"planner skills loaded: {names}")
    return "\n\n".join(parts)


def _call_groq(messages: list[dict], cfg: dict) -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    r = requests.post(
        GROQ_CHAT_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": os.environ.get("GROQ_MODEL", cfg["planner"]["model"]),
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
        },
        timeout=90,
    )
    if r.status_code == 429:
        raise RuntimeError("Groq rate limit hit (429). Wait and rerun, or reduce skills.")
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def make_plan(topic: str, cfg: dict, library: str = "") -> dict:
    lang = cfg["language"]
    user = (
        f"Topic: {topic}\n"
        f"Narration language: {lang}\n"
        f"Brand notes: {cfg['brand']['notes']}\n"
        f"Target length: about {cfg['video']['target_seconds']} seconds in total.\n"
        + (f"The owner has his own raw clips and photos about: {library}. Prefer a story he can actually show with them (his demos, his desk, his work), and use those words in footage_query where they fit.\n" if library else "")
        + "Return only the JSON object described in the rules."
    )
    messages = [
        {"role": "system", "content": build_system_prompt(cfg)},
        {"role": "user", "content": user},
    ]
    last_problems: list[str] = []
    for attempt in (1, 2):
        raw = _call_groq(messages, cfg)
        try:
            plan = json.loads(raw)
            last_problems = validate_plan(plan)
        except json.JSONDecodeError as e:
            plan, last_problems = None, [f"not valid JSON: {e}"]
        if not last_problems:
            return plan
        log(f"plan attempt {attempt} invalid: {last_problems[:3]}")
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Fix these problems and return the full JSON again:\n- "
             + "\n- ".join(last_problems[:6])},
        ]
    raise RuntimeError("planner failed twice: " + "; ".join(last_problems[:3]))


def sample_plan() -> dict:
    """Offline plan used by --offline runs and tests."""
    return json.loads((ROOT / "examples" / "sample_plan.json").read_text(encoding="utf-8"))
