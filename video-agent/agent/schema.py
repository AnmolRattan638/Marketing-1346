"""JSON schema for the plan Groq returns. The planner never writes code, only this."""
from __future__ import annotations

from jsonschema import Draft202012Validator

SFX_TYPES = ["whoosh", "pop", "riser", "click"]

PLAN_SCHEMA = {
    "type": "object",
    "required": ["title", "scenes"],
    "properties": {
        "title": {"type": "string", "minLength": 3, "maxLength": 120},
        "scenes": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {
                "type": "object",
                "required": ["narration", "footage_query"],
                "properties": {
                    "narration": {"type": "string", "minLength": 5, "maxLength": 240},
                    "footage_query": {"type": "string", "minLength": 3, "maxLength": 80},
                    # Optional cutaway (B-roll) searches, in the order the narration mentions them. Each cutaway shot in the scene
                    # uses the next one, so the picture matches what is being said at that moment.
                    "broll": {"type": "array", "maxItems": 4, "items": {"type": "string", "minLength": 3, "maxLength": 60}},
                    # Name of a clip you placed in assets/hero/ by hand (e.g. made on a
                    # free Kaggle GPU session). Null or missing means use Pexels.
                    "hero_clip": {"type": ["string", "null"]},
                    "sfx": {
                        "type": "array",
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "required": ["type"],
                            "properties": {
                                "type": {"enum": SFX_TYPES},
                                "at": {"enum": ["cut", "word"]},
                                "at_word": {"type": "string"},
                            },
                        },
                    },
                    # Reserved for later phases (Lottie overlays, transition styles).
                    # Accepted so plans stay forward compatible, ignored by v1.
                    "transition": {"type": "string"},
                    "lottie": {"type": ["string", "null"]},
                },
            },
        },
        "cta": {
            "type": "object",
            "properties": {"text": {"type": "string", "maxLength": 60}},
        },
    },
}

_validator = Draft202012Validator(PLAN_SCHEMA)


def validate_plan(plan) -> list[str]:
    """Return a list of human-readable problems, empty when the plan is valid."""
    problems = []
    for e in sorted(_validator.iter_errors(plan), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in e.path) or "(root)"
        problems.append(f"{where}: {e.message[:200]}")
    return problems
