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
import time
from pathlib import Path

import requests

from . import speech_text

from .common import log, run

URL = "https://api.sarvam.ai/text-to-speech"
# (pace, pitch, loudness) per emotion: small moves, because big ones make Bulbul sound synthetic
EMOTION = {
    "curious": (1.00, 0.06, 1.00), "empathetic": (0.92, -0.06, 0.95), "urgent": (1.08, 0.04, 1.10),
    "calm": (0.98, 0.00, 1.00), "excited": (1.10, 0.10, 1.15), "warm": (0.95, -0.02, 1.00),
}
PAUSE_AFTER = {"pain": 0.45, "poke": 0.40, "fix": 0.35, "payoff": 0.40, "recap": 0.30, "cta": 0.0}      # seconds of silence after the beat
PREP: dict[str, str] = {}
MOODS: dict[str, list[str]] = {}     # per line: one mood per sentence, chosen by the model that converts the text (curious, excited, ...)
_OK: list = []            # the model/speaker this account accepted, tried first from then on
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
def _load_lexicon() -> dict[str, str]:
    """The pronunciation dictionary: agent/pronunciations.json maps an English word (lower case) to the Devanagari spelling the voice reads correctly. Edit that file to fix a word."""
    try:
        d = json.loads((Path(__file__).with_name("pronunciations.json")).read_text(encoding="utf-8"))
        return {str(k).lower(): str(v) for k, v in d.items()}
    except Exception as e:
        log(f"sarvam: pronunciation dictionary not loaded ({e})")
        return {}


LEXICON = _load_lexicon()
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
    cleaned = [speech_text.clean(t) for t in todo]                      # short forms, 9:16, signs and full stops are fixed BEFORE the model sees the line
    prompt = ("Rewrite each Roman-letter Hinglish line for a Hindi text-to-speech engine so EVERY word is written in Devanagari, spelled the way an Indian speaker pronounces it: Hindi words "
              "in Devanagari, and English words transliterated phonetically into Devanagari (site -> साइट, mismatched -> मिसमैच्ड, WhatsApp -> व्हाट्सऐप, checklist -> चेकलिस्ट). "
              "NEVER translate an English word into Hindi: customer/customers stay कस्टमर/कस्टमर्स (not ग्राहक), second stays सेकंड, website stays वेबसाइट. "
              "Acronyms are spelled letter by letter in Devanagari (CRM -> सी आर एम). Words already in Devanagari stay as they are. Keep the meaning, order, numbers and the casual "
              "spoken tone; do not add or drop words. KEEP every punctuation mark: each sentence must end with . or ? or ! (add the right one if missing) and keep commas where a speaker "
              "breathes. Never write symbols, quotes, brackets, emoji or the words for them.\n"
              "For every line also give one MOOD per sentence, how a person would say it, from: curious, excited, empathetic, urgent, calm, warm "
              "(a question that teases an answer = curious, a big benefit or reveal = excited, a pain point = empathetic, a deadline or loss = urgent, an explanation = calm, a friendly ask = warm).\n"
              "Return JSON {\"lines\": [{\"text\": \"...\", \"moods\": [\"curious\", ...]}]} with exactly " + str(len(todo)) + " items in the same order.\n"
              + json.dumps([speakable(t) for t in cleaned], ensure_ascii=False))
    try:
        out = ask(prompt).get("lines") or []
        if len(out) != len(todo):
            raise ValueError(f"got {len(out)} lines for {len(todo)}")
        for src, dst in zip(todo, out):
            text, moods = (dst.get("text"), dst.get("moods")) if isinstance(dst, dict) else (dst, None)
            PREP[src] = speakable(speech_text.untranslate(text if isinstance(text, str) and text.strip() else speech_text.clean(src)))
            if isinstance(moods, list):
                MOODS[src] = [str(m).lower() for m in moods]
            left = sorted({w.lower() for w in _LATIN_WORD.findall(PREP[src])})
            if left:
                log(f"sarvam: still in Latin letters (add to pronunciations.json if one sounds wrong): {', '.join(left)}")
    except Exception as e:
        log(f"sarvam: bilingual conversion skipped ({str(e)[:120]}), speaking the cleaned Roman text")
        for t, c in zip(todo, cleaned):
            PREP[t] = speakable(c)


