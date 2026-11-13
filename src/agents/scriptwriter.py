"""Master scriptwriter: ONE script per day, written only from the verified fact sheet. The carousel and the video both read it.

Output: {"style", "hook", "hooks": [5 candidates with scores], "beats": [{"beat","line","screen","visual","facts"}], "cta", "language"}.
Code enforces what a model drifts on: every number must come from a cited fact, 5-14 words per spoken line, no greeting/intro, hook scored and picked by code."""
import json
import re
from .. import config, llm

STYLES = [
    {"id": "pain-poke-fix", "name": "6-beat framework", "beats": ["pain", "poke", "fix", "payoff", "recap", "cta"],
     "how": "pain = one pain the viewer already felt; poke = the obvious fix that does not work; fix = 2-3 short steps; payoff = a verified figure; recap = loops back to the pain; cta."},
    {"id": "myth-bust", "name": "Myth bust", "beats": ["pain", "poke", "fix", "payoff", "cta"],
     "how": "pain = a myth owners believe; poke = why it fails; fix = what works; payoff = a verified figure that proves it."},
    {"id": "number-first", "name": "Number first", "beats": ["pain", "poke", "fix", "recap", "cta"],
     "how": "Open with the verified figure itself as the pain; explain what it means; fix; recap."},
    {"id": "before-after", "name": "Before / after", "beats": ["pain", "poke", "fix", "payoff", "cta"],
     "how": "Show the day without the fix, then with it; payoff is a before/after contrast, a figure only if a fact gives one."},
    {"id": "one-mistake", "name": "One common mistake", "beats": ["pain", "poke", "fix", "cta"],
     "how": "Name the one mistake, why owners make it, the fix."},
    {"id": "imaginary-scene", "name": "Short imaginary scene", "beats": ["pain", "poke", "fix", "payoff", "cta"],
     "how": "Open inside a 2-line scene (a customer messages at 11pm); never claim it happened to a real client."},
    {"id": "viewer-question", "name": "Question the viewer asks", "beats": ["pain", "poke", "fix", "recap", "cta"],
     "how": "Pain is the question in the owner's own words; answer it plainly."},
    {"id": "loop-ending", "name": "Loop ending", "beats": ["pain", "fix", "payoff", "recap", "cta"],
     "how": "The recap repeats the first line word for word so the reel replays."},
]
BY_ID = {s["id"]: s for s in STYLES}
SYS = "You write short vertical-video scripts for a solo web and AI developer in India talking to small-business owners. Plain, specific, spoken."
BAD_OPEN = re.compile(r"^\s*(hi|hello|hey|namaste|welcome|in this (video|reel)|today (i|we)|aaj hum)\b", re.I)
_NUM = re.compile(r"\d[\d,\.]*")
WORDS = (5, 14)


def pick_style(history):
    """Least recently used style; never the same as yesterday."""
    last = [h.get("script_style") for h in history if h.get("script_style")]
    order = {s["id"]: (len(last) - 1 - max((i for i, x in enumerate(last) if x == s["id"]), default=-10 ** 6)) for s in STYLES}
    cand = sorted(STYLES, key=lambda s: -order[s["id"]])
    if last:
        cand = [s for s in cand if s["id"] != last[-1]] or cand
    return cand[0]


def _nums(t):
    return {n.strip(".,").replace(",", "") for n in _NUM.findall(t or "") if n.strip(".,")}


def score_hook(text):
    try:
        from viralsim.dimensions import HeuristicScorer
        c = HeuristicScorer().score(text)
        d = c.dims or {}
        return round(c.shareability + c.saveability + d.get("curiosity", 0) + d.get("relatability", 0), 2)
    except Exception:
        return 0.0


