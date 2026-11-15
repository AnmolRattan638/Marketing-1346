"""Sarvam Bulbul text-to-speech (Indian voices, Hinglish). Needs the secret SARVAM_API_KEY.

* The voice reads a BILINGUAL script (Sarvam's own guidance): Hindi words in Devanagari, English/tech words in Latin. Romanised Hindi degrades quality. The captions keep
  the Roman Hinglish of the master script; only the voice-over text is converted (one batch model call, cached).
* Bulbul v4-flash has no emotion knob; expressiveness comes from the persona and from pace/pitch/loudness, which are set per beat from the script's `emotion`.
* Each scene gets a short pause after it, so beats breathe instead of running together.
"""
from __future__ import annotations

import base64
import json
import os
import re

import requests

from .common import log, run

URL = "https://api.sarvam.ai/text-to-speech"
# (pace, pitch, loudness) per emotion: small moves, because big ones make Bulbul sound synthetic
EMOTION = {
    "curious": (1.00, 0.06, 1.00), "empathetic": (0.92, -0.06, 0.95), "urgent": (1.08, 0.04, 1.10),
    "calm": (0.98, 0.00, 1.00), "excited": (1.10, 0.10, 1.15), "warm": (0.95, -0.02, 1.00),
}
PAUSE_AFTER = {"pain": 0.45, "poke": 0.40, "fix": 0.35, "payoff": 0.40, "recap": 0.30, "cta": 0.0}      # seconds of silence after the beat
PREP: dict[str, str] = {}
_OK: list = []            # the model/speaker this account accepted, tried first from then on
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
# English words the Hindi voice mangles when they are left in Latin letters (it spells ALL-CAPS words letter by letter and says "whatsaap"): they are written the way an Indian speaker
# says them, in Devanagari, by code, so it does not depend on the model's conversion. Add words here when one sounds wrong.
LEXICON = {
    "bot": "बॉट", "bots": "बॉट्स", "chatbot": "चैटबॉट", "step": "स्टेप", "steps": "स्टेप्स", "whatsapp": "व्हाट्सऐप", "lead": "लीड", "leads": "लीड्स",
    "website": "वेबसाइट", "comment": "कमेंट", "message": "मैसेज", "reply": "रिप्लाई", "customer": "कस्टमर", "customers": "कस्टमर्स", "setup": "सेटअप",
    "free": "फ्री", "demo": "डेमो", "link": "लिंक", "dm": "डीएम", "instagram": "इंस्टाग्राम", "google": "गूगल", "online": "ऑनलाइन", "business": "बिज़नेस",
    "automation": "ऑटोमेशन", "ai": "ए आई", "minute": "मिनट", "minutes": "मिनट", "booking": "बुकिंग", "bookings": "बुकिंग्स", "follow": "फॉलो", "follow-up": "फॉलो-अप",
    "sales": "सेल्स", "app": "ऐप", "call": "कॉल", "number": "नंबर", "offer": "ऑफर",
}
_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def speakable(text: str) -> str:
    """Swap the lexicon's English words (any case) for their Devanagari spelling, so the voice says them as whole words."""
    return _LATIN_WORD.sub(lambda m: LEXICON.get(m.group(0).lower().rstrip("'"), m.group(0)), text)


def prepare(texts: list[str], ask) -> None:
    """Convert Roman Hinglish lines to the bilingual script in ONE call and cache them. `ask(prompt) -> dict` returns the model's parsed JSON. On any failure
    the lines are sent as they are (Roman), which Bulbul still reads, just less well."""
    todo = [t for t in dict.fromkeys(texts) if t not in PREP]
    if not todo:
        return
    prompt = ("Rewrite each Roman-letter Hinglish line for a text-to-speech engine: write the Hindi words in Devanagari and keep other English words (brand names, tech words) in Latin letters, written in normal lower case (never ALL CAPS, which the voice spells out). Keep the meaning, order, numbers, punctuation and the casual spoken tone; do not translate English words into Hindi "
              "and do not add or drop words.\nReturn JSON {\"lines\": [...]} with exactly " + str(len(todo)) + " strings in the same order.\n" + json.dumps(todo, ensure_ascii=False))
    try:
        out = ask(prompt).get("lines") or []
        if len(out) != len(todo):
            raise ValueError(f"got {len(out)} lines for {len(todo)}")
        for src, dst in zip(todo, out):
            PREP[src] = speakable(dst if isinstance(dst, str) and dst.strip() else src)
    except Exception as e:
        log(f"sarvam: bilingual conversion skipped ({str(e)[:120]}), speaking the Roman text")
        for t in todo:
            PREP[t] = speakable(t)


