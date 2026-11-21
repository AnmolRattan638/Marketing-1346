"""
Offline stylometric heuristics — free, zero-API local AI-fingerprint scoring.

These are *not* a replacement for commercial detectors. They approximate the
signals detectors care about so the adversarial loop can:

1. Pre-score text before spending an API call on the Critic.
2. Feed concrete mutation targets (banned phrases, low burstiness) to the Writer.
3. Work partially even when the Critic JSON parse fails.

Signals implemented
-------------------
- AI ban-list hits (phrases + words from config)
- Sentence-length burstiness (coefficient of variation + short/long pairing)
- Contraction density (humans use them; AI often avoids them)
- Type-token ratio proxy for lexical diversity
- Em-dash / stock-transition density
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from open_humanizer import config

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\[])|(?<=[.!?])\s*$", re.MULTILINE)
_WORD_RE = re.compile(r"[A-Za-z']+")
_EM_DASH_RE = re.compile(r"[—–]|&mdash;|--")


def split_sentences(text: str) -> List[str]:
    """Split text into sentences with a lightweight regex splitter."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    parts = _SENTENCE_SPLIT.split(cleaned)
    sentences = [p.strip() for p in parts if p and p.strip()]
    if not sentences:
        # Fallback: treat whole blob as one sentence
        return [cleaned]
    return sentences


