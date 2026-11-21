"""
Command-line interface for Open-Humanizer.

Examples
--------
  open-humanizer --text "Furthermore, it is paramount to delve into..."
  open-humanizer --file draft.txt --max-retries 4 --target-score 8
  cat draft.txt | open-humanizer --stdin
  open-humanizer --text "..." --analyze-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from open_humanizer import config
from open_humanizer.exceptions import EmptyTextError, OpenHumanizerError
from open_humanizer.heuristics import analyze as heuristic_analyze
from open_humanizer.pipeline import HumanizerPipeline


def _read_input(args: argparse.Namespace) -> str:
    if args.stdin:
        return sys.stdin.read()
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            return fh.read()
    if args.text is not None:
        return args.text
    raise ValueError(
        "Provide --text, --file PATH, or --stdin. See open-humanizer --help."
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="open-humanizer",
        description=(
            "Open-source adversarial AI text humanizer. "
            "Rewrites AI drafts into high-burstiness human prose using a "
            "Writer ↔ Critic loop. Free alternative to paid ZeroGPT humanizers."
        ),
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--text", "-t", type=str, help="Raw text to humanize")
    src.add_argument("--file", "-f", type=str, help="Path to a UTF-8 text file")
    src.add_argument(
        "--stdin",
        action="store_true",
        help="Read text from standard input",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key (default: OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Optional OpenAI-compatible base URL",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=config.DEFAULT_MODEL,
        help=f"Model name (default: {config.DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=config.DEFAULT_MAX_RETRIES,
        help=f"Max adversarial cycles (default: {config.DEFAULT_MAX_RETRIES})",
    )
    parser.add_argument(
        "--target-score",
        type=float,
        default=config.DEFAULT_TARGET_SCORE,
        help=f"Success threshold AI%% (default: {config.DEFAULT_TARGET_SCORE})",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Run free offline heuristics only (no API calls)",
    )
    parser.add_argument(
        "--no-heuristics",
        action="store_true",
        help="Disable offline heuristic layer during humanize",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print full result as JSON",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Write humanized text (or JSON) to this file",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress logs; print only the result",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        text = _read_input(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: failed to read input: {exc}", file=sys.stderr)
        return 2

    if not (text or "").strip():
        print("error: empty input text", file=sys.stderr)
        return 2

    if args.analyze_only:
        report = heuristic_analyze(text)
        payload = report.to_dict()
        output = json.dumps(payload, indent=2) if args.as_json else (
            f"Local AI score: {report.overall_ai_percentage}%\n"
            f"Burstiness: {report.burstiness_score}\n"
            f"Words: {report.word_count} | Sentences: {report.sentence_count}\n"
            f"Ban hits: {len(report.banned_hits)}\n"
            + ("\n".join(f"  - {n}" for n in report.notes) if report.notes else "")
        )
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(output if args.as_json else json.dumps(payload, indent=2))
        print(output)
        return 0

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get(
        "OPENHUMANIZER_API_KEY"
    )
    if not api_key:
        print(
            "error: set OPENAI_API_KEY or pass --api-key "
            "(or use --analyze-only for free offline scoring)",
            file=sys.stderr,
        )
        return 2

    if args.quiet:
        import logging

        logging.getLogger("open_humanizer").setLevel(logging.WARNING)

    try:
        engine = HumanizerPipeline(
            api_key=api_key,
            base_url=args.base_url,
            model_name=args.model,
            use_heuristics=not args.no_heuristics,
        )
        result = engine.humanize(
            text,
            max_retries=args.max_retries,
            target_score=args.target_score,
        )
    except (EmptyTextError, OpenHumanizerError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — surface API/network errors cleanly
        print(f"error: humanization failed: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        rendered = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        rendered = result.get("text", "")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rendered if args.as_json else result.get("text", ""))
            if not args.as_json:
                fh.write("\n")

    print(rendered)

    if not args.as_json and not args.quiet:
        print(
            f"\n# status={result.get('status')} final_score={result.get('final_score')}",
            file=sys.stderr,
        )

    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