def _request(key: str, text: str, model: str, speaker: str, params: tuple[float, float, float]) -> bytes | None:
    pace, pitch, loud = params
    body = {"text": text, "language_code": "hi-IN", "model": model, "speaker": speaker, "pace": pace, "speech_sample_rate": 24000, "output_audio_codec": "wav"}
    if model == "bulbul:v4-flash":
        body.update({"pitch": pitch, "loudness": loud})              # v3 has no pitch/loudness; v4-flash has no temperature
    r = None
    for attempt in range(5):                       # a busy or rate-limited moment is waited out; the reel must never switch to another voice half way
        try:
            r = requests.post(URL, headers={"api-subscription-key": key, "Content-Type": "application/json"}, json=body, timeout=90)
        except requests.RequestException as e:
            log(f"sarvam: network error ({str(e)[:80]}), retry {attempt + 1}/5")
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            wait = min(30.0, float(r.headers.get("Retry-After") or 3 * (attempt + 1)))
            log(f"sarvam: {r.status_code}, waiting {wait:.0f}s (retry {attempt + 1}/5)")
            time.sleep(wait)
            continue
        break
    if r is None:
        raise RuntimeError("Sarvam unreachable after 5 tries")
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
    spoken = PREP.get(text) or speakable(speech_text.clean(text))
    takes = speech_text.sentences(spoken)                              # [(take, silence after, sentence index)]
    n_sent = takes[-1][2] + 1
    heard = MOODS.get(text) or []
    if len(heard) == n_sent and all(m in EMOTION for m in heard):
        sent_moods = heard                                             # the mood the converting model gave each sentence
    else:
        whole = [" ".join(t for t, _, si in takes if si == k) for k in range(n_sent)]
        sent_moods = sentence_emotions(whole, emotion, beat)
    cands = scfg.get("candidates") or [{"model": scfg.get("model", "bulbul:v4-flash"), "speaker": scfg.get("speaker", "aayan_hi_conversational")}]
    wavs = []
    for i, (sent, _, si) in enumerate(takes):                          # each take is its own request with its own pace/pitch/loudness
        mood = sent_moods[si]
        wav_bytes = None
        for cand in ([*_OK] if _OK else cands):                       # once a speaker has been accepted it is the ONLY one used for the whole reel
            wav_bytes = _request(key, sent, cand["model"], cand["speaker"], EMOTION[mood])      # first model/speaker the account accepts wins
            if wav_bytes:
                _OK[:] = [cand]
                break
        if not wav_bytes:
            raise RuntimeError("Sarvam returned no audio for any configured speaker")
        w = mp3.with_suffix(f".s{i}.wav")
        w.write_bytes(wav_bytes)
        wavs.append(w)
    scale = float(scfg.get("gap_scale", 1.0))                         # every pause comes from the punctuation: , short   . normal   ? a little more   ... long
    pause = PAUSE_AFTER.get(beat or "", 0.3) * float(scfg.get("pause_scale", 1.0))
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for w in wavs:
        cmd += ["-i", w]
    trim = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse"   # the engine's own dead air is cut so the pauses are exactly the ones above
    parts = [f"[{i}:a]{trim},apad=pad_dur={(takes[i][1] * scale if i < len(wavs) - 1 else pause):.2f}[a{i}]" for i in range(len(wavs))]
    chain = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(wavs))) + f"concat=n={len(wavs)}:v=0:a=1[out]"
    run(cmd + ["-filter_complex", chain, "-map", "[out]", "-ac", "1", "-b:a", "128k", mp3])
    for w in wavs:
        w.unlink()
