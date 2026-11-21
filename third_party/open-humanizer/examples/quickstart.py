#!/usr/bin/env python3
"""
Open-Humanizer quickstart example.

Usage:
  export OPENAI_API_KEY=sk-...
  python examples/quickstart.py

Optional:
  export OPENAI_BASE_URL=https://api.openai.com/v1
  export OPENHUMANIZER_MODEL=gpt-4o
"""

from __future__ import annotations

import json
import os
import sys

from open_humanizer import HumanizerPipeline, analyze_local


AI_DRAFT = """
Furthermore, it is paramount to delve into these metrics in today's digital age.
Moreover, this comprehensive framework will revolutionize the existing paradigm
and serve as a catalyst for robust, seamless innovation across the landscape.
It is important to note that leveraging these insights can enhance outcomes
and foster a dynamic interplay of multifaceted opportunities moving forward.
"""


def main() -> int:
    print("=== Offline heuristic pre-check (free, no API) ===")
    local = analyze_local(AI_DRAFT)
    print(json.dumps(local, indent=2))

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "\nNo OPENAI_API_KEY set — skipping live adversarial loop.\n"
            "Set OPENAI_API_KEY and re-run for full Writer↔Critic humanization.",
            file=sys.stderr,
        )
        return 0

    print("\n=== Adversarial humanization loop ===")
    engine = HumanizerPipeline(
        api_key=api_key,
        base_url=os.environ.get("OPENAI_BASE_URL"),
        model_name=os.environ.get("OPENHUMANIZER_MODEL", "gpt-4o"),
    )
    result = engine.humanize(AI_DRAFT, max_retries=3, target_score=10.0)
    print(json.dumps({k: v for k, v in result.items() if k != "text"}, indent=2))
    print("\n--- Humanized text ---\n")
    print(result["text"])
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
