"""Carousel planner. Every carousel follows the SAME order, enforced by code and not left to the model:
    1 hook slide -> 1-2 problem slides -> 2-3 solution slides -> 1 CTA slide   (5 to 7 slides; the service diagram may add one solution slide).
A 'taste' (config/carousel_flavors.json) only changes HOW the parts are told: a bold hook with a slow reveal, a myth bust, a short imaginary scene, a verified
fact from a named source, and so on. Tastes rotate, and the one used is saved on the draft so the weekly review can compare them.
Safety: no prices, payment words, delivery times, percentages or multipliers, guarantees or invented attributions. The 'factual-source' taste is only used
when config/facts.json holds a fact YOU verified, and the slides must quote it exactly; a model never makes up who said what."""
import json
import re

from .. import config, llm
from .problems import audience

ORDER = ["hook", "problem", "solution", "cta"]
LIMITS = {"hook": (1, 1), "problem": (1, 2), "solution": (2, 3), "cta": (1, 1)}
MAX_WORDS = {"headline": 14, "body": 40, "hook_body": 14}
BANNED = re.compile(r"(?i)(%|\b\d+\s?x\b|₹|\brs\.?\s*\d|\binr\b|\$|\bprice|\bpricing|\bcost|\bpay\b|\bpaid\b|\bpayment|\bfree\b|\bdiscount|\bguarantee|\bproven\b|\b\d+\s*hours?\b)")
INVENTED_SOURCE = re.compile(r"(?i)\b(according to|studies show|a study|survey|research (shows|says|finds)|experts? (say|says|agree)|reported|announced)\b")
SYS = "You write honest, simple carousel posts for small-business owners in India. You never invent statistics, clients, quotes or sources."


def flavors():
    return config.load_json(config.ROOT / "config" / "carousel_flavors.json", {}).get("flavors", [])


def facts_for(service_id):
    fs = config.load_json(config.ROOT / "config" / "facts.json", {}).get("facts", [])
    return [f for f in fs if f.get("claim") and f.get("source_name") and (not f.get("services") or service_id in f["services"])]


def _used(date):
    out = []
    for f in sorted(config.DRAFTS.glob("*.json")):
        d = config.load_json(f, None)
        if isinstance(d, dict) and str(d.get("date", "")) < str(date) and (d.get("carousel") or {}).get("flavor"):
            out.append((d["carousel"]["flavor"], (d["carousel"] or {}).get("fact_id")))
    return out


def pick_flavor(date, service_id):
    """(taste, fact or None): never one of the last two tastes, otherwise the least used; fact tastes only when a verified fact exists."""
    fs = facts_for(service_id)
    usable = [f for f in flavors() if not f.get("needs_fact") or fs]
    if not usable:
        return None, None
    used = _used(date)
    ids = [u[0] for u in used]
    pool = [f for f in usable if f["id"] not in ids[-2:]] or usable
    taste = min(pool, key=lambda f: (ids.count(f["id"]), usable.index(f)))
    fact = None
    if taste.get("needs_fact"):
        seen = [u[1] for u in used if u[0] == taste["id"]]
        fact = min(fs, key=lambda x: (seen.count(x.get("id")), fs.index(x)))
    return taste, fact


def _words(t):
    return len(re.findall(r"\S+", t or ""))


def normalize(slides, focus):
    out = []
    for s in slides if isinstance(slides, list) else []:
        if isinstance(s, dict):
            out.append({"role": str(s.get("role", "")).strip().lower(), "headline": " ".join(str(s.get("headline", "")).split()), "body": " ".join(str(s.get("body", "")).split())})
    for s in out:
        if s["role"] == "cta":                               # the CTA slide always carries the real DM keyword
            s["headline"] = f"DM {focus['dm_keyword']}"
    return out


def validate(slides, focus, taste, fact):
    """Problems (empty list = fine). The order and counts are never negotiable."""
    probs = []
    roles = [s["role"] for s in slides]
    if any(r not in ORDER for r in roles):
        return [f"every role must be one of {ORDER}"]
    if roles != sorted(roles, key=ORDER.index):
        probs.append("the order must be hook, then problem, then solution, then cta")
    for r, (lo, hi) in LIMITS.items():
        if not lo <= roles.count(r) <= hi:
            probs.append(f"need {lo}-{hi} '{r}' slide(s), got {roles.count(r)}")
    if len(slides) > 7:
        probs.append("at most 7 slides")
    text = " ".join(f"{s['headline']} {s['body']}" for s in slides)
    for i, s in enumerate(slides, 1):
        if not s["headline"]:
            probs.append(f"slide {i} has no headline")
        if _words(s["headline"]) > MAX_WORDS["headline"]:
            probs.append(f"slide {i} headline is over {MAX_WORDS['headline']} words")
        if _words(s["body"]) > (MAX_WORDS["hook_body"] if s["role"] == "hook" else MAX_WORDS["body"]):
            probs.append(f"slide {i} body is too long")
    bad = BANNED.search(text)
    if bad:
        probs.append(f"'{bad.group(0)}' is not allowed (no prices, payment words, delivery times, percentages, multipliers or guarantees)")
    if fact is None and INVENTED_SOURCE.search(text):
        probs.append("do not attribute anything to a study, survey, expert or report; there is no verified source for this carousel")
    if fact is not None:
        first = " ".join(f"{s['headline']} {s['body']}" for s in slides[:2]).lower()
        if fact["source_name"].lower() not in (slides[0]["headline"] + " " + slides[0]["body"]).lower():
            probs.append(f"the hook must name the source '{fact['source_name']}'")
        if fact["claim"].lower() not in first:
            probs.append("slides 1-2 must quote the verified claim exactly")
    return probs


