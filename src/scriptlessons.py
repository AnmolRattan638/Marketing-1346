"""Scriptwriter mistakes -> remembered lessons.

Every time a script is rejected, each reason is turned into a general rule and counted in data/script_lessons.json (data/ is committed by the workflow even when the run fails, so the
memory survives). The most frequent rules go into the NEXT script prompt as "mistakes you made before", so they are avoided from the first try. A few rules the model really broke are
always present (SEED), so a fresh repo still starts with them."""
import datetime
import json
import re
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "data" / "script_lessons.json"
SEED = [
    "Keep the WHOLE script at 52-85 words: short but never weak, beat 2 must give the first surprising specific answer within the first 8 seconds.",
    "Write EVERY beat of the style, in order, and finish with the last one (cta). Never stop early.",
    "Every digit you speak or show must appear in a cited fact or in the service capabilities (24x7 is allowed); otherwise say the idea in words.",
    "State what the service does; never promise a result for the owner (no 'never lose a lead', no 'guaranteed', no sales numbers).",
    "Only the cta beat asks; it asks for the ONE keyword and says what they get. No demo, sample, discount or free trial.",
    "Write every spoken line so a voice can say it: no ALL-CAPS word except the DM keyword (write 'SERP' as a plain word or as S E R P), no digits glued to letters (2BHK, Q4, mp3), no symbols (+ = $ @); acronyms the voice knows are fine (UPI, GST, SEO, CRM, FAQ, 24x7).",
]
RULES = [
    (r"linkedin\[pitchy\]", "linkedin-pitchy", "LinkedIn is personal, not an ad: no DM, price, 'pay after approval', discount, urgency or hire-me language; say it in plain words."),
    (r"linkedin\[context\]", "linkedin-context", "Assume the reader has never heard of anything you built: the first time you name it (content system, Lead Finder, LocalSignal, the voice), say in one plain sentence what it is and does, within the first two paragraphs, before the story's point."),
    (r"linkedin\[hook\]", "linkedin-hook", "The first line must be one curious sentence of 18 words or fewer that starts with a specific true detail, an admission or a real question; never 'Small businesses...' or another generic opener."),
    (r"linkedin\[never\]", "linkedin-never", "Never write a phrase the facts file bans (client names, student, years of experience, job offers, DM)."),
    (r"linkedin\[numbers\]", "linkedin-numbers", "Use only numbers that are written in the facts file, and never claim a count of clients or customers."),
    (r"linkedin\[pitch-share\]", "linkedin-pitch-share", "On a pitch day keep the offer to 30% of the post or less and list its sentences in pitch_sentences; on every other day write no offer at all."),
    (r"linkedin\[(length|shape|links)\]", "linkedin-shape", "Write 110 to 250 words in at least 3 short paragraphs, first person, no links, no hashtags, no exclamation marks, no percentages, at most one emoji."),
    (r"pronunciation: .*capitals", "pronounce-caps", "Never write an unknown ALL-CAPS word in a spoken line (the voice says it as one word); use a plain word or spell it with spaces (S E R P). Only the DM keyword may be in capitals."),
    (r"pronunciation: .*digits and letters", "pronounce-glued", "Never glue digits to letters in a spoken line (2BHK, Q4, mp3); write the number and the word apart or in full words."),
    (r"pronunciation: .*symbol", "pronounce-symbol", "Never leave a symbol (+ = $ @) in a spoken line; say it in words."),
    (r"not backed by a cited fact", "number-unbacked", "Every digit must come from a cited fact; if no fact has the number, say it in words with no digit."),
    (r"beats must be exactly", "beats-exact", "Return exactly the style's beats in order, including the last one."),
    (r"script is \d+ words", "total-length", "The whole script stays under 85 words (about 30 s); give each beat one concrete idea and its reason, nothing more."),
    (r"line has \d+ words", "words", "Keep each beat inside its word range, in full spoken sentences."),
    (r"generic filler", "generic", "No filler like 'game changer' or 'next level'; say something only this business could say."),
    (r"not Hinglish", "hinglish", "Every spoken line is everyday Hindi in Roman letters with English tech words."),
    (r"too abstract", "abstract", "Name a concrete moment or thing (11 pm message, unanswered enquiry) in pain and poke."),
    (r"turns a statistic into a promise", "promise-stat", "Say only what the fact says; do not turn a statistic into a promise."),
    (r"another service's DM keyword", "wrong-keyword", "Use only this post's own DM keyword."),
    (r"ask belongs only in the cta", "ask-early", "Keep the DM ask out of every beat except cta."),
    (r"cta: must ask", "cta-ask", "The cta names the one keyword and what the viewer gets."),
    (r"offer we do not make", "offer", "No demo, sample, discount, free trial or limited-seats offer."),
    (r"absolute / unverifiable claim", "claim", "No absolute claims; say 'can help' or 'makes it easier'."),
    (r"em dash|contrast reveal|negation list|self-answered|stock phrase", "ai-tell", "No em dashes, 'it is not X, it is Y', 'No X, no Y' or stock phrases; state the point directly."),
    (r"hook carries no price|hook is too long|opens with a greeting", "hook", "The hook is a short scene of the owner's pain: no greeting, price, brand or keyword."),
    (r"off-service|never names", "off-service", "Talk about the service in focus only."),
    (r"fix: needs 2-3 concrete steps", "steps", "The fix beat walks through 2-3 short steps and the spoken line follows them."),
    (r"bare statements", "connectors", "Use helping words (kyunki, isliye, jaise ki, phir) so each line gives its reason."),
    (r"absolute result|outcomes? no fact supports|promises? (an? )?(absolute|outcome)|never have to wait", "promise", "Describe what the service does (replies instantly, collects enquiries); never promise an outcome like 'no enquiry is missed' or 'you will never lose a lead'."),
    (r"first-frame headline|`screen`", "screen", "`screen` text is a 2-6 word bold headline that works on mute; no full sentence."),
    (r"fact id", "fact-id", "Cite only fact ids that exist on the sheet."),
]


