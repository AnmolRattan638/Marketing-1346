"""Custom exceptions for Open-Humanizer."""

from __future__ import annotations


class OpenHumanizerError(Exception):
    """Base exception for all Open-Humanizer errors."""


class ScannerParseError(OpenHumanizerError):
    """Raised when the Critic (Agent B) returns unparseable or invalid JSON."""


class EmptyTextError(OpenHumanizerError):
    """Raised when the caller passes empty or whitespace-only text."""


class APIResponseError(OpenHumanizerError):
    """Raised when the LLM API returns an empty or malformed completion."""