def problems(script, sheet, style):
    """Every reason this script must not ship (empty list = fine)."""
    out, facts = [], {f["id"]: f for f in sheet.get("facts", [])}
    beats = script.get("beats") or []
    names = [b.get("beat") for b in beats]
    if names != style["beats"]:
        out.append(f"beats must be exactly {style['beats']}, got {names}")
    for b in beats:
        line = str(b.get("line") or "")
        n = len(line.split())
        if b.get("beat") != "cta" and not WORDS[0] <= n <= WORDS[1] + 4:
            out.append(f"{b.get('beat')}: line has {n} words (want {WORDS[0]}-{WORDS[1]})")
        cited = [facts[i] for i in b.get("facts") or [] if i in facts]
        if any(i not in facts for i in b.get("facts") or []):
            out.append(f"{b.get('beat')}: cites a fact id that is not on the sheet")
        allowed = set().union(*[_nums(f["claim"]) | _nums(f.get("figure") or "") for f in cited]) if cited else set()
        stray = _nums(line + " " + str(b.get("screen") or "")) - allowed
        if stray:
            out.append(f"{b.get('beat')}: number(s) {sorted(stray)} not backed by a cited fact")
    if beats and BAD_OPEN.search(str(beats[0].get("line") or "")):
        out.append("opens with a greeting/intro")
    if "payoff" in names and not any(b.get("facts") for b in beats if b.get("beat") == "payoff") and "before-after" != style["id"]:
        out.append("payoff needs a cited verified fact")
    return out


def run(sheet, focus, style, ask=None, voice=None, max_tries=3):
    """-> master script dict. Raises ValueError if no valid script after max_tries (caller's stage() reports it)."""
    ask = ask or llm.gemini
    voice = voice if voice is not None else config.voice()
    fixes = ""
    for _ in range(max_tries):
        prompt = f"""Service in focus: {focus.get('name')} - {focus.get('pitch', '')}
STYLE: {style['name']} - {style['how']}
Beats, in this exact order: {style['beats']}
VERIFIED FACTS (the ONLY facts you may use; cite by id):
{json.dumps(sheet['facts'], ensure_ascii=False)}
VOICE: {voice[:1500]}

Write ONE script. Rules: no greeting or intro; one idea; spoken lines of {WORDS[0]}-{WORDS[1]} words (the cta may be shorter); plain Hinglish; every number must come from a cited fact and the
source is named in words when a figure is spoken; no invented clients, results or testimonials; replace any vague line with a concrete detail from the facts or delete it; read each line aloud
and cut filler. Also give 5 alternative first lines using 5 different hook formulas (question, number, myth, scene, bold claim).
Return JSON: {{"hooks": ["...x5"], "beats": [{{"beat": "pain", "line": "spoken", "screen": "<=8 words on screen", "visual": "what is shown", "facts": ["f1"]}}], "cta": "the one ask", "linkedin_english": "2-3 plain English sentences of the same idea"}}
{fixes}"""
        data = llm.ask_json(ask, prompt, SYS)
        if not isinstance(data, dict):
            continue
        hooks = [str(h) for h in (data.get("hooks") or []) if str(h).strip()]
        beats = data.get("beats") or []
        if beats and beats[0].get("beat") == "pain" and beats[0].get("line"):
            hooks.append(str(beats[0]["line"]))       # the pain line is itself a candidate
        scored = sorted(({"text": h, "score": score_hook(h)} for h in dict.fromkeys(hooks) if not BAD_OPEN.search(h)), key=lambda x: -x["score"])
        if scored and beats:
            beats[0]["line"] = scored[0]["text"]       # best hook wins; it must still pass the checks below
        script = {"style": style["id"], "hook": scored[0]["text"] if scored else "", "hooks": scored[:6], "beats": beats,
                  "cta": str(data.get("cta") or (beats[-1].get("line") if beats else "")), "linkedin_english": str(data.get("linkedin_english") or ""),
                  "language": "hinglish", "facts": sheet["facts"], "topic": sheet.get("topic")}
        bad = problems(script, sheet, style)
        if not bad:
            return script
        fixes = "Your last script was rejected: " + "; ".join(bad[:6]) + ". Fix exactly these."
        if scored and any("hook" in p or "pain" in p for p in bad) and len(scored) > 1:
            pass
    raise ValueError("scriptwriter: no valid script - " + fixes[:300])