def explain(problem: str) -> tuple[str, str]:
    """-> (key, general rule) for one rejection reason."""
    msg = re.sub(r"^(meaning|skills|marketing):\s*", "", str(problem))
    for rx, key, rule in RULES:
        if re.search(rx, msg, re.I):
            return key, rule
    msg = re.split(r"\bFix:", msg)[0]
    short = re.sub(r"\d+", "N", re.sub(r"'[^']{3,}'|\"[^\"]{3,}\"", "...", re.sub(r"^[\w, ]{2,30}:\s*", "", msg)))[:130]
    return "other:" + short[:40], short


def load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


_COUNTED: set[tuple[str, str, str]] = set()      # one rejection reason is counted once per run, however many repair rounds show it again
KEEP_RECENT = 3


def concrete(problem: str) -> str:
    """The rejection as it happened: which beat, what was written, why it failed, how to fix it (the validator's own words, trimmed)."""
    return re.sub(r"\s+", " ", str(problem)).strip()[:260]


def record(problems: list[str]) -> None:
    """Count each rejection AND keep the concrete mistake with its date, so the next script prompt can say exactly what went wrong last time."""
    data = load()
    today = datetime.date.today().isoformat()
    for p in problems:
        key, rule = explain(p)
        what = concrete(p)
        once = (str(STATE), key, what)
        if once in _COUNTED:
            continue
        _COUNTED.add(once)
        row = data.setdefault(key, {"count": 0})
        row["count"] += 1
        row["rule"] = rule
        recent = [r for r in row.get("recent", []) if r.get("mistake") != what]
        recent.append({"on": today, "mistake": what})
        row["recent"] = recent[-KEEP_RECENT:]
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


SEED_LINKEDIN = [
    "A LinkedIn post is a person talking: first person, one true story or one thing built, plain words, a curious first line that is paid off inside the post.",
    "Use only the facts you are given. No prices, no client names, no results, no invented numbers, no DM keyword, no 'pay after approval'.",
]


def prompt_block(limit: int = 6, scope: str | None = None) -> str:
    """The rules the writer must not break again. scope='linkedin' shows only the LinkedIn lessons; the default shows only the script lessons, so neither crowds the other out."""
    li = scope == "linkedin"
    rules = list(SEED_LINKEDIN if li else SEED)
    rows = [kv for kv in load().items() if kv[0].startswith("linkedin-") == li]
    for _, row in sorted(rows, key=lambda kv: -kv[1].get("count", 0))[:limit]:
        if row.get("rule") and row["rule"] not in rules:
            last = (row.get("recent") or [{}])[-1].get("mistake")
            rules.append(f"{row['rule']} (rejected {row['count']}x before)" + (f" LAST TIME you wrote this and it was rejected: {last}" if last else ""))
    what = "a LinkedIn post" if li else "a script"
    return f"\nMISTAKES YOU HAVE MADE BEFORE (a rejected {what} costs the whole day; check each before answering):\n- " + "\n- ".join(rules) + "\n"