def word_tokens(text: str) -> List[str]:
    """Lowercased alphabetic tokens including contractions."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text or "")]


@dataclass
class HeuristicReport:
    """Structured local AI-fingerprint analysis."""

    overall_ai_percentage: float
    sentence_count: int
    word_count: int
    banned_hits: List[Dict[str, str]] = field(default_factory=list)
    burstiness_score: float = 0.0  # 0 = flat AI-like, 100 = very human variance
    contraction_ratio: float = 0.0
    type_token_ratio: float = 0.0
    avg_sentence_length: float = 0.0
    sentence_length_std: float = 0.0
    em_dash_count: int = 0
    notes: List[str] = field(default_factory=list)

    def notes_block(self) -> str:
        """Format notes as a bullet list for the Writer prompt."""
        if not self.notes and not self.banned_hits:
            return ""
        lines: List[str] = []
        for note in self.notes:
            lines.append(f"- {note}")
        for hit in self.banned_hits[:12]:
            lines.append(
                f"- Banned AI marker '{hit['match']}' found near: \"{hit['context']}\""
            )
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, object]:
        """Serialize for JSON / public API consumers."""
        return {
            "overall_ai_percentage": self.overall_ai_percentage,
            "sentence_count": self.sentence_count,
            "word_count": self.word_count,
            "burstiness_score": self.burstiness_score,
            "contraction_ratio": self.contraction_ratio,
            "type_token_ratio": self.type_token_ratio,
            "avg_sentence_length": self.avg_sentence_length,
            "sentence_length_std": self.sentence_length_std,
            "em_dash_count": self.em_dash_count,
            "banned_hits": list(self.banned_hits),
            "notes": list(self.notes),
        }


def _find_banned_hits(text: str) -> List[Dict[str, str]]:
    """Locate ban-list phrases/words with short surrounding context."""
    lower = text.lower()
    hits: List[Dict[str, str]] = []
    seen_spans: List[Tuple[int, int]] = []

    # Longer phrases first so "delve into" beats "delve"
    phrases = sorted(config.AI_BAN_PHRASES, key=len, reverse=True)
    for phrase in phrases:
        start = 0
        needle = phrase.lower()
        while True:
            idx = lower.find(needle, start)
            if idx < 0:
                break
            end = idx + len(needle)
            # Skip overlapping hits
            if any(not (end <= s or idx >= e) for s, e in seen_spans):
                start = end
                continue
            # Word-boundary-ish check for single-token phrases
            if " " not in needle:
                before_ok = idx == 0 or not lower[idx - 1].isalpha()
                after_ok = end >= len(lower) or not lower[end].isalpha()
                if not (before_ok and after_ok):
                    start = end
                    continue
            ctx_start = max(0, idx - 40)
            ctx_end = min(len(text), end + 40)
            context = text[ctx_start:ctx_end].replace("\n", " ").strip()
            hits.append({"match": phrase, "context": context})
            seen_spans.append((idx, end))
            start = end
    return hits


def _sentence_lengths(sentences: Sequence[str]) -> List[int]:
    return [max(1, len(word_tokens(s))) for s in sentences]


def _std(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(var)


def _burstiness_from_lengths(lengths: Sequence[int]) -> Tuple[float, float, float]:
    """
    Return (burstiness_0_100, avg_len, std_len).

    Burstiness here is a normalized coefficient of variation of sentence length,
    scaled so ~0.5 CV ≈ 70 and very high variance caps at 100.
    """
    if not lengths:
        return 0.0, 0.0, 0.0
    floats = [float(x) for x in lengths]
    avg = sum(floats) / len(floats)
    std = _std(floats)
    if avg <= 0:
        return 0.0, avg, std
    cv = std / avg
    # Map CV: 0 -> 0, 0.15 -> ~25, 0.35 -> ~55, 0.6+ -> ~90–100
    score = max(0.0, min(100.0, (cv / 0.65) * 100.0))
    return score, avg, std


def analyze(text: str) -> HeuristicReport:
    """
    Run offline AI-fingerprint heuristics on ``text``.

    Returns a :class:`HeuristicReport` with an approximate ``overall_ai_percentage``
    (0 = looks human, 100 = looks strongly AI under these proxies).
    """
    raw = (text or "").strip()
    if not raw:
        return HeuristicReport(
            overall_ai_percentage=0.0,
            sentence_count=0,
            word_count=0,
            notes=["Empty text — nothing to score."],
        )

    sentences = split_sentences(raw)
    tokens = word_tokens(raw)
    word_count = len(tokens)
    lengths = _sentence_lengths(sentences)
    burstiness, avg_len, std_len = _burstiness_from_lengths(lengths)

    banned = _find_banned_hits(raw)
    ban_density = min(1.0, len(banned) / max(1.0, word_count / 40.0))

    contraction_count = sum(1 for t in tokens if t in config.COMMON_CONTRACTIONS)
    contraction_ratio = contraction_count / word_count if word_count else 0.0

    unique = len(set(tokens))
    ttr = unique / word_count if word_count else 0.0

    em_dashes = len(_EM_DASH_RE.findall(raw))

    notes: List[str] = []

    # Component scores toward AI-ness (each 0–100)
    ban_component = min(100.0, ban_density * 100.0 * 1.4)
    if banned:
        notes.append(
            f"Found {len(banned)} AI ban-list hit(s); remove or rephrase them."
        )

    # Low burstiness => high AI component
    flat_component = max(0.0, 100.0 - burstiness)
    if burstiness < 35:
        notes.append(
            "Low sentence-length burstiness (flat rhythm). Mix 3–6 word sentences "
            "with 25–35 word sentences."
        )

    # Few contractions => AI-like
    if contraction_ratio < 0.01 and word_count >= 40:
        contraction_component = 70.0
        notes.append(
            "Almost no contractions detected. Use don't/can't/it's/you'll naturally."
        )
    elif contraction_ratio < 0.025 and word_count >= 40:
        contraction_component = 40.0
        notes.append("Low contraction density — add natural contractions.")
    else:
        contraction_component = max(0.0, 25.0 - contraction_ratio * 400.0)

    # Very low lexical diversity on longer texts
    if word_count >= 80 and ttr < 0.42:
        diversity_component = 55.0
        notes.append(
            f"Low type-token ratio ({ttr:.2f}). Increase lexical variety / perplexity."
        )
    elif word_count >= 80 and ttr < 0.5:
        diversity_component = 30.0
    else:
        diversity_component = 0.0

    # Em-dash spam
    em_component = 0.0
    if word_count:
        em_per_100 = em_dashes / (word_count / 100.0)
        if em_per_100 > 2.5:
            em_component = min(40.0, em_per_100 * 10.0)
            notes.append("Heavy em-dash usage — a common modern LLM fingerprint.")

    # Uniform mid-length sentences (classic LLM)
    uniform_component = 0.0
    if len(lengths) >= 4 and std_len < 3.5 and 12 <= avg_len <= 22:
        uniform_component = 45.0
        notes.append(
            "Sentences cluster in a narrow mid-length band — classic low-burstiness AI."
        )

    overall = (
        ban_component * 0.30
        + flat_component * 0.28
        + contraction_component * 0.18
        + diversity_component * 0.12
        + em_component * 0.06
        + uniform_component * 0.06
    )
    overall = max(0.0, min(100.0, round(overall, 2)))

    if overall < 15 and not notes:
        notes.append("Local heuristics look relatively human-like.")

    return HeuristicReport(
        overall_ai_percentage=overall,
        sentence_count=len(sentences),
        word_count=word_count,
        banned_hits=banned,
        burstiness_score=round(burstiness, 2),
        contraction_ratio=round(contraction_ratio, 4),
        type_token_ratio=round(ttr, 4),
        avg_sentence_length=round(avg_len, 2),
        sentence_length_std=round(std_len, 2),
        em_dash_count=em_dashes,
        notes=notes,
    )
