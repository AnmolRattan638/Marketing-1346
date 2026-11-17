"""Word timings for captions and SFX: Groq Whisper, with an even-split estimate as fallback."""
from __future__ import annotations


import re
import subprocess

import requests

from . import groqkeys
from .common import log

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def _transcribe(mp3, lang: str, cfg: dict, prompt: str = "", model: str = "") -> list[dict]:
    r = None
    for key in groqkeys.rotated():
        with open(mp3, "rb") as fh:
            r = requests.post(
                GROQ_STT_URL,
                headers={"Authorization": f"Bearer {key}"},
                files={"file": (mp3.name, fh, "audio/mpeg")},
                data={
                    "model": model or cfg["captions"]["model"],
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word",
                    "language": lang,
                    **({"prompt": prompt} if prompt else {}),
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


def speech_spans(audio, seconds: float) -> list[tuple[float, float]]:
    """When the voice is actually audible (everything between the silences), from ffmpeg's silence detector. [] when it cannot be measured."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(audio), "-af", "silencedetect=noise=-35dB:d=0.25", "-f", "null", "-"], capture_output=True, text=True)
    sil, cur = [], None
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            cur = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: (-?[\d.]+)", line)
        if m and cur is not None:
            sil.append((cur, float(m.group(1))))
            cur = None
    if cur is not None:
        sil.append((cur, seconds))
    spans, pos = [], 0.0
    for a, b in sorted(sil):
        if a - pos > 0.15:
            spans.append((pos, a))
        pos = max(pos, b)
    if seconds - pos > 0.15:
        spans.append((pos, seconds))
    return spans


def fill_gaps(heard: list[dict], spans: list[tuple[float, float]], min_gap: float = 0.5) -> list[dict]:
    """Whisper sometimes drops stretches of speech (typically the first words). Wherever the voice is audible but no word was heard, add a placeholder word whose length matches
    the heard speaking rate, so align_script spreads our script over the real time span and does not squeeze the missed words in right before the first heard one."""
    if not heard or not spans:
        return heard
    letters = float(sum(len(w["text"]) + 1 for w in heard))
    active = sum(min(b, heard[-1]["end"]) - max(a, heard[0]["start"]) for a, b in spans if min(b, heard[-1]["end"]) > max(a, heard[0]["start"])) or 1.0
    rate = letters / active                                   # letters per second of audible speech, from the part Whisper did hear
    edges = [(0.0, heard[0]["start"])] + [(x["end"], y["start"]) for x, y in zip(heard, heard[1:])] + [(heard[-1]["end"], spans[-1][1])]
    ghosts = []
    for g0, g1 in edges:
        if g1 - g0 < min_gap:
            continue
        for a, b in spans:
            lo, hi = max(a, g0), min(b, g1)
            if hi - lo >= min_gap:
                ghosts.append({"text": "x" * max(2, int(rate * (hi - lo)) - 1), "start": lo, "end": hi, "ghost": True})
    return sorted(heard + ghosts, key=lambda w: w["start"])


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


LISTEN: list[str] = []          # listen-back findings of this run (read by run.py and put in the Telegram caption)


def listen_back(text: str, heard: list[dict]) -> float:
    """How much of the script the voice-over actually says: the share of script words found, in order, in what Whisper heard (1.0 = all of it).
    Catches a voice that skips, garbles or cuts off words (a wrong number, a missing CTA) before you watch the video."""
    import difflib
    norm = lambda t: re.sub(r"[^\w]+", " ", str(t).lower()).split()
    ours, said = norm(text), norm(" ".join(w.get("text", "") for w in heard))
    if not ours:
        return 1.0
    got = sum(b.size for b in difflib.SequenceMatcher(None, ours, said, autojunk=False).get_matching_blocks())
    return round(got / len(ours), 2)


def get_words(text: str, mp3, seconds: float, cfg: dict, offline: bool) -> list[dict]:
    words: list[dict] = []
    if not offline and groqkeys.keys():
        try:
            lang = cfg.get("voice_language") or cfg["language"]
            words = _transcribe(mp3, lang, cfg, prompt=text[:400])      # our own script as the hint: Whisper then keeps the opening words
            cov = listen_back(text, words)
            if cov < 0.8:
                LISTEN.append(f"voice-over check: only {cov:.0%} of the script words were heard in the audio, listen before approving")
                log(LISTEN[-1])
            if lang != cfg["language"] or cfg.get("align_script"):
                filled = fill_gaps(words, speech_spans(mp3, seconds))
                if len(filled) > len(words):
                    log(f"whisper missed {len(filled) - len(words)} stretch(es) of speech; the captions for them are timed from the audio, not guessed")
                words = align_script(text, filled)
        except Exception as e:
            log(f"whisper failed, estimating word times: {e}")
    if not words:
        words = _estimate(text, seconds)
    for w in words:
        w["end"] = min(w["end"], seconds)
        w["start"] = round(min(w["start"], w["end"]), 3)
        w["end"] = round(w["end"], 3)
    return words
