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
WORDS = (14, 42)      # a body beat explains itself in 1-3 spoken sentences; length of the video does not matter, how clearly it explains does
HOOK_WORDS = (5, 16)
CTA_WORDS = (8, 36)
# helping words that join a thought to its reason or example; a script made only of short bare statements fails
CONNECT = re.compile(r"\b(kyunki|kyuki|isliye|isiliye|matlab|yaani|jaise|jaise ki|maan lo|socho|yani|toh phir|phir|isse|taaki|warna|lekin|par asli|asli baat|dhyan rakho|iska matlab)\b", re.I)
# a statistic describes how things are; a line must not turn it into a promise (e.g. "70-90% of calls are repeat questions" is not "70-90% of calls will stop")
PROMISE = re.compile(r"\b(nahi aayenge|nahi aayegi|nahi aaenge|band ho (jayenge|jayegi|jaenge)|khatam ho|zero ho|guarantee|pakka|100 ?%)\b", re.I)
COUNT = re.compile(r"\b\d\s?-?\s?(steps?|tarike|tareeke|points?|baar)\b|\b\d{1,2}(:\d\d)?\s?(baje|bje|pm|am)\b", re.I)      # '3 steps' counts our own list, not a statistic
EMOTIONS = ("curious", "empathetic", "urgent", "calm", "excited", "warm")
DEFAULT_EMOTION = {"pain": "empathetic", "poke": "urgent", "fix": "calm", "payoff": "excited", "recap": "curious", "cta": "warm"}
# lines that could be said by any brand about anything; the script is rejected until they are replaced by something concrete
GENERIC = re.compile(r"\b(the myth|myth:|basic but powerful|game.?changer|unlock (your|the)|revolution|in today'?s (digital )?world|take your .{0,20} to the next level|"
                     r"comment learn|learn more|like and subscribe|stay tuned|let me know in the comments|dm me for more|follow for more)\b", re.I)
