"""Prompt assembly for Agent A (Writer) and Agent B (Critic)."""

from __future__ import annotations

from open_humanizer import config


class PromptManager:
    """Builds full prompt payloads for the adversarial loop."""

    @staticmethod
    def get_scanner_payload(text: str) -> str:
        """
        Build the Critic (Agent B) user prompt.

        Parameters
        ----------
        text:
            Document to score as AI-generated or human-like.
        """
        return (
            f"{config.DETECTOR_RULES}\n\n"
            f"Text to analyze:\n"
            f'"""{text}"""'
        )

    @staticmethod
    def get_humanizer_payload(
        text: str,
        flagged_details: str,
        current_score: float,
        local_heuristic_notes: str = "",
    ) -> str:
        """
        Build the Writer (Agent A) user prompt with Critic feedback.

        Parameters
        ----------
        text:
            Current document version to rewrite.
        flagged_details:
            Bullet list of high-confidence AI sentences and reasons.
        current_score:
            Overall AI percentage from the latest Critic scan.
        local_heuristic_notes:
            Optional notes from the offline stylometric heuristic layer.
        """
        heuristic_block = ""
        if local_heuristic_notes.strip():
            heuristic_block = (
                "\nAdditional offline stylometric signals:\n"
                f"{local_heuristic_notes}\n"
            )

        details = flagged_details.strip() or (
            "(No individual sentences crossed the flag threshold; "
            "rewrite holistically to raise burstiness and perplexity.)"
        )

        return (
            f"Review this original text document:\n"
            f'"""{text}"""\n\n'
            f"Our internal detector layer flagged it as AI-generated with a high "
            f"signature score of {current_score}%.\n"
            f"Here are the specific structural nodes that failed detection:\n"
            f"{details}\n"
            f"{heuristic_block}\n"
            f"Task: Rewrite the document. Focus heavily on mutating the flagged "
            f"segments to break their mathematical signatures completely using high "
            f"burstiness and unpredictable word pairings, while keeping unflagged "
            f"text stable where possible. Preserve all facts, names, numbers, and "
            f"SEO keywords. Return only the rewritten plain text."
        )

    @staticmethod
    def get_humanizer_system_prompt() -> str:
        """Return the Writer system prompt (style guide)."""
        return config.HUMANIZER_RULES
