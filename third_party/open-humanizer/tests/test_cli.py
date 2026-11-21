"""CLI tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from open_humanizer.cli import main
from tests.conftest import make_chat_response, make_scanner_json


def test_cli_analyze_only(capsys, sample_ai_text):
    code = main(["--analyze-only", "--text", sample_ai_text, "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "overall_ai_percentage" in data
    assert data["word_count"] > 0


def test_cli_missing_input():
    code = main([])
    assert code == 2


def test_cli_humanize_success(capsys, sample_human_text, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_chat_response(
        make_scanner_json(3.0, undetectable=True)
    )

    with patch("open_humanizer.cli.HumanizerPipeline") as Pipe:
        instance = MagicMock()
        instance.humanize.return_value = {
            "status": "success",
            "final_score": 3.0,
            "text": sample_human_text,
            "metrics_history": [],
        }
        Pipe.return_value = instance
        code = main(["--text", sample_human_text, "--json", "-q"])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "success"


def test_cli_requires_api_key_for_humanize(capsys, sample_ai_text, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENHUMANIZER_API_KEY", raising=False)
    code = main(["--text", sample_ai_text])
    assert code == 2
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY" in err or "api-key" in err.lower()


def test_cli_file_input(tmp_path, capsys, sample_ai_text):
    path = tmp_path / "draft.txt"
    path.write_text(sample_ai_text, encoding="utf-8")
    code = main(["--analyze-only", "--file", str(path), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["word_count"] > 0