def plan(post_plan, focus, brand, taste, fact, guidance="", notes=""):
    hook = post_plan["hooks"][post_plan.get("chosen_hook", 0)]["text"]
    fact_block = ""
    if fact:
        fact_block = (f"\nFACT (verified by the owner; the ONLY source you may name): source = {fact['source_name']}; claim = \"{fact['claim']}\"; link = {fact.get('source_url', '')}\n"
                      "Quote the claim exactly once in slide 1 or 2 and name the source in the hook. Add no other statistic or attribution.")
    prompt = f"""Write a swipe CAROUSEL for the service in focus.
Service: {focus['name']}: {focus['pitch']}
Audience: {audience(focus)}
Topic: {post_plan['topic']} | Angle: {post_plan.get('angle', '')} | Key points: {json.dumps(post_plan.get('key_points', []), ensure_ascii=False)}
Opening idea (adapt it to the taste): {hook}
Guidance: {guidance[:500]}

TASTE: {taste['name']}: {taste['taste']}
STRICT ORDER, never change it: 1 hook slide, then 1-2 problem slides, then 2-3 solution slides, then 1 cta slide.
- hook: {taste['hook']}
- problem: {taste['problem']}
- solution: {taste['solution']}
- cta: {taste['cta']} The cta headline is exactly: DM {focus['dm_keyword']}
{fact_block}
Brand rules that always apply: {json.dumps(brand['facts_rules'], ensure_ascii=False)}
Slide rules: each slide has "headline" (max {MAX_WORDS['headline']} words) and "body" (max {MAX_WORDS['body']} words; the hook body max {MAX_WORDS['hook_body']}). Plain words a busy owner understands. One idea per slide.
Never write prices, payment words, "free", delivery times, percentages, multipliers like 10x, guarantees, invented numbers, clients, testimonials or demos. Any scene must be clearly imaginary
("Imagine...", "Example"). Never say a person, company, study or report said something unless it is the FACT above.
{notes}
Return JSON: {{"slides": [{{"role": "hook|problem|solution|cta", "headline": "...", "body": "..."}}]}}"""
    out = llm.ask_json(llm.gemini, prompt, SYS)
    return normalize(out.get("slides") if isinstance(out, dict) else None, focus)


def check(slides, focus, brand, fact):
    """A second model reads the whole carousel the way a sceptical reader would. Returns a list of issues (empty = fine)."""
    shown = [{"slide": i, "role": s["role"], "headline": s["headline"], "body": s["body"]} for i, s in enumerate(slides, 1)]
    prompt = f"""Fact-check this carousel for {focus['name']}.
Slides: {json.dumps(shown, ensure_ascii=False)}
Verified fact the carousel may use (the only allowed source): {json.dumps(fact, ensure_ascii=False) if fact else 'NONE'}
Brand facts and rules: {json.dumps(brand, ensure_ascii=False)}
Flag every slide that: invents a statistic, client, testimonial, result, demo or price; says a real person, company, study or report said something (unless it is the verified fact);
promises or guarantees an outcome; presents an imaginary scene as real; or describes the service wrongly. Slides that are fine are not listed.
Return JSON: {{"ok": true/false, "issues": ["slide N: what is wrong"]}}"""
    out = llm.ask_json(llm.factcheck_model, prompt, "You are a strict, fair fact-checker. Answer with JSON only.")
    if not isinstance(out, dict) or "ok" not in out:
        raise RuntimeError("fact-check returned no verdict")
    return [] if out["ok"] else [str(i)[:200] for i in (out.get("issues") or ["the fact-check rejected the carousel"])][:6]


def build(post_plan, focus, brand, guidance, date):
    """-> ({"flavor", "fact_id", "slides", "checked"}, None) or (None, reason). The caller falls back to a single image when there is no carousel."""
    taste, fact = pick_flavor(date, focus["id"])
    if not taste:
        return None, "no carousel taste is available"
    notes = ""
    for _ in range(2):
        slides = plan(post_plan, focus, brand, taste, fact, guidance, notes)
        probs = validate(slides, focus, taste, fact)
        checked = False
        if not probs:
            try:
                probs, checked = check(slides, focus, brand, fact), True
            except Exception as e:                     # the human still approves every post and sees every slide, but say it was not machine-checked
                print(f"[carousel] fact-check unavailable: {e}")
        if not probs:
            return {"flavor": taste["id"], "fact_id": fact.get("id") if fact else None, "slides": slides, "checked": checked, "diagram": bool(taste.get("diagram"))}, None
        notes = "FIX THESE PROBLEMS and keep the strict order: " + "; ".join(probs)
    return None, "; ".join(probs)[:300]
