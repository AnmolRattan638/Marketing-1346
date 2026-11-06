"""Telegram: send the finished video, or an error log, to you."""
from __future__ import annotations

import os
from pathlib import Path

import requests

from .common import log

TELEGRAM_LIMIT = 50 * 1024 * 1024  # bot upload limit as I know it; check Telegram's docs


def _creds():
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log("Telegram not configured, skipping notification")
        return None
    return token, chat


def send_message(text: str) -> None:
    c = _creds()
    if not c:
        return
    requests.post(f"https://api.telegram.org/bot{c[0]}/sendMessage",
                  data={"chat_id": c[1], "text": text[:3900]}, timeout=30).raise_for_status()


def send_video(path: Path, caption: str) -> None:
    c = _creds()
    if not c:
        return
    if path.stat().st_size > TELEGRAM_LIMIT:
        send_message(f"{caption}\n\nVideo is over 50 MB, grab it from the workflow artifact.")
        return
    with open(path, "rb") as fh:
        requests.post(f"https://api.telegram.org/bot{c[0]}/sendVideo",
                      data={"chat_id": c[1], "caption": caption[:1000], "supports_streaming": "true"},
                      files={"video": fh}, timeout=300).raise_for_status()
