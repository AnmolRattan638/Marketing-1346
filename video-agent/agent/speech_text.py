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
from dataclasses import dataclass
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


UNTRANSLATE = {"दुकानदारों": "बिज़नेस ओनर्स", "दुकानदार": "बिज़नेस ओनर", "दुकानों": "बिज़नेस", "दुकान": "बिज़नेस", "ग्राहकों": "कस्टमर्स", "ग्राहक": "कस्टमर", "उपभोक्ताओं": "कस्टमर्स", "उपभोक्ता": "कस्टमर"}   # the voice says the English word the script means
NOM = {"aapki": "aapka", "tumhari": "tumhara", "hamari": "hamara", "meri": "mera", "apni": "apna", "uski": "uska", "unki": "unka", "iski": "iska"}
OBL = {"aapki": "aapke", "tumhari": "tumhare", "hamari": "hamare", "meri": "mere", "apni": "apne", "uski": "uske", "unki": "unke", "iski": "iske"}
ROMAN_BACK = [
    (re.compile(r"\b(aapki|tumhari|hamari|meri|apni|uski|unki|iski)\s+(?:dukaan|dukan)(?:on|en)?\b(\s+(?:ki|ke|ka|ko|par|pe|mein|me|se|tak)\b)?", re.I), lambda m: (OBL if m[2] else NOM)[m[1].lower()] + " business" + (m[2] or "")),
    (re.compile(r"\b(?:dukaan|dukan|dukaandaar|dukandar)\s+(?:wale|walon|walo|waale)\b", re.I), "business owners"),
    (re.compile(r"\b(?:dukaandaar|dukandar|dukaandar)(?:on)?\b", re.I), "business owner"),
    (re.compile(r"\b(?:dusri|doosri)\s+(?:dukaan|dukan)\b", re.I), "dusra business"),
    (re.compile(r"\b(?:dukaan|dukan)(?:on|en)?\b", re.I), "business"),
    (re.compile(r"\bgrahak(?:on|o)?\b", re.I), "customers")]


FEM_VERBS = {"karti": "karta", "hoti": "hota", "jaati": "jaata", "jati": "jata", "chalti": "chalta", "rukti": "rukta", "lagti": "lagta", "milti": "milta", "dikhti": "dikhta",
             "aati": "aata", "banti": "banta", "rehti": "rehta", "padti": "padta", "sakti": "sakta", "paati": "paata", "deti": "deta", "leti": "leta", "rahi": "raha", "thi": "tha",
             "gayi": "gaya", "gai": "gaya", "hui": "hua", "chali": "chala", "ruki": "ruka", "mili": "mila", "bani": "bana", "kho": "kho", "dikhi": "dikha", "lagi": "laga", "padi": "pada"}
FEM_NOUNS = re.compile(r"\b(website|site|page|call|calls|enquiry|enquiries|booking|bookings|speed|sales|reply|replies|baat|cheez|problem|salary|team|ad|ads|post|posts|search|ranking|image|photo|list|app|visibility|query|queries|report|service|kami|galti|wajah|jagah|chat|dukaan)\b", re.I)
CLAUSE = re.compile(r"([,;.!?:\u2026]|\s(?:aur|lekin|par|kyunki|toh|isliye|jab|agar|ki)\s)", re.I)
SUBJECT = re.compile(r"\b(?:dukaan|dukan)(?!\s+(?:ki|ke|ka|ko|se|mein|me|par|pe|tak|wale|walon)\b)(?!on|en)", re.I)


def _agree(clause):
    """A clause whose SUBJECT was 'dukaan' (feminine) but is now 'business' (masculine): karti -> karta, hoti -> hota, gayi -> gaya. Left alone when another feminine noun
    (website, call, enquiry...) is in the clause, because then the verb belongs to that noun."""
    if not SUBJECT.search(clause) or re.search(r"\b(?:dusri|doosri)\s+(?:dukaan|dukan)", clause, re.I) or FEM_NOUNS.search(SUBJECT.sub("", clause)):
        return clause
    return re.sub(r"\b(" + "|".join(k for k in FEM_VERBS if k != "kho") + r")\b", lambda m: FEM_VERBS[m.group(1).lower()], clause, flags=re.I)


def agree_business(text):
    parts = CLAUSE.split(str(text or ""))
    return "".join(_agree(p) if i % 2 == 0 else p for i, p in enumerate(parts))


def untranslate(text: str) -> str:
    text = agree_business(text)
    for k in sorted(UNTRANSLATE, key=len, reverse=True):
        text = text.replace(k, UNTRANSLATE[k])
    for rx, rep in ROMAN_BACK:
        text = rx.sub(rep, text)
    return text