def _request(key: str, text: str, model: str, speaker: str, params: tuple[float, float, float]) -> bytes | None:
    pace, pitch, loud = params
    body = {"text": text, "language_code": "hi-IN", "model": model, "speaker": speaker, "pace": pace, "speech_sample_rate": 24000, "output_audio_codec": "wav"}
    if model == "bulbul:v4-flash":
        body.update({"pitch": pitch, "loudness": loud})              # v3 has no pitch/loudness; v4-flash has no temperature
    r = requests.post(URL, headers={"api-subscription-key": key, "Content-Type": "application/json"}, json=body, timeout=90)
    if r.status_code in (400, 422):
        log(f"sarvam: {model}/{speaker} rejected ({r.status_code}): {r.text[:160]}")
        return None
    if r.status_code == 429:
        raise RuntimeError("Sarvam rate limit (429)")
    if r.status_code in (401, 403):
        raise RuntimeError(f"Sarvam key refused ({r.status_code}): check SARVAM_API_KEY and the credit balance")
    r.raise_for_status()
    audios = r.json().get("audios") or []
    return base64.b64decode(audios[0]) if audios else None


_SENT = re.compile(r"(?<=[.?!।])\s+")


def sentence_emotions(sentences: list[str], base: str | None, beat: str | None) -> list[str]:
    """One mood per sentence, so a scene is not read in one flat tone: the scene's mood opens it, a question turns curious, an exclamation excited, the sentence that
    carries the reason (after kyunki/matlab/isliye) slows to calm, and the last sentence of a pain/poke beat softens to empathetic."""
    base = base if base in EMOTION else "calm"
    out = []
    for i, t in enumerate(sentences):
        t = t.strip()
        if t.endswith("?"):
            e = "curious"
        elif t.endswith("!"):
            e = "excited"
        elif re.search(r"\b(kyunki|kyuki|isliye|matlab|yaani|taaki|क्योंकि|इसलिए|मतलब|ताकि)\b", t, re.I):
            e = "calm"
        elif i == len(sentences) - 1 and len(sentences) > 1 and beat in ("pain", "poke"):
            e = "empathetic"
        else:
            e = base
        out.append(e)
    return out


def synth(text: str, mp3, scfg: dict, emotion: str | None = None, beat: str | None = None) -> None:
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        raise RuntimeError("SARVAM_API_KEY is not set")
    spoken = PREP.get(text) or speakable(text)
    sentences = [x for x in _SENT.split(spoken.strip()) if x.strip()] or [spoken]
    moods = sentence_emotions(sentences, emotion, beat)
    cands = scfg.get("candidates") or [{"model": scfg.get("model", "bulbul:v4-flash"), "speaker": scfg.get("speaker", "aayan_hi_conversational")}]
    wavs = []
    for i, (sent, mood) in enumerate(zip(sentences, moods)):          # each sentence is its own take with its own pace/pitch/loudness
        wav_bytes = None
        for cand in ([*_OK] + [c for c in cands if c not in _OK]):
            wav_bytes = _request(key, sent, cand["model"], cand["speaker"], EMOTION[mood])      # first model/speaker the account accepts wins
            if wav_bytes:
                _OK[:] = [cand]
                break
        if not wav_bytes:
            raise RuntimeError("Sarvam returned no audio for any configured speaker")
        w = mp3.with_suffix(f".s{i}.wav")
        w.write_bytes(wav_bytes)
        wavs.append(w)
    gap = float(scfg.get("sentence_gap", 0.22))                       # a breath between sentences
    pause = PAUSE_AFTER.get(beat or "", 0.3) * float(scfg.get("pause_scale", 1.0))
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for w in wavs:
        cmd += ["-i", w]
    parts = [f"[{i}:a]apad=pad_dur={(gap if i < len(wavs) - 1 else pause):.2f}[a{i}]" for i in range(len(wavs))]
    chain = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(wavs))) + f"concat=n={len(wavs)}:v=0:a=1[out]"
    run(cmd + ["-filter_complex", chain, "-map", "[out]", "-ac", "1", "-b:a", "128k", mp3])
    for w in wavs:
        w.unlink()
