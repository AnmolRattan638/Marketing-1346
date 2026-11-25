"""Redo ONLY the LinkedIn post of the draft that is waiting for your tap.

    python -m src.relinkedin --check    # is there a pending draft to redo? (exit 0 yes; exit 3 no, and Telegram says why)
    python -m src.relinkedin            # write a new LinkedIn post with the new writer and send a fresh Approve / Reject message

Everything else in the draft (Instagram, Bluesky, image, reel, replies) is left exactly as it was. Tapping Approve publishes whatever is in the saved draft file at that moment, so the redo gives the
draft a NEW id: the buttons of the earlier Telegram message then refuse to act ("older draft") and can never post the old LinkedIn text. It only works on a draft that is still pending: a draft that is
publishing, published or rejected is never touched."""
from __future__ import annotations

import datetime as dt
import secrets
import sys

from . import captions, config, linkedin_story as story, tg
from .agents import linkedin_writer

NOT_PENDING = 3


def latest() -> tuple:
    files = sorted(config.DRAFTS.glob("*.json"))
    if not files:
        return None, None
    return files[-1], config.load_json(files[-1], None)


def why_not(draft) -> str:
    """'' when the newest draft can be redone, else the reason in plain words."""
    if not isinstance(draft, dict):
        return "There is no saved draft."
    if draft.get("status") != "pending":
        return f"The latest draft ({draft.get('date')}) is {draft.get('status')}, not waiting for your tap, so there is nothing to redo."
    return ""


def redo(ask=None, send=None) -> int:
    """0 = done; NOT_PENDING = nothing to redo; 2 = the writer could not produce a post that passes the checks (the draft is left exactly as it was)."""
    send = send or tg.send
    path, draft = latest()
    reason = why_not(draft)
    if reason:
        send(f"LinkedIn redo: {reason} Nothing was changed.")
        return NOT_PENDING
    fx, hist = story.facts(), story.recent()
    mode, topic = story.choose(fx, hist)
    res = linkedin_writer.run(mode, topic, fx, ask=ask, recent_posts=[h["post"] for h in hist], text_only=(draft.get("linkedin_format", "text") == "text"))
    if not res["post"]:
        send("LinkedIn redo: the writer could not produce a post that passes the checks, so I changed nothing. Your earlier message and its buttons still work.\nWhat failed:\n- " + "\n- ".join(res["problems"])[:900])
        return 2
    text = captions.finalize_linkedin(res["post"])
    draft.setdefault("linkedin_replaced", []).append(draft["posts"].get("linkedin", ""))
    draft["posts"]["linkedin"] = text
    draft["linkedin_mode"], draft["linkedin_topic"] = res["mode"], res["topic"]
    draft["id"] = f"{draft.get('date') or path.stem}-{secrets.token_hex(3)}"             # a new id: the earlier message's buttons are now refused
    draft["created_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    config.save_json(path, draft)
    send(f"[LINKEDIN, NEW POST ({res['mode']}), replaces the earlier one]\n{text}")
    send("Approve posting? Instagram and Bluesky stay exactly as in your earlier message; only the LinkedIn post changed. The Approve button on the earlier message no longer works, so use this one.",
         buttons=[{"text": "Approve", "callback_data": f"approve:{draft['id']}"}, {"text": "Reject", "callback_data": f"reject:{draft['id']}"}])
    return 0


def main() -> None:
    if "--check" in sys.argv:
        _, draft = latest()
        reason = why_not(draft)
        if reason:
            tg.send(f"LinkedIn redo: {reason} Nothing was changed.")
            raise SystemExit(NOT_PENDING)
        print("a pending draft is waiting: the LinkedIn post can be redone")
        return
    raise SystemExit(redo())


if __name__ == "__main__":
    main()