# --- how a person SAYS things the script writes with symbols or glued letters (the pronunciation list; words live in shortforms.json, Devanagari spellings in pronunciations.json) ---
BY_24_7 = "twenty four by seven"          # 24x7, 24X7, 24×7, 24*7, 24 x 7, 24-7, 24by7, 24/7  (Indian speech: "twenty four by seven")
_ORD = "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth".split()
ORDINAL = {i + 1: w for i, w in enumerate(_ORD)}
ORDINAL.update({20 + i: f"twenty {_ORD[i - 1]}" for i in range(1, 10)})
ORDINAL.update({30: "thirtieth", 31: "thirty first"})
UNITS = {"km": "kilometer", "kmph": "kilometers per hour", "kg": "kilogram", "gm": "gram", "gms": "grams", "ml": "milliliter", "cm": "centimeter", "mm": "millimeter",
         "gb": "gigabyte", "mb": "megabyte", "kb": "kilobyte", "tb": "terabyte"}
MONEY_UNIT = {"k": "thousand", "l": "lakh", "lakh": "lakh", "lac": "lakh", "lacs": "lakh", "cr": "crore", "crore": "crore"}
MONEY = re.compile(r"(?:₹|\bRs\.?\s*|\bINR\s*)\s*(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*(k|l|lakh|lacs?|cr|crore)\b)?(?:\s*/-)?", re.I)   # the space AFTER the amount is never eaten
TITLES = {"dr", "mr", "mrs", "prof"}                                                   # "Dr. Sharma": the dot belongs to the title, not a sentence end
VIDEO_WORDS = "video|videos|resolution|quality|ultra|hd|display|screen|camera|footage|reel|reels|monitor|tv|content|clip|clips"


def _phone(m: re.Match) -> str:
    pre = "" if not m[1] else ("plus 9 1, " if "+" in m[1] else "9 1, ")
    return f"{pre}{' '.join(m[2])}, {' '.join(m[3])}"                                      # digit by digit, a breath in the middle: 9 8 7 6 5, 4 3 2 1 0


def _money(m: re.Match) -> str:
    return f"{m[1]} {MONEY_UNIT.get((m[2] or '').lower(), '')} rupees".replace("  ", " ")


def _symbols(t: str) -> str:
    """Symbols and glued forms the voice would misread: 24x7, 30sec, 24hrs, 1st, 4K, 5G, #1, 10+, 10-15, 5kg, phone numbers, www/.com/@, e.g., 3,199."""
    # web addresses and handles
    t = re.sub(r"\bhttps?://", "", t, flags=re.I)
    t = re.sub(r"\bwww\.", "W W W dot ", t, flags=re.I)
    t = re.sub(r"(?<=[A-Za-z0-9._])@(?=[A-Za-z0-9])", " at the rate ", t)                  # an e-mail is read the Indian way: "name at the rate site dot com"
    t = re.sub(r"@(?=[A-Za-z0-9_])", "at ", t)                                              # a handle: "@arrdesigns" -> "at arrdesigns"
    t = re.sub(r"(?<=[A-Za-z0-9])\.(co\.in|com|in|org|net|io|ai|app|dev|me)\b(/?)", lambda m: " dot " + m[1].replace(".", " dot ") + (" slash " if m[2] else ""), t, flags=re.I)
    # 24x7 and its spellings (never a date such as 24/7/2026)
    spoken = SHORT.get("24/7", BY_24_7)
    sep = r"\s*(?:[xX×*/]|by|-)\s*"
    t = re.sub(rf"\b24{sep}7{sep}365\b", f"{spoken} by three sixty five", t, flags=re.I)
    t = re.sub(rf"\b24{sep}7\b(?![/\-]\d)", spoken, t, flags=re.I)
    # phone numbers, digit by digit
    t = re.sub(r"(?<![\d.,₹])(\+?91[\s-]?)?([6-9]\d{4})[\s-]?(\d{5})(?!\d)", _phone, t)
    # digits glued to a unit: 30sec, 24hrs, 2mins, 5kg, 2GB
    t = re.sub(r"(?<=\d)(?=(?:secs?|mins?|hrs?|yrs?)\b)", " ", t, flags=re.I)
    t = re.sub(r"(?<=\d)\s*(kmph|km|kg|gms?|ml|cm|mm|gb|mb|kb|tb)\b", lambda m: " " + UNITS[m[1].lower()], t, flags=re.I)
    # 1st 2nd 3rd 21st
    t = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", lambda m: ORDINAL.get(int(m[1]), m[0]), t, flags=re.I)
    # 4K video / in 4K, 5G, 3D (K and G are letters here, not "thousand")
    t = re.sub(rf"\b([248])[kK]\b(?=\s+(?:{VIDEO_WORDS})\b)", lambda m: f"{NUM[int(m[1])]} K", t)
    t = re.sub(r"\b(in|at)\s+([248])K\b", lambda m: f"{m[1]} {NUM[int(m[2])]} K", t)
    t = re.sub(r"\b([2345])G\b", lambda m: f"{NUM[int(m[1])]} G", t)
    t = re.sub(r"\b([23])D\b", lambda m: f"{NUM[int(m[1])]} D", t)
    # numbers
    t = re.sub(r"(?<![\d,])\d{1,3}(?:,\d{2,3})*,\d{3}(?!\d)(?!,\d)", lambda m: m[0].replace(",", ""), t)   # 3,199 and 1,00,000 -> 3199 and 100000
    t = re.sub(r"(?<![\d\-/.:])(\d{1,4})\s*[-–]\s*(\d{1,4})(?!\d)(?![\-/:]\d)(?!\.\d)", r"\1 to \2", t)     # 10-15 -> 10 to 15 (dates are left alone)
    t = re.sub(r"#\s*(?=\d)", "number ", t)                                                 # #1 -> number 1
    t = re.sub(r"(?<=[\d%])\+(?![\w+])", " plus", t)                                        # 10+ -> 10 plus
    t = re.sub(r"\$\s*(\d+(?:,\d+)*(?:\.\d+)?)", r"\1 dollars", t)
    t = re.sub(r"\be\.\s?g\b\.?", "for example", t, flags=re.I)
    t = re.sub(r"\bi\.\s?e\b\.?", "that is", t, flags=re.I)
    t = re.sub(r"\b([ap])\.m\b\.?", lambda m: m[1].lower() + "m", t, flags=re.I)         # 10 a.m. -> 10 am
    t = re.sub(r"\b(?:[A-Za-z]\.){2,}(?:[A-Za-z]\b)?", _dotted, t)                         # S.E.O. -> SEO (the voice used to stop at every dot)
    return t


