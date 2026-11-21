"""Tests for HumanizerPipeline with mocked OpenAI client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from open_humanizer.exceptions import EmptyTextError, ScannerParseError
from open_humanizer.pipeline import (
    HumanizerPipeline,
    ScannerReport,
    SentenceAnalysis,
    _extract_json_object,
    _message_content,
)
from tests.conftest import make_chat_response, make_scanner_json


class TestJsonExtraction:
    def test_raw_json(self):
        data = _extract_json_object('{"overall_ai_percentage": 12, "flagged_sentences": [], "is_undetectable": false}')
        assert data["overall_ai_percentage"] == 12

    def test_fenced_json(self):
        raw = '```json\n{"overall_ai_percentage": 5, "flagged_sentences": [], "is_undetectable": true}\n```'
        data = _extract_json_object(raw)
        assert data["is_undetectable"] is True

    def test_prose_wrapped_json(self):
        raw = 'Here you go:\n{"overall_ai_percentage": 40, "flagged_sentences": [], "is_undetectable": false}\nThanks'
        data = _extract_json_object(raw)
        assert data["overall_ai_percentage"] == 40

    def test_invalid_raises(self):
        with pytest.raises(ScannerParseError):
            _extract_json_object("not json at all")


class TestMessageContent:
    def test_ok(self):
        resp = make_chat_response("hello")
        assert _message_content(resp) == "hello"

    def test_empty_choices(self):
        from open_humanizer.exceptions import APIResponseError

        with pytest.raises(APIResponseError):
            _message_content(MagicMock(choices=[]))


class TestScannerReportModel:
    def test_clamps_and_validates(self):
        r = ScannerReport(
            overall_ai_percentage=150,
            flagged_sentences=[
                {
                    "sentence": "x",
                    "ai_confidence_score": -5,
                    "reason_for_flag": "test",
                }
            ],
            is_undetectable="true",
        )
        assert r.overall_ai_percentage == 100.0
        assert r.flagged_sentences[0].ai_confidence_score == 0.0
        assert r.is_undetectable is True


class TestHumanizerPipeline:
    def test_requires_api_key_without_client(self):
        with pytest.raises(ValueError):
            HumanizerPipeline(api_key="")

    def test_empty_text_raises(self, pipeline_factory):
        engine = pipeline_factory()
        with pytest.raises(EmptyTextError):
            engine.humanize("   ")

    def test_invalid_max_retries(self, pipeline_factory, sample_ai_text):
        engine = pipeline_factory()
        with pytest.raises(ValueError):
            engine.humanize(sample_ai_text, max_retries=0)

    def test_success_first_scan_already_human(
        self, pipeline_factory, mock_openai_client, sample_human_text
    ):
        mock_openai_client.chat.completions.create.return_value = make_chat_response(
            make_scanner_json(4.5, undetectable=True)
        )
        engine = pipeline_factory()
        result = engine.humanize(sample_human_text, max_retries=3, target_score=10.0)

        assert result["status"] == "success"
        assert result["final_score"] == 4.5
        assert result["text"] == sample_human_text.strip()
        assert len(result["metrics_history"]) == 1
        # Only scan, no mutate
        assert mock_openai_client.chat.completions.create.call_count == 1

    def test_mutate_then_success(
        self, pipeline_factory, mock_openai_client, sample_ai_text
    ):
        humanized = (
            "The metrics matter. We dug into the numbers ourselves after the "
            "Q3 drop and found the funnel was leaking at checkout — not strategy decks."
        )
        scan_high = make_chat_response(
            make_scanner_json(
                92.0,
                flagged=[
                    {
                        "sentence": "Furthermore, it is paramount to delve into these metrics.",
                        "ai_confidence_score": 98.0,
                        "reason_for_flag": "AI transitions",
                    }
                ],
            )
        )
        mutate = make_chat_response(humanized)
        scan_low = make_chat_response(make_scanner_json(7.0, undetectable=True))

        mock_openai_client.chat.completions.create.side_effect = [
            scan_high,
            mutate,
            scan_low,
        ]

        engine = pipeline_factory()
        result = engine.humanize(sample_ai_text, max_retries=3, target_score=10.0)

        assert result["status"] == "success"
        assert result["final_score"] == 7.0
        assert result["text"] == humanized
        assert len(result["metrics_history"]) == 2
        assert mock_openai_client.chat.completions.create.call_count == 3

    def test_max_cycles_exhausted(
        self, pipeline_factory, mock_openai_client, sample_ai_text
    ):
        # Each cycle: scan (high) + mutate; after loop final scan (high)
        high = make_chat_response(make_scanner_json(80.0))
        mut = make_chat_response("Slightly rewritten body with still AI flavor furthermore.")

        # max_retries=2 => scan, mut, scan, mut, final_scan = 5 calls
        mock_openai_client.chat.completions.create.side_effect = [
            high,
            mut,
            high,
            mut,
            high,
        ]

        engine = pipeline_factory(use_heuristics=False)
        result = engine.humanize(sample_ai_text, max_retries=2, target_score=10.0)

        assert result["status"] == "max_cycles_exhausted"
        assert result["final_score"] == 80.0
        assert "text" in result
        assert len(result["metrics_history"]) >= 2

    def test_scan_repair_on_bad_json(
        self, pipeline_factory, mock_openai_client, sample_ai_text
    ):
        bad = make_chat_response("I think this is like 90% AI lol")
        good = make_chat_response(make_scanner_json(9.0, undetectable=True))
        mock_openai_client.chat.completions.create.side_effect = [bad, good]

        engine = pipeline_factory(use_heuristics=False)
        result = engine.humanize(sample_ai_text, max_retries=2)
        assert result["status"] == "success"
        assert result["final_score"] == 9.0

    def test_scan_falls_back_to_heuristics_when_repair_fails(
        self, pipeline_factory, mock_openai_client, sample_ai_text
    ):
        bad1 = make_chat_response("not json")
        bad2 = make_chat_response("still not json")
        # After heuristic fallback report will be high AI for sample_ai_text,
        # then mutate, then we need more responses... simplify: use target that
        # might not pass. We'll just assert _scan path works via humanize one cycle.
        mut = make_chat_response("Rewritten without banned words hopefully.")
        # final path: first scan fails+repair fails -> heuristic report (high),
        # mutate, second scan fails+repair fails -> heuristic, maybe still high,
        # etc. Keep max_retries=1
        mock_openai_client.chat.completions.create.side_effect = [
            bad1,
            bad2,  # repair for scan 1
            mut,
            bad1,
            bad2,  # final scan repair
        ]
        engine = pipeline_factory(use_heuristics=True)
        result = engine.humanize(sample_ai_text, max_retries=1, target_score=0.0)
        assert result["status"] in {"success", "max_cycles_exhausted"}
        assert "final_score" in result
        assert result["text"]

    def test_analyze_local(self, pipeline_factory, sample_ai_text):
        engine = pipeline_factory()
        local = engine.analyze_local(sample_ai_text)
        assert "overall_ai_percentage" in local
        assert local["word_count"] > 0
        assert isinstance(local["banned_hits"], list)

    def test_clean_rewrite_strips_fence(self):
        cleaned = HumanizerPipeline._clean_rewrite_output(
            "```markdown\nHello world.\n```"
        )
        assert cleaned == "Hello world."

    def test_base_url_client_construction(self):
        # Should not raise; uses real OpenAI client object construction
        engine = HumanizerPipeline(
            api_key="sk-test",
            base_url="https://example.com/v1",
            model_name="gpt-4o-mini",
        )
        assert engine.model == "gpt-4o-mini"
        assert engine.client is not None

    def test_format_flagged_filters_low_confidence(self, pipeline_factory):
        engine = pipeline_factory()
        report = ScannerReport(
            overall_ai_percentage=70,
            flagged_sentences=[
                SentenceAnalysis(
                    sentence="low",
                    ai_confidence_score=20,
                    reason_for_flag="meh",
                ),
                SentenceAnalysis(
                    sentence="high",
                    ai_confidence_score=90,
                    reason_for_flag="AI marker",
                ),
            ],
        )
        details = engine._format_flagged_details(report)
        assert "high" in details
        assert "low" not in details
