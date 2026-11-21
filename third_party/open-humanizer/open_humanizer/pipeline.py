"""
Adversarial humanization pipeline.

Agent A (Writer) rewrites text under a human style guide.
Agent B (Critic) scores the text like an aggressive AI detector.
A local heuristic layer adds free offline stylometric signals.

The loop runs until the text is undetectable (score <= target) or
``max_retries`` cycles are exhausted.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator

from open_humanizer import config
from open_humanizer.exceptions import (
    APIResponseError,
    EmptyTextError,
    ScannerParseError,
)
from open_humanizer.heuristics import HeuristicReport, analyze as heuristic_analyze
from open_humanizer.prompt_manager import PromptManager

logger = logging.getLogger("open_humanizer")

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Pydantic models (Critic JSON schema)
# ---------------------------------------------------------------------------


class SentenceAnalysis(BaseModel):
    """One Critic-flagged sentence with confidence and rationale."""

    sentence: str
    ai_confidence_score: float = Field(ge=0.0, le=100.0)
    reason_for_flag: str

    @field_validator("ai_confidence_score", mode="before")
    @classmethod
    def _clamp_score(cls, v: Any) -> float:
        try:
            val = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("ai_confidence_score must be numeric") from exc
        return max(0.0, min(100.0, val))


class ScannerReport(BaseModel):
    """Full Critic report for a document version."""

    overall_ai_percentage: float = Field(ge=0.0, le=100.0)
    flagged_sentences: List[SentenceAnalysis] = Field(default_factory=list)
    is_undetectable: bool = False

    @field_validator("overall_ai_percentage", mode="before")
    @classmethod
    def _clamp_overall(cls, v: Any) -> float:
        try:
            val = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("overall_ai_percentage must be numeric") from exc
        return max(0.0, min(100.0, val))

    @field_validator("is_undetectable", mode="before")
    @classmethod
    def _coerce_bool(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"true", "1", "yes"}
        return bool(v)


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)


def _extract_json_object(raw: str) -> Dict[str, Any]:
    """
    Parse a JSON object from model output, tolerating markdown fences
    and leading/trailing prose.
    """
    if raw is None:
        raise ScannerParseError("Critic returned empty content")

    text = raw.strip()
    if not text:
        raise ScannerParseError("Critic returned empty content")

    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Fenced ```json ... ```
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        try:
            data = json.loads(fence.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # First {...} span
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as exc:
            raise ScannerParseError(
                f"Failed to parse Critic JSON: {exc}"
            ) from exc

    raise ScannerParseError(
        f"Critic response was not valid JSON. Preview: {text[:240]!r}"
    )


def _message_content(response: Any) -> str:
    """Safely pull the assistant message content from an OpenAI response."""
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise APIResponseError(
            f"Malformed API response structure: {exc}"
        ) from exc
    if content is None:
        raise APIResponseError("API returned null message content")
    return str(content)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class HumanizerPipeline:
    """
    Production adversarial humanizer.

    Parameters
    ----------
    api_key:
        OpenAI-compatible API key.
    base_url:
        Optional custom base URL (OpenRouter, Azure, local vLLM, Ollama, etc.).
    model_name:
        Chat model id (default: ``gpt-4o``).
    use_heuristics:
        When True, blend offline stylometric notes into Writer prompts and
        attach heuristic metrics to the result payload.
    scan_temperature:
        Critic sampling temperature (low = more consistent JSON scoring).
    mutate_temperature:
        Writer sampling temperature (higher = more lexical variance / perplexity).
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model_name: str = config.DEFAULT_MODEL,
        use_heuristics: bool = True,
        scan_temperature: float = config.DEFAULT_SCAN_TEMPERATURE,
        mutate_temperature: float = config.DEFAULT_MUTATE_TEMPERATURE,
        client: Optional[OpenAI] = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("api_key is required unless a prebuilt client is passed")

        if client is not None:
            self.client = client
        elif base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)

        self.model = model_name
        self.use_heuristics = use_heuristics
        self.scan_temperature = scan_temperature
        self.mutate_temperature = mutate_temperature

    # -- Critic ------------------------------------------------------------

    def _scan(self, text: str) -> ScannerReport:
        prompt = PromptManager.get_scanner_payload(text)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.scan_temperature,
            response_format={"type": "json_object"},
        )
        raw = _message_content(response)
        try:
            payload = _extract_json_object(raw)
            report = ScannerReport(**payload)
        except (ScannerParseError, ValidationError, TypeError) as exc:
            logger.warning("Critic parse failed (%s); attempting repair pass", exc)
            report = self._scan_repair(text, raw)

        # Enforce policy: undetectable only under threshold
        if report.overall_ai_percentage >= config.UNDETECTABLE_THRESHOLD:
            report.is_undetectable = False
        elif report.overall_ai_percentage < config.UNDETECTABLE_THRESHOLD:
            report.is_undetectable = True
        return report

    def _scan_repair(self, text: str, bad_raw: str) -> ScannerReport:
        """One-shot repair if the Critic returns broken JSON."""
        repair_prompt = (
            "Your previous analysis was not valid JSON. "
            "Re-analyze the text and respond with ONLY a raw JSON object matching:\n"
            '{"overall_ai_percentage": 0-100, "flagged_sentences": '
            '[{"sentence": "...", "ai_confidence_score": 0-100, '
            '"reason_for_flag": "..."}], "is_undetectable": true|false}\n\n'
            f'Previous invalid output (for reference only):\n{bad_raw[:1500]}\n\n'
            f'Text to analyze:\n"""{text}"""'
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": repair_prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = _message_content(response)
        try:
            payload = _extract_json_object(raw)
            return ScannerReport(**payload)
        except (ScannerParseError, ValidationError, TypeError) as exc:
            # Last resort: synthesize a report from local heuristics
            logger.error("Critic repair failed (%s); falling back to heuristics", exc)
            return self._heuristic_as_scanner_report(text)

    def _heuristic_as_scanner_report(self, text: str) -> ScannerReport:
        h = heuristic_analyze(text)
        flagged: List[SentenceAnalysis] = []
        for hit in h.banned_hits[:20]:
            flagged.append(
                SentenceAnalysis(
                    sentence=hit.get("context", hit.get("match", "")),
                    ai_confidence_score=85.0,
                    reason_for_flag=f"Local ban-list hit: '{hit.get('match', '')}'",
                )
            )
        score = h.overall_ai_percentage
        return ScannerReport(
            overall_ai_percentage=score,
            flagged_sentences=flagged,
            is_undetectable=score < config.UNDETECTABLE_THRESHOLD,
        )

    # -- Writer ------------------------------------------------------------

    def _format_flagged_details(self, report: ScannerReport) -> str:
        lines: List[str] = []
        for s in report.flagged_sentences:
            if s.ai_confidence_score > config.FLAG_CONFIDENCE_THRESHOLD:
                lines.append(
                    f"- Sentence: '{s.sentence}'\n"
                    f"  Score: {s.ai_confidence_score}\n"
                    f"  Reason: {s.reason_for_flag}"
                )
        return "\n".join(lines)

    def _mutate(
        self,
        text: str,
        report: ScannerReport,
        heuristic: Optional[HeuristicReport] = None,
    ) -> str:
        flagged_details = self._format_flagged_details(report)
        local_notes = ""
        if heuristic is not None:
            local_notes = heuristic.notes_block()

        prompt = PromptManager.get_humanizer_payload(
            text=text,
            flagged_details=flagged_details,
            current_score=report.overall_ai_percentage,
            local_heuristic_notes=local_notes,
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": PromptManager.get_humanizer_system_prompt(),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.mutate_temperature,
        )
        rewritten = _message_content(response).strip()
        if not rewritten:
            raise APIResponseError("Writer returned empty rewrite")
        # Strip accidental wrapping quotes / fences
        rewritten = self._clean_rewrite_output(rewritten)
        return rewritten

    @staticmethod
    def _clean_rewrite_output(text: str) -> str:
        cleaned = text.strip()
        # Drop markdown fences if the model ignored instructions
        fence = re.match(r"^```(?:\w+)?\s*([\s\S]*?)\s*```$", cleaned)
        if fence:
            cleaned = fence.group(1).strip()
        # Drop common preambles
        for prefix in (
            "Here is the rewritten",
            "Here's the rewritten",
            "Rewritten text:",
            "Here is the rewrite:",
            "Sure, here",
        ):
            if cleaned.lower().startswith(prefix.lower()):
                # Cut first line
                parts = cleaned.split("\n", 1)
                cleaned = parts[1].strip() if len(parts) > 1 else cleaned
                break
        return cleaned

    # -- Public API --------------------------------------------------------

    def analyze_local(self, text: str) -> Dict[str, Any]:
        """
        Run free offline heuristics only (no API calls).

        Useful for CI, pre-checks, or users without an API key for a first pass.
        """
        if not (text or "").strip():
            raise EmptyTextError("text must be a non-empty string")
        return heuristic_analyze(text).to_dict()

    def humanize(
        self,
        text: str,
        max_retries: int = config.DEFAULT_MAX_RETRIES,
        target_score: float = config.DEFAULT_TARGET_SCORE,
    ) -> Dict[str, Any]:
        """
        Run the adversarial Writer ↔ Critic loop until undetectable or exhausted.

        Parameters
        ----------
        text:
            Source document (typically AI-drafted) to humanize.
        max_retries:
            Maximum scan→mutate cycles (default 3).
        target_score:
            Success when Critic ``overall_ai_percentage`` is <= this value
            (default 10.0).

        Returns
        -------
        dict with keys:
            status, final_score, text, metrics_history, and optional heuristics.
        """
        if not isinstance(text, str) or not text.strip():
            raise EmptyTextError("text must be a non-empty string")
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if not (0.0 <= target_score <= 100.0):
            raise ValueError("target_score must be between 0 and 100")

        current_text = text.strip()
        execution_history: List[Dict[str, Any]] = []
        last_heuristic: Optional[HeuristicReport] = None

        for attempt in range(max_retries):
            logger.info(
                "Humanization cycle running: Attempt %s/%s",
                attempt + 1,
                max_retries,
            )

            if self.use_heuristics:
                last_heuristic = heuristic_analyze(current_text)
                logger.info(
                    "Local heuristic AI%%=%.2f burstiness=%.2f ban_hits=%s",
                    last_heuristic.overall_ai_percentage,
                    last_heuristic.burstiness_score,
                    len(last_heuristic.banned_hits),
                )

            report = self._scan(current_text)
            cycle_metrics: Dict[str, Any] = {
                "cycle": attempt + 1,
                "ai_percentage": report.overall_ai_percentage,
                "flagged_sentence_count": len(report.flagged_sentences),
                "is_undetectable": report.is_undetectable,
            }
            if last_heuristic is not None:
                cycle_metrics["local_heuristic_ai_percentage"] = (
                    last_heuristic.overall_ai_percentage
                )
                cycle_metrics["local_burstiness"] = last_heuristic.burstiness_score
            execution_history.append(cycle_metrics)

            logger.info(
                "Critic score=%.2f flagged=%s undetectable=%s",
                report.overall_ai_percentage,
                len(report.flagged_sentences),
                report.is_undetectable,
            )

            if report.is_undetectable or report.overall_ai_percentage <= target_score:
                return self._success_payload(
                    current_text,
                    report.overall_ai_percentage,
                    execution_history,
                    last_heuristic,
                )

            # Mutate for next cycle (skip mutate after last eval only if we're done)
            current_text = self._mutate(current_text, report, last_heuristic)

        # Exhausted rewrite budget — final scan of last mutation
        if self.use_heuristics:
            last_heuristic = heuristic_analyze(current_text)
        final_report = self._scan(current_text)
        execution_history.append(
            {
                "cycle": max_retries + 1,
                "ai_percentage": final_report.overall_ai_percentage,
                "flagged_sentence_count": len(final_report.flagged_sentences),
                "is_undetectable": final_report.is_undetectable,
                "phase": "final_scan",
            }
        )

        if (
            final_report.is_undetectable
            or final_report.overall_ai_percentage <= target_score
        ):
            return self._success_payload(
                current_text,
                final_report.overall_ai_percentage,
                execution_history,
                last_heuristic,
            )

        result: Dict[str, Any] = {
            "status": "max_cycles_exhausted",
            "final_score": final_report.overall_ai_percentage,
            "text": current_text,
            "metrics_history": execution_history,
        }
        if last_heuristic is not None:
            result["local_heuristics"] = {
                "overall_ai_percentage": last_heuristic.overall_ai_percentage,
                "burstiness_score": last_heuristic.burstiness_score,
                "banned_hits": last_heuristic.banned_hits,
                "notes": last_heuristic.notes,
            }
        return result

    def _success_payload(
        self,
        text: str,
        score: float,
        history: List[Dict[str, Any]],
        heuristic: Optional[HeuristicReport],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "status": "success",
            "final_score": score,
            "text": text,
            "metrics_history": history,
        }
        if heuristic is not None:
            payload["local_heuristics"] = {
                "overall_ai_percentage": heuristic.overall_ai_percentage,
                "burstiness_score": heuristic.burstiness_score,
                "banned_hits": heuristic.banned_hits,
                "notes": heuristic.notes,
            }
        return payload


# Convenience alias for shorter imports in notebooks
Humanizer = HumanizerPipeline
