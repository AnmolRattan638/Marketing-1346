"""Word timings for captions and SFX: Groq Whisper, with an even-split estimate as fallback."""
from __future__ import annotations

import os

import requests

from . import groqkeys
from .common import log

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def _transcribe(mp3, lang: str, cfg: dict) -> list[dict]:
    r = None
    for key in groqkeys.rotated():
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
        if r.status_code != 429:
            break
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


def align_script(text: str, heard: list[dict]) -> list[dict]:
    """The voice speaks Devanagari but the captions must show the script's Roman Hinglish: keep the heard timings, put OUR words on them. Each script word gets the time
    that matches its share of the line (by letters) along the heard words, so captions and animation cues still land on the spoken words."""
    ours = text.split()
    if not ours or not heard:
        return heard
    marks = [(0.0, heard[0]["start"])]                       # (share of heard letters, time) at each heard word boundary
    total = float(sum(len(w["text"]) + 1 for w in heard))
    run_ = 0.0
    for w in heard:
        marks.append((run_ / total, w["start"]))
        run_ += len(w["text"]) + 1
        marks.append((run_ / total, w["end"]))
    def at(share: float) -> float:
        for (a, ta), (b, tb) in zip(marks, marks[1:]):
            if share <= b:
                return ta if b == a else ta + (tb - ta) * (share - a) / (b - a)
        return marks[-1][1]
    weights = [len(w) + 1 for w in ours]
    wsum, acc, out = float(sum(weights)), 0.0, []
    for w, wt in zip(ours, weights):
        out.append({"text": w, "start": round(at(acc / wsum), 3), "end": round(at((acc + wt) / wsum), 3)})
        acc += wt
    return out


def get_words(text: str, mp3, seconds: float, cfg: dict, offline: bool) -> list[dict]:
    words: list[dict] = []
    if not offline and groqkeys.keys():
        try:
            lang = cfg.get("voice_language") or cfg["language"]
            words = _transcribe(mp3, lang, cfg)
            if lang != cfg["language"] or cfg.get("align_script"):
                words = align_script(text, words)
        except Exception as e:
            log(f"whisper failed, estimating word times: {e}")
    if not words:
        words = _estimate(text, seconds)
    for w in words:
        w["end"] = min(w["end"], seconds)
        w["start"] = round(min(w["start"], w["end"]), 3)
        w["end"] = round(w["end"], 3)
    return words
