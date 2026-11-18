"""Scriptwriter mistakes -> remembered lessons.

Every time a script is rejected, each reason is turned into a general rule and counted in data/script_lessons.json (data/ is committed by the workflow even when the run fails, so the
memory survives). The most frequent rules go into the NEXT script prompt as "mistakes you made before", so they are avoided from the first try. A few rules the model really broke are
always present (SEED), so a fresh repo still starts with them."""
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
]
RULES = [
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


def record(problems: list[str]) -> None:
    data = load()
    for p in problems:
        key, rule = explain(p)
        row = data.setdefault(key, {"count": 0})
        row["count"] += 1
        row["rule"] = rule
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def prompt_block(limit: int = 6) -> str:
    rules = list(SEED)
    for _, row in sorted(load().items(), key=lambda kv: -kv[1].get("count", 0))[:limit]:
        if row.get("rule") and row["rule"] not in rules:
            rules.append(f"{row['rule']} (rejected {row['count']}x before)")
    return "\nMISTAKES YOU HAVE MADE BEFORE (a rejected script costs the whole day; check each before answering):\n- " + "\n- ".join(rules) + "\n"
