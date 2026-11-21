"""
Open-Humanizer
==============

Drop-in open-source adversarial loop to rewrite AI text into human prose.

Public API
----------
>>> from open_humanizer import HumanizerPipeline
>>> engine = HumanizerPipeline(api_key="sk-...")
>>> result = engine.humanize("Furthermore, it is paramount to delve into...")
>>> print(result["text"])
"""

from typing import Any, Dict

from open_humanizer.pipeline import Humanizer, HumanizerPipeline
from open_humanizer.exceptions import (
    APIResponseError,
    EmptyTextError,
    OpenHumanizerError,
    ScannerParseError,
)
from open_humanizer.heuristics import HeuristicReport, analyze as _analyze_report

__version__ = "1.0.0"


def analyze_local(text: str) -> Dict[str, Any]:
    """
    Free offline AI-fingerprint heuristics (no API key required).

    Returns a JSON-serializable dict with overall_ai_percentage, banned_hits,
    burstiness_score, notes, and related stylometric fields.
    """
    return _analyze_report(text).to_dict()


__all__ = [
    "HumanizerPipeline",
    "Humanizer",
    "HeuristicReport",
    "analyze_local",
    "OpenHumanizerError",
    "ScannerParseError",
    "EmptyTextError",
    "APIResponseError",
    "__version__",
]
