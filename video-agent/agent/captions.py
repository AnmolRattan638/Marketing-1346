"""Word timings for captions and SFX: Groq Whisper, with an even-split estimate as fallback."""
from __future__ import annotations

import os

import requests

from .common import log

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def _transcribe(mp3, lang: str, cfg: dict) -> list[dict]:
    key = os.environ["GROQ_API_KEY"]
    with open(mp3, "rb") as fh:
        r = requests.post(
            GROQ_STT_URL,
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (mp3.name, fh, "audio/mpeg")},
            data={
                "model": cfg["captions"]["model"],
                "response_format": "verbose_json",
                "timestamp_granularities[]": "word",
                "language": lang,
            },
            timeout=120,
        )
    r.raise_for_status()
    return [
        {"text": w["word"].strip(), "start": float(w["start"]), "end": float(w["end"])}
        for w in r.json().get("words", [])
        if w.get("word", "").strip()
    ]


def _estimate(text: str, seconds: float) -> list[dict]:
    """Spread words across the clip in proportion to their length."""
    words = text.split()
    weights = [len(w) + 1 for w in words]
    total = float(sum(weights)) or 1.0
    out, t = [], 0.0
    for w, wt in zip(words, weights):
        d = seconds * wt / total
        out.append({"text": w, "start": round(t, 3), "end": round(t + d, 3)})
        t += d
    return out


def get_words(text: str, mp3, seconds: float, cfg: dict, offline: bool) -> list[dict]:
    words: list[dict] = []
    if not offline and os.environ.get("GROQ_API_KEY"):
        try:
            words = _transcribe(mp3, cfg["language"], cfg)
        except Exception as e:
            log(f"whisper failed, estimating word times: {e}")
    if not words:
        words = _estimate(text, seconds)
    for w in words:
        w["end"] = min(w["end"], seconds)
        w["start"] = round(min(w["start"], w["end"]), 3)
        w["end"] = round(w["end"], 3)
    return words
