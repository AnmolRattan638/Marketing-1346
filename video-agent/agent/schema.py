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
                "required": ["narration"],          # footage_query is only needed when the scene has no `graphic`
                "properties": {
                    "narration": {"type": "string", "minLength": 5, "maxLength": 240},
                    "footage_query": {"type": "string", "minLength": 3, "maxLength": 80},
                    # Optional cutaway (B-roll) searches, in the order the narration mentions them. Each cutaway shot in the scene
                    # uses the next one, so the picture matches what is being said at that moment.
                    "broll": {"type": "array", "maxItems": 4, "items": {"type": "string", "minLength": 3, "maxLength": 60}},
                    # Optional animated graphics anchored to spoken words (agent/fx_plan.py) and how this scene arrives.
                    "fx": {"type": "array", "maxItems": 2, "items": {
                        "type": "object",
                        "required": ["type"],
                        "properties": {
                            "type": {"enum": ["stat", "glitch", "title", "lower_third", "shake"]},
                            "at_word": {"type": "string", "maxLength": 40},
                            "seconds": {"type": "number", "minimum": 0.5, "maximum": 4},
                            "text": {"type": "string", "maxLength": 40},
                            "label": {"type": "string", "maxLength": 50},
                            "value": {"type": "number"},
                            "prefix": {"type": "string", "maxLength": 4},
                            "suffix": {"type": "string", "maxLength": 6},
                        },
                    }},
                    "transition": {"enum": ["settle", "whip", "zoom", "iris", "glitch", "circle"]},
                    # Motion-graphic scene (agent/graphics.py): the visual is built from animated components instead of footage.
                    "graphic": {
                        "type": "object",
                        "required": ["layout"],
                        "properties": {
                            "layout": {"enum": ["title", "step", "strike", "punch"]},
                            "step": {"type": "string", "maxLength": 14},
                            "kicker": {"type": "string", "maxLength": 40},
                            "heading": {"type": "string", "maxLength": 30},
                            "heading2": {"type": "string", "maxLength": 30},
                            "heading_at": {"type": "string", "maxLength": 40},
                            "ghost": {"type": "string", "maxLength": 12},
                            "chips": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 24}},
                            "items": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 60}},
                            "reveal": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 40}},
                            "mock": {
                                "type": "object",
                                "required": ["type"],
                                "properties": {
                                    "type": {"enum": ["terminal", "comment", "checklist", "browser", "file", "window"]},
                                    "title": {"type": "string", "maxLength": 30},
                                    "items": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 60}},
                                },
                            },
                        },
                    },
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
                    # Reserved for later phases (Lottie overlays); accepted so plans stay forward compatible, ignored.
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
