"""Tests for offline stylometric heuristics."""

from open_humanizer.heuristics import analyze, split_sentences, word_tokens


def test_split_sentences_basic():
    text = "One. Two? Three!"
    sents = split_sentences(text)
    assert len(sents) >= 2


def test_word_tokens_includes_contractions():
    tokens = word_tokens("Don't worry, it's fine.")
    assert "don't" in tokens
    assert "it's" in tokens


def test_ai_heavy_text_scores_higher_than_human(sample_ai_text, sample_human_text):
    ai = analyze(sample_ai_text)
    human = analyze(sample_human_text)
    assert ai.overall_ai_percentage > human.overall_ai_percentage
    assert len(ai.banned_hits) > 0
    assert ai.banned_hits  # delve / furthermore etc.


def test_banned_hits_detect_delve_and_furthermore():
    text = "Furthermore, we should delve into the tapestry of issues."
    report = analyze(text)
    matches = {h["match"].lower() for h in report.banned_hits}
    assert any("furthermore" in m for m in matches)
    assert any("delve" in m for m in matches)


def test_human_text_has_higher_burstiness_or_contractions(sample_human_text):
    report = analyze(sample_human_text)
    assert report.word_count > 10
    # At least one of: decent burstiness, contractions, few bans
    assert (
        report.contraction_ratio > 0
        or report.burstiness_score > 20
        or len(report.banned_hits) == 0
    )


def test_empty_text():
    report = analyze("   ")
    assert report.word_count == 0
    assert report.overall_ai_percentage == 0.0


def test_notes_block_format(sample_ai_text):
    report = analyze(sample_ai_text)
    block = report.notes_block()
    assert isinstance(block, str)
    if report.notes or report.banned_hits:
        assert "-" in block


def test_analyze_returns_stable_fields():
    report = analyze("Short sample. Another line here with more words for density.")
    assert 0 <= report.overall_ai_percentage <= 100
    assert report.sentence_count >= 1
    assert report.word_count >= 1


def test_to_dict_and_public_analyze_local():
    from open_humanizer import analyze_local

    report = analyze("Furthermore, delve into the tapestry.")
    as_dict = report.to_dict()
    assert as_dict["overall_ai_percentage"] == report.overall_ai_percentage
    assert "banned_hits" in as_dict

    public = analyze_local("Furthermore, delve into the tapestry.")
    assert isinstance(public, dict)
    assert public["word_count"] > 0
    assert public["overall_ai_percentage"] >= 0
