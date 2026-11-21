"""Shared pytest fixtures for Open-Humanizer tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from open_humanizer.pipeline import HumanizerPipeline


def make_chat_response(content: str) -> SimpleNamespace:
    """Build a minimal OpenAI-like chat completion response."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def make_scanner_json(
    overall: float,
    flagged: Optional[List[Dict[str, Any]]] = None,
    undetectable: Optional[bool] = None,
) -> str:
    if undetectable is None:
        undetectable = overall < 10.0
    payload = {
        "overall_ai_percentage": overall,
        "flagged_sentences": flagged or [],
        "is_undetectable": undetectable,
    }
    return json.dumps(payload)


@pytest.fixture
def sample_ai_text() -> str:
    return (
        "Furthermore, it is paramount to delve into these metrics in today's world. "
        "Moreover, this comprehensive framework will revolutionize the paradigm and "
        "serve as a catalyst for robust innovation. It is important to note that "
        "leveraging these insights can seamlessly enhance outcomes across the landscape."
    )


@pytest.fixture
def sample_human_text() -> str:
    return (
        "Look, the numbers don't lie. Sales jumped 18% after we cut the checkout "
        "steps — messy experiment, honest results. I wouldn't call it a miracle. "
        "What actually moved the needle was the support team rewriting three emails "
        "by hand until they sounded like a real person wrote them at 11pm."
    )


@pytest.fixture
def mock_openai_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def pipeline_factory(mock_openai_client):
    """Factory that builds a HumanizerPipeline with a mock client."""

    def _factory(**kwargs) -> HumanizerPipeline:
        defaults = {
            "api_key": "test-key",
            "client": mock_openai_client,
            "use_heuristics": True,
        }
        defaults.update(kwargs)
        return HumanizerPipeline(**defaults)

    return _factory
