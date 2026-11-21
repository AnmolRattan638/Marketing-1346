"""Tests for configuration constants and ban lists."""

from open_humanizer import config


def test_detector_rules_require_json_shape():
    assert "overall_ai_percentage" in config.DETECTOR_RULES
    assert "flagged_sentences" in config.DETECTOR_RULES
    assert "is_undetectable" in config.DETECTOR_RULES
    assert "raw JSON" in config.DETECTOR_RULES or "JSON object" in config.DETECTOR_RULES


def test_humanizer_rules_core_directives():
    rules = config.HUMANIZER_RULES.lower()
    assert "burstiness" in rules
    assert "perplexity" in rules
    assert "contractions" in rules
    assert "delve" in rules
    assert "furthermore" in rules


def test_ban_lists_nonempty_and_include_classics():
    assert "delve" in config.AI_BAN_WORDS
    assert "furthermore" in config.AI_BAN_WORDS
    assert any("delve" in p for p in config.AI_BAN_PHRASES)
    assert len(config.AI_BAN_PHRASES) >= 20
    assert len(config.COMMON_CONTRACTIONS) >= 10


def test_defaults_sane():
    assert config.DEFAULT_MAX_RETRIES >= 1
    assert 0 < config.DEFAULT_TARGET_SCORE <= 20
    assert config.DEFAULT_SCAN_TEMPERATURE < config.DEFAULT_MUTATE_TEMPERATURE