def _dotted(m: re.Match) -> str:
    letters = m[0].replace(".", "")
    if not m[0].endswith("."):
        return letters
    nxt = m.string[m.end():].lstrip()[:1]
    return letters + ("" if nxt.islower() or nxt.isdigit() or nxt in ",;:)" else ".")        # the last dot stays only when it ends a sentence


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}


def _below100(n: int) -> str:
    if n in NUM:
        return NUM[n]
    return TENS[n // 10] + (" " + NUM[n % 10] if n % 10 else "")


def _fmt_date(d_: str, mo_: str, y: str, orig: str) -> str:
    """12.05.2026 / 12/05/2026 / 12-05-2026 / 22.11 -> "twelve May twenty twenty six" / "twenty two November" (never read as a decimal or a range)."""
    d, mo = int(d_), int(mo_)
    if not (1 <= d <= 31 and 1 <= mo <= 12):
        return orig
    out = f"{_below100(d)} {MONTHS[mo - 1]}"
    if y:
        yi = int(y) if len(y) == 4 else 2000 + int(y)
        out += f" twenty {_below100(yi - 2000)}" if 2010 <= yi <= 2099 else f" {yi}"
    return out


def _decimal(m: re.Match) -> str:
    whole = int(m[1])
    return f"{_word(whole)} point {' '.join(NUM[int(d)] for d in m[2])}"                    # digits after the point are read one by one, in English words


def _short(m: re.Match) -> str:
    """One word of shortforms.json. A full stop after it is dropped only when it belongs to the abbreviation (Dr. Sharma, approx. 5), kept when it ends the sentence (30 sec. Phir)."""
    k = m[1].lower()
    word = SHORT.get(k)
    if word is None and k.endswith("s") and "/" not in k:
        base = SHORT.get(k[:-1])
        if base and re.fullmatch(r"(?:[A-Za-z0-9] )+[A-Za-z0-9]", base):               # UPIs, CTAs, KPIs: letter by letter, then 's
            word = base + "'s"
    if word is None or "/" in k:
        return m[0]
    keep = ""
    if m[2]:
        nxt = m.string[m.end():].lstrip()[:1]
        if k not in TITLES and not (nxt.islower() or nxt.isdigit() or nxt in ",;:)"):
            keep = "."
    return word + keep


def expand(text: str) -> str:
    """Short forms, ratios, percentages, money, multipliers, 24x7, phone numbers, web addresses: all as the words a person says."""
    t = untranslate(text)
    t = _symbols(t)
    t = re.sub(r"(?<!\d)(\d{1,2}):(\d{1,2})(?!\d)(?!\s*(?:am|pm|baje|बजे))", lambda m: f"{_word(int(m[1]))} by {_word(int(m[2]))}" if int(m[1]) <= 21 and int(m[2]) <= 21 else m[0], t, flags=re.I)  # 9:16 is a ratio, never a clock
    t = re.sub(r"(\d)\s*%", r"\1 percent", t)
    t = MONEY.sub(_money, t)
    t = re.sub(r"\b(rupees)\s*[-–]\s*(?=\d)", r"\1 to ", t)                                  # ₹999-₹3199 -> 999 rupees to 3199 rupees
    t = re.sub(r"(?<![\w₹])(\d+(?:,\d+)*)\s*/-", r"\1 rupees", t)                           # 999/- -> 999 rupees
    t = re.sub(r"(?<=[A-Za-z0-9])\s*/\s*(?=(?:month|mo|year|yr|day|week|hour|hr|person|piece|night|visit|click|lead|sqft|kg|km|litre|liter)\b)", " per ", t, flags=re.I)   # rupees/month -> rupees per month
    t = re.sub(r"(\d)\s*[kK]\b", r"\1 thousand", t)
    t = re.sub(r"(\d)\s*[xX]\b", r"\1 times", t)
    t = t.replace("&", " and ")
    for k in sorted((k for k in SHORT if "/" in k and k != "24/7"), key=len, reverse=True):   # w/ w/o b/w a/b and/or: whole words only, so show/hide and new/old are left alone
        t = re.sub(r"(?<![A-Za-z0-9])" + re.escape(k) + (r"(?![A-Za-z0-9])" if k[-1].isalnum() else ""), SHORT[k], t, flags=re.I)
    t = re.sub(r"\bv(?=\d+\.\d)", "version ", t, flags=re.I)                                 # v2.5 -> version 2.5
    t = re.sub(r"(?<![\d.,/:\-])(\d{1,2})([./-])(\d{1,2})\2(\d{4}|\d{2})(?![\d.]|/\d)", lambda m: _fmt_date(m[1], m[3], m[4], m[0]), t)   # full dates with a year
    t = re.sub(r"(?<![\d.,/:\-])(1[3-9]|2\d|3[01])\.(0[1-9]|1[0-2])(?![\d.]|/\d|:\d)", lambda m: _fmt_date(m[1], m[2], "", m[0]), t)   # 22.11: a day above 12 and a two digit month
    t = re.sub(r"(?<![\d.,/:\-])(\d{1,3})\.(\d{1,3})(?![\d.]|/\d|:\d)", _decimal, t)       # 2.5 -> two point five, never "do point panch" (dates, IPs, 1.2.3 are left alone)
    t = re.sub(r"\b([A-Za-z][A-Za-z0-9]{0,11})(\.?)(?=\W|$)", _short, t)
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


# --- the gate: what the voice would STILL say wrong after all the rules above. The script writer rejects a script that has any of these, so the writer fixes the words
#     before the voice ever sees them (see src/pronounce.py). Each finding says what was written, what the voice would do with it and what to write instead.
CAPS_OK = {"am", "pm", "ist"}


def _lexicon() -> set[str]:
    try:
        return {str(k).lower() for k in json.loads(Path(__file__).with_name("pronunciations.json").read_text(encoding="utf-8"))}
    except Exception:
        return set()


LEXICON = _lexicon()


@dataclass(frozen=True)
class Finding:
    kind: str          # caps-word | glued | symbol
    token: str
    message: str       # concrete: the word, where it was heard, what the voice would do, what to write instead


def audit(text: str, allow=()) -> list[Finding]:
    """Everything in `text` that the voice would still mispronounce after the cleaner has done its work. `allow` = capital-letter words that ARE meant as words (the DM keywords)."""
    names = {str(a).lower() for a in allow if a} | CAPS_OK | set(SHORT) | LEXICON
    spoken = strip_signs(expand(text))
    found: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, m: re.Match, why: str) -> None:
        if (kind, m[0]) in seen:
            return
        seen.add((kind, m[0]))
        ctx = spoken[max(0, m.start() - 28): m.end() + 28].strip()
        found.append(Finding(kind, m[0], f'"{m[0]}" (heard in: "...{ctx}...") {why}'))

    for m in re.finditer(r"\b[A-Z]{2,6}s?\b", spoken):
        low = m[0].lower()
        if low in names or low.rstrip("s") in names:
            continue
        add("caps-word", m, f'is written in capitals but has no spelling in the pronunciation list, so the voice would say it as one word ("{low}"). Write a plain word instead, or spell it with spaces (S E R P).')
    for m in re.finditer(r"\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]+\b", spoken):
        if re.fullmatch(r"\d{1,2}(am|pm)|\d+(st|nd|rd|th)", m[0], re.I) or m[0].lower() in names:
            continue
        add("glued", m, "mixes digits and letters, so the voice may spell it out or skip part of it. Write the number and the word apart, or in full words.")
    for m in re.finditer(r"[+=$@%]", spoken):
        add("symbol", m, "is a symbol the voice would read out or drop. Say it in words (plus, equals, dollars, at, percent).")
    return found
