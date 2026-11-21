"""Everything done to a script line BEFORE the voice reads it, so the voice says what a person would say.

* short forms are spoken in full (sec -> second, min -> minute, vs -> versus; the list is agent/shortforms.json),
* numbers and symbols are made speakable (9:16 -> nine by sixteen, 50% -> 50 percent, Rs 5k -> 5 thousand rupees, 3x -> 3 times, & -> and),
* signs the voice must never read out (* # _ ~ | brackets, quotes, arrows, emoji, slashes) are removed or turned into a pause,
* every sentence ends with a full stop / question mark / exclamation mark so the voice knows where to stop and breathe,
* a long sentence is cut at its commas into short takes, so there is a breath where a person would take one.
The captions keep the original script words; only the voice text goes through here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

NUM = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
       14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty", 21: "twenty one"}
END = ".?!।"


def _load() -> dict[str, str]:
    try:
        d = json.loads(Path(__file__).with_name("shortforms.json").read_text(encoding="utf-8"))
        return {k.lower(): v for k, v in d.items() if not k.startswith("_")}
    except Exception:
        return {}


SHORT = _load()


def _word(n: int) -> str:
    return NUM.get(n, str(n))


UNTRANSLATE = {"ग्राहकों": "कस्टमर्स", "ग्राहक": "कस्टमर", "उपभोक्ताओं": "कस्टमर्स", "उपभोक्ता": "कस्टमर"}   # the voice says the English word the script means
ROMAN_BACK = [(re.compile(r"\bgrahak(?:on|o)?\b", re.I), "customers")]


def untranslate(text: str) -> str:
    for k in sorted(UNTRANSLATE, key=len, reverse=True):
        text = text.replace(k, UNTRANSLATE[k])
    for rx, rep in ROMAN_BACK:
        text = rx.sub(rep, text)
    return text


def expand(text: str) -> str:
    """Short forms, ratios, percentages, money, multipliers: all as the words a person says."""
    t = untranslate(text)
    t = re.sub(r"(?<!\d)(\d{1,2}):(\d{1,2})(?!\d)(?!\s*(?:am|pm|baje|बजे))", lambda m: f"{_word(int(m[1]))} by {_word(int(m[2]))}" if int(m[1]) <= 21 and int(m[2]) <= 21 else m[0], t, flags=re.I)  # 9:16 is a ratio, never a clock
    t = re.sub(r"(\d)\s*%", r"\1 percent", t)
    t = re.sub(r"(?:₹|\bRs\.?\s*|\bINR\s*)\s*(\d[\d,\.]*)\s*(k|K|L|l|lakh|cr|Cr)?\b", lambda m: f"{m[1]} {({'k': 'thousand', 'l': 'lakh', 'lakh': 'lakh', 'cr': 'crore'}).get((m[2] or '').lower(), '')} rupees".replace("  ", " "), t)
    t = re.sub(r"(\d)\s*[kK]\b", r"\1 thousand", t)
    t = re.sub(r"(\d)\s*[xX]\b", r"\1 times", t)
    t = t.replace("&", " and ")
    t = re.sub(r"\b24\s*/\s*7\b", SHORT.get("24/7", "twenty four seven"), t)
    for k in sorted((k for k in SHORT if "/" in k and k != "24/7"), key=len, reverse=True):
        t = re.sub(re.escape(k), SHORT[k], t, flags=re.I)
    t = re.sub(r"\b([A-Za-z]{1,6})\.?(?=\W|$)", lambda m: SHORT.get(m[1].lower(), m[0]) if m[1].lower() in SHORT and "/" not in m[1] else m[0], t)
    return t


def strip_signs(text: str) -> str:
    """Remove what the voice would read out loud or stumble on. A dash, colon, semicolon or slash becomes a comma pause; an ellipsis a longer pause."""
    t = text
    t = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️‍]", " ", t)           # emoji
    t = re.sub(r"[→←↑↓➜➡⇒►▶•·●◆★☆✓✔✗✘]", ", ", t)
    t = re.sub(r"[*_#~^|\\<>\[\]{}\"“”‘’`]", " ", t)
    t = re.sub(r"\(([^)]*)\)", r", \1, ", t)
    t = t.replace("…", "...")
    t = re.sub(r"\.{2,}", " … ", t)                                                       # kept as a marker: pause_marker() gives it a longer gap
    t = re.sub(r"\s[-–—]+\s|[–—]", ", ", t)
    t = re.sub(r"(?<!\d):(?!\d)|;", ",", t)
    t = re.sub(r"(?<=[A-Za-zऀ-ॿ])/(?=[A-Za-zऀ-ॿ])", " ya ", t)
    t = re.sub(r"\s*,(\s*,)+", ",", t)
    t = re.sub(r"\s+([,.?!।])", r"\1", t)
    return re.sub(r"\s+", " ", t).strip(" ,")


def punctuate(text: str, question: bool | None = None) -> str:
    """Make sure the line ends in a terminal sign, and that a sentence boundary the writer forgot (a capital after a lowercase word with no sign) gets a full stop."""
    t = text.strip()
    if not t:
        return t
    if t[-1] not in END + "…":
        t += "?" if (question if question is not None else _looks_question(t)) else "."
    return t


QUESTION_START = re.compile(r"^(kya|kyun|kyu|kaise|kab|kaun|kitn[aeiy]|kahan|kidhar|क्या|क्यों|कैसे|कब|कौन|कितने|कितना|कितनी|कहाँ)\b", re.I)
QUESTION_END = re.compile(r"\b(hai|hain|hota|hoti|hote|tha|thi|the|ho|kya|na|nahi)\s*$", re.I)


def _looks_question(t: str) -> bool:
    return bool(QUESTION_START.search(t.strip()))


def sentences(text: str) -> list[tuple[str, float, int]]:
    """Cut the cleaned line into takes: (text, silence after it in seconds). Sentence ends get a real stop (? a little more, ... most); a sentence of more than ~11 words is cut at a
    comma into shorter takes with a small breath between them. Each take also carries the index of the sentence it belongs to (one mood per sentence)."""
    cleaned = strip_signs(expand(text))
    head, tail = re.split(r"(?<=[.?!।…])\s+", cleaned)[:-1], re.split(r"(?<=[.?!।…])\s+", cleaned)[-1]
    cleaned = " ".join([*head, punctuate(tail)])                  # only the LAST sentence can be missing its sign here; its own words decide if it is a question
    out: list[tuple[str, float, int]] = []
    for si, s in enumerate(x for x in re.split(r"(?<=[.?!।…])\s+", cleaned) if x.strip() and x.strip() not in tuple(END + "…")):
        s = s.strip()
        gap = {"?": 0.34, "!": 0.28, "…": 0.55}.get(s[-1], 0.30)
        if s.endswith("…"):
            s = s[:-1].rstrip(" ,") + "..."
        parts = [p.strip() for p in re.split(r"(?<=,)\s+", s)]
        takes, buf = [], ""
        for p in parts:                                   # glue comma pieces back together until a take is ~5+ words, so a take is never a single stub
            buf = f"{buf} {p}".strip() if buf else p
            if len(buf.split()) >= 5:
                takes.append(buf)
                buf = ""
        if buf:
            if takes and len(buf.split()) < 3:
                takes[-1] = f"{takes[-1]} {buf}"
            else:
                takes.append(buf)
        if len(s.split()) <= 11 or len(takes) < 2:
            takes = [s]
        for k, tk in enumerate(takes):
            tk = tk.rstrip(",") if k < len(takes) - 1 else tk
            if k < len(takes) - 1 and tk[-1] not in END:
                tk += ","
            out.append((tk, 0.14 if k < len(takes) - 1 else gap, si))
    return out or [(punctuate(cleaned), 0.0, 0)]


def clean(text: str) -> str:
    """The voice text for a line as ONE string (expanded, signs removed, punctuated). Used before the Devanagari conversion."""
    return " ".join(s for s, _, _ in sentences(text))
