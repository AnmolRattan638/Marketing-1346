"""Hardcoded marketing-skills layer (marketingskills pack by Corey Haines, MIT, vendored in marketing-skills/).

Marketing = WHAT we say (who it is for, which offer, which claims, which ask). Content skills (src/contentskills.py) = HOW we say it (hook, retention, caption craft).
They must never contradict, so there is ONE source of truth, config/marketing.json (the product-marketing context doc the pack's skills read first), and a fixed precedence:

    marketing brief (this module)  >  content skills  >  style preferences

Jobs:
 1. block(stage, focus): the brief + rule digests injected into every script / caption / carousel / video-plan prompt.
 2. *_problems(): deterministic validators (claims, offers, AI tells, price, keyword, ICP, funnel); a failing output is rejected with the exact fix.
 3. alignment_problems(): the same service, keyword, price and offer in script, caption, carousel and video plan (no two outputs disagree).
 4. audit(): an LLM pass using the pack's own copy-editing / offers / product-marketing guidance.
The pack's promo / tool-registry sections are stripped by load(); the agent never mentions them.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "marketing-skills" / "skills"
BRIEF_PATH = ROOT / "config" / "marketing.json"

PRECEDENCE = ("PRECEDENCE: the MARKETING BRIEF below decides WHAT is said (audience, offer, claims, the one DM keyword and what it gets). The CONTENT SKILLS decide HOW it is said "
              "(hook, pacing, captions). If a content rule seems to conflict with the brief (for example a 'comment YES' style ask), the brief wins: ask once, with the service's keyword, "
              "naming what the viewer gets.")

_cache = {}


def brief() -> dict:
    if "b" not in _cache:
        _cache["b"] = json.loads(BRIEF_PATH.read_text(encoding="utf-8"))
    return _cache["b"]


def cta_for(focus: dict) -> dict:
    """{'keyword','gets','terms'} for the service in focus; the keyword always comes from services.json (the real DM keyword)."""
    c = dict(brief()["ctas"].get(focus.get("id") or "", {}))
    if focus.get("dm_keyword"):
        c["keyword"] = focus["dm_keyword"]
    c.setdefault("keyword", "")
    c.setdefault("gets", "honest advice on whether it fits your business")
    c.setdefault("terms", [])
    return c


def load(skill: str, rel: str = "SKILL.md") -> str:
    """A pack file with front matter, tool-registry sections and sponsor blockquotes removed."""
    p = SKILLS / skill / rel
    if not p.exists():
        return ""
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"\A---.*?\n---\n", "", t, flags=re.S)
    t = re.sub(r"^#{2,3} (Publishing From Your Agent|Tools? .*|Related Skills|Integrations?).*?(?=^#{1,3} |\Z)", "", t, flags=re.S | re.M)
    t = re.sub(r"^>.*(Magister|Disclosure).*?(?=^[^>]|\Z)", "", t, flags=re.S | re.M)
    return t.strip()


def pillar(date: str) -> str:
    """Deterministic 60/30/10 pillar for a date string (YYYY-MM-DD): educate / how_it_works / offer."""
    n = sum(map(ord, str(date))) % 10
    return "educate" if n < 6 else "how_it_works" if n < 9 else "offer"


def block(stage: str, focus: dict, date: str = "") -> str:
    """Hardcoded marketing digest for a stage ('script', 'caption', 'carousel', 'video')."""
    b, c = brief(), cta_for(focus)
    date = date or __import__("datetime").date.today().isoformat()
    pil = b["pillars"][pillar(date)]
    rules = [
        f"AUDIENCE: {b['icp']}",
        f"POSITIONING: {b['positioning']} Voice: {b['voice']}",
        f"SERVICE IN FOCUS: {focus.get('name')}. It speaks ONLY about this service; do not drift to another service or promise what it does not do.",
        f"ONE ASK: DM {c['keyword']} and say exactly what they get: {c['gets']}. The ask rides the last beat / last slide / last caption line only; the hook never carries a price, the brand, the keyword or an offer. Never another service's keyword.",
        "OFFERS ALLOWED: " + "; ".join(b["offers_allowed"]) + ". Nothing else free or discounted. Forbidden words: " + ", ".join(b["offers_forbidden"]) + ".",
        "CLAIMS: " + " ".join(b["claims_rules"]) + " Forbidden: " + ", ".join(b["claims_forbidden"]) + ".",
        f"FUNNEL: {b['funnel']['goal']} Beat roles: " + "; ".join(f"{k} = {v}" for k, v in b["funnel"]["beat_roles"].items()) + ".",
        f"TODAY'S PILLAR: {pillar(date)} ({pil['job']}).",
        "NO AI TELLS: " + "; ".join(b["ai_tells_forbidden"]) + ". Fill every hook formula with a specific fact, number or scene.",
    ]
    if stage == "video":
        rules.append("The video's scenes, on-screen text and voice-over carry the same service, the same one ask and the same claims as the master script; a scene adds no offer, price, claim or keyword of its own.")
    if stage == "caption":
        rules.append("Caption, carousel and video are ONE story with ONE ask: reuse the script's keyword and deliverable, never a different one.")
    return "\nMARKETING BRIEF (mandatory; the output is rejected if it breaks it):\n- " + "\n- ".join(rules) + "\n" + PRECEDENCE + "\n"


# ---- deterministic validators ----
def _rx(words):
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)


_OFFERS = None
_CLAIMS = None
EMDASH = re.compile(r"—| -- ")
CONTRAST = re.compile(r"\b(it'?s|it is|this is|that'?s)\s+not\b[^.!?\n]{1,60}[,;]\s*(but\s+|it'?s\s+|it is\s+)|\bnahi\b[^.!?\n]{0,40},?\s*\bbalki\b|\bnot because\b[^.!?\n]{1,60}\.\s*because\b", re.I)
NEGLIST = re.compile(r"\bno [a-z]+,\s*no [a-z]+", re.I)
SELFQ = re.compile(r"\b(the result|the best part|the catch|the secret|the bonus)\s*[?:]", re.I)
STOCK = re.compile(r"\b(say goodbye to|unlock the power|game[- ]?changer|take it to the next level|here'?s the thing|let that sink in|read that again|reimagined|supercharge)\b", re.I)
BAITQ = re.compile(r"(\bagree\?|\bthoughts\?|\bwho else\?)", re.I)
PRICE = re.compile(r"(?:₹|\brs\.?|\binr)\s*([\d,]+)", re.I)
DEV = re.compile(r"\b(web ?developers?|developers?|coders?|web ?designers?|website designers?)\b", re.I)
LEADGEN_ONLY = re.compile(r"\b(freelancers?|agenc(?:y|ies))\b", re.I)
BRAND = re.compile(r"\bAR Designs\b|\bLocalSignal\b", re.I)


def _offers():
    global _OFFERS, _CLAIMS
    if _OFFERS is None:
        _OFFERS, _CLAIMS = _rx(brief()["offers_forbidden"]), _rx(brief()["claims_forbidden"])
    return _OFFERS


def _prices_ok(focus):
    note = " ".join(str(s.get("price_note", "")) for s in [focus] if isinstance(s, dict))
    return {n.replace(",", "") for n in re.findall(r"[\d,]{3,}", note)}


def other_keywords(focus):
    mine = cta_for(focus)["keyword"]
    if not mine:
        return set()
    return {c["keyword"] for c in brief()["ctas"].values() if c["keyword"] != mine} | {s for s in ("SITE", "BOT", "ADS", "LEADS", "SCRIPT", "BLOG") if s != mine}


def text_problems(text: str, focus: dict, where: str = "text", hook: bool = False) -> list[str]:
    """Rule breaks in one piece of text. `hook=True` for the opening line / first slide / first caption line."""
    t = str(text or "")
    c = cta_for(focus)
    out = []
    _offers()
    m = _OFFERS.search(t)
    if m:
        out.append(f"{where}: '{m.group(0)}' is an offer we do not make (only pay-after-approval and a short DM chat are allowed); remove it")
    m = _CLAIMS.search(t)
    if m:
        out.append(f"{where}: '{m.group(0)}' is an absolute / unverifiable claim; say what the service does (can help, makes it easier)")
    if EMDASH.search(t):
        out.append(f"{where}: no em dashes; use a full stop")
    if CONTRAST.search(t):
        out.append(f"{where}: contrast reveal ('it is not X, it is Y'); state the point directly")
    if NEGLIST.search(t):
        out.append(f"{where}: negation list ('No X, no Y'); say what does happen")
    if SELFQ.search(t):
        out.append(f"{where}: self-answered question ('The result? ...'); just state it")
    if STOCK.search(t) or BAITQ.search(t):
        out.append(f"{where}: stock phrase or engagement bait; say the plain point")
    for k in other_keywords(focus):
        if re.search(rf"\b{k}\b", t):
            out.append(f"{where}: '{k}' is another service's DM keyword; this post's only keyword is {c['keyword']}")
    if focus.get("id") == "lead_gen":
        if DEV.search(t):
            out.append(f"{where}: lead-gen speaks to freelancers, agencies and service sellers; never call the reader a developer/coder/designer")
        if PRICE.search(t):
            out.append(f"{where}: no price for lead gen; say DM")
    else:
        if LEADGEN_ONLY.search(t):
            out.append(f"{where}: this service speaks to business owners; do not address freelancers or agencies")
        bad = [n for n in (p.replace(",", "") for p in PRICE.findall(t)) if n not in _prices_ok(focus)]
        if bad:
            out.append(f"{where}: price {bad} is not in the price list; copy a price only from the service's price note")
    if hook:
        if PRICE.search(t) or BRAND.search(t) or (c["keyword"] and re.search(rf"\b{c['keyword']}\b", t)):
            out.append(f"{where}: the hook carries no price, brand or DM keyword; it shows the owner's pain")
    return out


def script_problems(script: dict, focus: dict) -> list[str]:
    """Marketing rules for a master script: claims/offers/tells in every beat, one ask only on the cta beat with the real keyword, hook clean, on-service."""
    beats = script.get("beats") or []
    c = cta_for(focus)
    out = []
    for i, b in enumerate(beats):
        name = b.get("beat") or f"beat {i + 1}"
        out += text_problems(f"{b.get('line', '')} {b.get('screen', '')}", focus, name, hook=(i == 0))
        if b.get("beat") != "cta" and c["keyword"] and re.search(rf"\b{c['keyword']}\b", str(b.get("line") or ""), re.I) and re.search(r"\b(DM|comment|send|bhej|likho)\b", str(b.get("line") or ""), re.I):
            out.append(f"{name}: the ask belongs only in the cta beat")
    if beats and beats[-1].get("beat") == "cta" and c["keyword"] and not re.search(rf"\b{c['keyword']}\b", str(beats[-1].get("line") or ""), re.I):
        out.append(f"cta: must ask for exactly one thing: the word {c['keyword']}, and say what they get ({c['gets']})")
    full = re.sub(rf"\b{c['keyword'] or 'x'}\b", "", " ".join(str(b.get("line") or "") for b in beats), flags=re.I).lower()
    if c["terms"] and beats and not any(t in full for t in c["terms"]):
        out.append(f"script is off-service: it never mentions {focus.get('name')} (use one of: {', '.join(c['terms'][:5])})")
    return list(dict.fromkeys(out))


def caption_problems(text: str, focus: dict) -> str:
    """'; '-joined marketing issues for an Instagram caption (empty = fine)."""
    return "; ".join(caption_issues(text, focus))


def caption_issues(text: str, focus: dict) -> list[str]:
    t = re.sub(r"\*+", "", str(text or ""))
    body = re.sub(r"#\w+", "", t).strip()
    first = body.split("\n", 1)[0]
    c = cta_for(focus)
    out = text_problems(body, focus, "caption") + text_problems(first, focus, "caption first line", hook=True)
    if c["keyword"] and not re.search(rf"\b{c['keyword']}\b", body):
        out.append(f"caption: end with ONE soft ask: DM {c['keyword']} (the same keyword as the video and carousel)")
    return list(dict.fromkeys(out))


def carousel_problems(slides: list, focus: dict) -> list[str]:
    out = []
    for i, s in enumerate(slides or [], 1):
        where = f"slide {i}"
        txt = f"{s.get('headline', '')} {s.get('body', '')}"
        if s.get("role") == "cta":
            txt = re.sub(rf"\bDM {cta_for(focus)['keyword']}\b", "", txt)
        out += text_problems(txt, focus, where, hook=(i == 1))
    return list(dict.fromkeys(out))


def alignment_problems(focus: dict, script: dict | None = None, caption: str = "", slides: list | None = None, plan: dict | None = None) -> list[str]:
    """Cross-output check: the video script, the caption, the carousel and the video plan must carry the same service, one keyword, and prices from the same list."""
    c = cta_for(focus)
    kw = c["keyword"]
    parts = {}
    if script:
        parts["script"] = " ".join(str(b.get("line") or "") for b in script.get("beats", []))
    if caption:
        parts["caption"] = re.sub(r"\*+", "", str(caption))
    if slides:
        parts["carousel"] = " ".join(f"{s.get('headline', '')} {s.get('body', '')}" for s in slides)
    if plan:
        parts["video plan"] = " ".join(str(s.get("narration") or "") + " " + json.dumps(s.get("graphic") or {}, ensure_ascii=False) for s in plan.get("scenes", []))
    out = []
    for name, txt in parts.items():
        for k in other_keywords(focus):
            if re.search(rf"\b{k}\b", txt):
                out.append(f"{name} asks for {k} but this post's keyword is {kw}; all outputs must ask for {kw}")
        if kw and name in ("caption", "carousel") and not re.search(rf"\b{kw}\b", txt):
            out.append(f"{name} does not carry the shared ask (DM {kw}) that the video script uses")
        if c["terms"] and not any(t in re.sub(rf"\b{kw}\b", "", txt, flags=re.I).lower() for t in c["terms"]):
            out.append(f"{name} is off-service: it never mentions {focus.get('name')}")
        if focus.get("id") != "lead_gen":
            bad = [n for n in (p.replace(",", "") for p in PRICE.findall(txt)) if n not in _prices_ok(focus)]
            if bad:
                out.append(f"{name} quotes price {bad} that is not in the price list")
    return list(dict.fromkeys(out))


def audit(script: dict, focus: dict, ask) -> list[str]:
    """LLM pass: does this script follow the marketing brief (right audience, one honest ask, no unsupported promise, no AI tells)? Empty list = pass or no checker."""
    from . import llm
    rows = [{"beat": b.get("beat"), "line": b.get("line")} for b in script.get("beats", [])]
    guide = "\n\n".join(x for x in (load("copy-editing")[:2500], load("offers")[:1500]) if x)
    prompt = ("Check this short-video script against the MARKETING BRIEF. Flag ONLY clear failures: wrong audience for the brief's ICP; a promise of a result instead of a capability; "
              "an offer that is not in offers_allowed; a hook that sells (price, brand, keyword) instead of showing the owner's pain; a poke (beat 2) that only restates the problem instead of giving the first new specific answer (viewers leave by second 5); a thin script that is short because it says nothing; a CTA that asks for anything but the one keyword with what they get; "
              "copy that reads as AI (contrast reveals, negation lists, stock phrases). Each issue must give the exact fix. Return JSON {\"issues\": [\"beat: problem and fix\"]}, empty if it passes.\n"
              f"BRIEF: {json.dumps({k: brief()[k] for k in ('icp', 'positioning', 'offers_allowed', 'claims_rules')}, ensure_ascii=False)}\nONE ASK FOR THIS POST: DM {cta_for(focus)['keyword']} to get {cta_for(focus)['gets']}\n"
              f"PACK GUIDANCE (copy editing and offers):\n{guide[:4000]}\nSCRIPT: {json.dumps(rows, ensure_ascii=False)}")
    try:
        res = llm.ask_json(ask, prompt, "You are a strict marketing editor. JSON only.")
        return [str(x) for x in (res or {}).get("issues", [])][:3] if isinstance(res, dict) else []
    except Exception:
        return []
