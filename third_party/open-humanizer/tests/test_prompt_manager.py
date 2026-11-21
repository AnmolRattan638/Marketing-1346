"""Tests for PromptManager payload assembly."""

from open_humanizer.prompt_manager import PromptManager
from open_humanizer import config


def test_scanner_payload_includes_rules_and_text():
    text = "Hello world. This is a test."
    payload = PromptManager.get_scanner_payload(text)
    assert config.DETECTOR_RULES.strip()[:40] in payload
    assert text in payload
    assert "Text to analyze" in payload


def test_humanizer_payload_includes_score_and_flags():
    text = "Original document body."
    flags = "- Sentence: 'Furthermore x'\n  Reason: AI transition"
    payload = PromptManager.get_humanizer_payload(text, flags, 88.5)
    assert text in payload
    assert "88.5" in payload
    assert "Furthermore" in payload
    assert "Rewrite" in payload or "rewrite" in payload


def test_humanizer_payload_with_heuristic_notes():
    payload = PromptManager.get_humanizer_payload(
        "body",
        "",
        70.0,
        local_heuristic_notes="- Low burstiness detected",
    )
    assert "Low burstiness" in payload
    assert "offline stylometric" in payload.lower() or "Additional offline" in payload


def test_humanizer_payload_empty_flags_gets_fallback_message():
    payload = PromptManager.get_humanizer_payload("body", "   ", 55.0)
    assert "No individual sentences" in payload or "rewrite holistically" in payload


def test_system_prompt_matches_config():
    assert PromptManager.get_humanizer_system_prompt() == config.HUMANIZER_RULES
