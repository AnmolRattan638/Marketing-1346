"""Start the run again automatically after a failed script run.

When the script stage fails (for example a script is rejected on every try, pronunciation included), the workflow has by then SAVED the lessons (data/script_lessons.json, with the concrete
mistake). This step then starts the same workflow again, so the new run begins AFTER the failure and already reads those lessons in its prompt. It waits a little first (a provider
that just failed is rarely ready that second), tells you in Telegram what went wrong and which attempt this is, and stops after RETRY_MAX attempts so it can never loop.

    python -m src.retry --workflow daily-draft.yml        # attempt number from RETRY_ATTEMPT, limit RETRY_MAX (3), wait RETRY_DELAY seconds (120)

Starting a workflow twice in one day is already safe: a run that finds today's draft/script done stays quiet, and a failed run saved none."""
from __future__ import annotations

import argparse
import datetime
import os
import sys
import time

import requests

from . import config, scriptlessons

DEFAULT_MAX, DEFAULT_DELAY = 3, 120


def recent_mistakes(limit: int = 3) -> list[str]:
    """The concrete mistakes saved today by the failed run (newest first), in the lessons file the next run reads."""
    today = datetime.date.today().isoformat()
    rows = []
    for key, row in scriptlessons.load().items():
        for r in row.get("recent", []):
            if r.get("on") == today:
                rows.append((key, r.get("mistake", "")))
    return [m for _, m in rows[::-1]][:limit]


def decide(attempt: int, max_attempts: int) -> int | None:
    """-> the next attempt number, or None when the limit is reached."""
    return attempt + 1 if attempt < max_attempts else None


def run(workflow: str, attempt: int = 1, max_attempts: int = DEFAULT_MAX, delay: float = DEFAULT_DELAY, ref: str = "main",
        token: str | None = None, post=requests.post, send=None, sleep=time.sleep) -> int:
    """0 = restarted or deliberately stopped at the limit; 1 = the restart itself failed (you are told)."""
    if send is None:
        from . import tg
        send = tg.send

    def tell(text: str) -> None:
        try:
            send(text)
        except Exception as e:                                     # a missing Telegram setup must never hide the retry itself
            print(f"[retry] telegram: {e}", file=sys.stderr)

    why = recent_mistakes()
    why_txt = ("\nWhat went wrong (saved as a lesson for the next run):\n- " + "\n- ".join(m[:240] for m in why)) if why else ""
    nxt = decide(attempt, max_attempts)
    if nxt is None:
        tell(f"{workflow} failed {attempt} times in a row, so I stopped. Nothing was posted.{why_txt}\nStart it again by hand when you are ready; the lessons above are already saved.")
        return 0
    token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
    if not token:
        tell(f"{workflow} failed but I have no GitHub token to start it again.{why_txt}")
        return 1
    sleep(max(0.0, delay))
    r = post(f"https://api.github.com/repos/{config.REPO}/actions/workflows/{workflow}/dispatches", timeout=30,
             headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, json={"ref": ref, "inputs": {"attempt": str(nxt)}})
    if r.status_code != 204:
        tell(f"{workflow} failed and I could not start it again (GitHub said HTTP {r.status_code}).{why_txt}")
        return 1
    tell(f"{workflow} failed, so I started it again automatically (attempt {nxt} of {max_attempts}). The new run reads the lessons from this failure.{why_txt}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True, help="workflow file name, e.g. daily-draft.yml")
    a = ap.parse_args()
    num = lambda name, default: int(float(os.getenv(name) or default))
    raise SystemExit(run(a.workflow, attempt=num("RETRY_ATTEMPT", 1), max_attempts=num("RETRY_MAX", DEFAULT_MAX), delay=num("RETRY_DELAY", DEFAULT_DELAY),
                         ref=os.getenv("GITHUB_REF_NAME") or "main"))


if __name__ == "__main__":
    main()