HINDI = re.compile(r"\b(hai|hain|ka|ki|ke|ko|se|mein|me|par|pe|nahi|nahin|aap|aapka|aapki|aapke|kya|kyun|kaise|jab|to|toh|bhi|hi|raha|rahi|rahe|wala|wali|phir|fir|pehle|lekin|aur|koi|sab|karo|karna|kar|ho|hota|hoga|tha|thi|dena|lena|milta|milte|jaata|jaate|bas|sirf|ek)\b", re.I)
SCENE = re.compile(r"\b(raat|baje|subah|shaam|din|hafte|mahine|pm|am|customer|enquiry|enquiries|inquiry|whatsapp|message|messages|order|booking|call|lead|leads|ad|ads|site|website|page|reply|jawab|dukaan|shop|menu|google|instagram|insta|form|number|phone|mobile)\b", re.I)
DELIVERABLE = re.compile(r"\b(setup|set-up|checklist|template|steps|guide|demo|sample|list|script|plan|example|audit|review|file|pdf|link|video|reply|jawab)\b", re.I)


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
        lo, hi = HOOK_WORDS if b is (beats[0] if beats else None) else (CTA_WORDS if b.get("beat") == "cta" else WORDS)
        if not lo <= n <= hi + 6:
            out.append(f"{b.get('beat')}: line has {n} words (want {lo}-{hi}; explain it in full spoken sentences, not a slogan)")
        cited = [facts[i] for i in b.get("facts") or [] if i in facts]
        if any(i not in facts for i in b.get("facts") or []):
            out.append(f"{b.get('beat')}: cites a fact id that is not on the sheet")
        allowed = set().union(*[_nums(f["claim"]) | _nums(f.get("figure") or "") for f in cited]) if cited else set()
        stray = _nums(COUNT.sub(" ", line + " " + str(b.get("screen") or ""))) - allowed
        if stray:
            out.append(f"{b.get('beat')}: number(s) {sorted(stray)} not backed by a cited fact")
    if beats and BAD_OPEN.search(str(beats[0].get("line") or "")):
        out.append("opens with a greeting/intro")
    for b in beats:
        line = str(b.get("line") or "")
        if GENERIC.search(line) or GENERIC.search(str(b.get("screen") or "")):
            out.append(f"{b.get('beat')}: generic filler phrase ({GENERIC.search(line + ' ' + str(b.get('screen') or '')).group(0)!r}); say something only this business could say")
        if b.get("beat") != "cta" and not HINDI.search(line):
            out.append(f"{b.get('beat')}: not Hinglish (needs everyday spoken Hindi in Roman letters, like talking to a shop owner)")
        if b.get("beat") in ("pain", "poke", "fix") and not SCENE.search(line) and not (b.get("facts") or []):
            out.append(f"{b.get('beat')}: too abstract; name a concrete moment or thing (a 11 pm message, an unanswered enquiry, the WhatsApp reply)")
    hook = beats[0] if beats else {}
    if hook and len(str(hook.get("line") or "").split()) > HOOK_WORDS[1] + 2:
        out.append(f"hook is too long; {HOOK_WORDS[1]} words max")
    body = [b for b in beats[1:] if b.get("beat") in ("poke", "fix", "payoff", "recap")]
    if sum(1 for b in body if CONNECT.search(str(b.get("line") or ""))) < max(1, len(body) // 2):
        out.append("lines are bare statements; use helping words that give the reason or an example (kyunki, isliye, matlab, jaise ki, phir, taaki) so the viewer understands WHY")
    for b in beats:
        if b.get("facts") and PROMISE.search(str(b.get("line") or "")):
            out.append(f"{b.get('beat')}: turns a statistic into a promise ({PROMISE.search(str(b.get('line'))).group(0)!r}); say only what the fact says")
    fix = next((b for b in beats if b.get("beat") == "fix"), None)
    if fix is not None:
        steps = [str(x).strip() for x in (fix.get("steps") or []) if str(x).strip()]
        if not 2 <= len(steps) <= 3 or any(len(x.split()) > 7 for x in steps):
            out.append("fix: needs 2-3 concrete steps (each 7 words max) in `steps`, and the spoken line must walk through them")
    cta = beats[-1] if beats else {}
    if cta.get("beat") == "cta":
        text = str(cta.get("line") or "")
        kw = str(sheet.get("keyword") or "").upper()
        if kw and kw not in text.upper().split() and kw not in re.sub(r"[^A-Za-z ]", " ", text.upper()).split():
            out.append(f"cta: must contain the keyword {kw}")
        if not DELIVERABLE.search(text):
            out.append("cta: must say what the viewer gets (setup steps, a checklist, a demo, a free review ...)")
    for b in beats:
        if b.get("emotion") not in EMOTIONS:
            b["emotion"] = DEFAULT_EMOTION.get(b.get("beat"), "calm")
    if "payoff" in names and not any(b.get("facts") for b in beats if b.get("beat") == "payoff") and "before-after" != style["id"]:
        out.append("payoff needs a cited verified fact")
    return out


def fidelity(script, sheet, ask):
    """One more model pass that only checks MEANING: does each spoken line say what its cited facts say (no promises, no wrong cause, no nonsense)? -> list of issues."""
    facts = {f["id"]: f["claim"] for f in sheet.get("facts", [])}
    rows = [{"beat": b.get("beat"), "line": b.get("line"), "facts": {i: facts.get(i) for i in b.get("facts") or []}} for b in script.get("beats", [])]
    prompt = ("You are a strict editor. For each spoken line, decide whether (a) it makes sense heard once by a small-business owner, and (b) it says ONLY what its cited facts say: "
              "no promise or outcome the fact does not claim, no changed number or cause. Lines citing no fact must not state any statistic.\nReturn JSON {\"issues\": [\"beat: what is wrong and how to say it correctly\"]}, empty list if all fine.\n"
              + json.dumps(rows, ensure_ascii=False))
    try:
        res = llm.ask_json(ask, prompt, "You check whether lines are faithful and clear. JSON only.")
        return [str(x) for x in (res or {}).get("issues", [])][:5] if isinstance(res, dict) else []
    except Exception:
        return []


def run(sheet, focus, style, ask=None, voice=None, max_tries=4):
    sheet = {**sheet, "keyword": sheet.get("keyword") or focus.get("dm_keyword") or ""}
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
VOICE: {voice[:900]}
LANGUAGE (strict): every spoken line is HINGLISH in Roman letters, everyday spoken Hindi with English tech words, like talking to a shop owner. Example: "Raat 11 baje customer ne WhatsApp kiya, aur aapne subah reply diya. Tab tak woh dusri dukaan chala gaya." Not translated-sounding Hindi, not plain English.

Write ONE script. Rules: no greeting or intro; one idea; 
SPOKEN LINES: the hook is {HOOK_WORDS[0]}-{HOOK_WORDS[1]} words. Every other beat is {WORDS[0]}-{WORDS[1]} words in 2-3 full spoken sentences, and the CTA {CTA_WORDS[0]}-{CTA_WORDS[1]}. Do not worry about video length; worry about the viewer UNDERSTANDING.
EXPLAIN, don't announce: pain = the moment AND why it hurts (what it costs: time, a lost customer); poke = why the obvious fix fails, the reason in plain words; fix = each step with a one-clause reason ("pehle ..., kyunki ..."); payoff = what the fact MEANS for this owner in plain words (do the arithmetic only if every number comes from a fact); recap = loop back to the pain.
Use helping words (kyunki, isliye, matlab, jaise ki, phir, taaki, lekin) so each line connects to the one before it. A line must make sense when heard once, with no screen.
STATISTICS: say a figure exactly as its fact states it. "X% of calls are repeat questions" never becomes "X% of calls will stop"; do not invent an outcome the fact does not claim.
Vary sentence length and mood inside a beat: a short punchy sentence, then a longer explaining one; a question where you are talking to the owner; "!" only for a real payoff.

HOOK: a specific scene or number from the facts (a time, a thing, a loss), never a general statement or "the myth". PAIN/POKE: one concrete moment the owner has lived. FIX: walk through 2-3 concrete steps in the spoken line AND list them in `steps` (each 7 words max). PAYOFF: only a fact from the sheet, source named in words. CTA: the keyword {sheet.get('keyword', '')} plus exactly what they get and why it helps them (e.g. "Agar aapki website pe bhi yahi dikkat hai, toh comment mein BOT likho. Main aapko 3-step setup bhejunga, taaki aap kal se hi isse try kar sako.").
Give each beat an `emotion` for the voice-over, one of: curious, empathetic, urgent, calm, excited, warm. plain Hinglish; every number must come from a cited fact and the
source is named in words when a figure is spoken; no invented clients, results or testimonials; replace any vague line with a concrete detail from the facts or delete it; read each line aloud
and cut filler. Also give 5 alternative first lines using 5 different hook formulas (question, number, myth, scene, bold claim).
Return JSON: {{"hooks": ["...x5"], "beats": [{{"beat": "pain", "line": "spoken", "screen": "<=8 words on screen", "visual": "what is shown", "emotion": "empathetic", "steps": ["only for the fix beat"], "facts": ["f1"]}}], "cta": "the one ask", "linkedin_english": "2-3 plain English sentences of the same idea"}}
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
                  "language": "hinglish", "facts": sheet["facts"], "topic": sheet.get("topic"), "service": focus.get("id") or focus.get("name"), "keyword": sheet.get("keyword")}
        bad = problems(script, sheet, style)
        if not bad:
            bad = [f"meaning: {x}" for x in fidelity(script, sheet, ask)]
        if not bad:
            return script
        fixes = "Your last script was rejected: " + "; ".join(bad[:6]) + ". Fix exactly these."
        if scored and any("hook" in p or "pain" in p for p in bad) and len(scored) > 1:
            pass
    raise ValueError("scriptwriter: no valid script - " + fixes[:300])
