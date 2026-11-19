"""Master scriptwriter: ONE script per day, written only from the verified fact sheet. The carousel and the video both read it.

Output: {"style", "hook", "hooks": [5 candidates with scores], "beats": [{"beat","line","screen","visual","facts"}], "cta", "language"}.
Code enforces what a model drifts on: every number must come from a cited fact, 5-14 words per spoken line, no greeting/intro, hook scored and picked by code."""
import json
import re
import datetime
from .. import config, contentskills, llm, marketingskills, scriptlessons

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
# LENGTH BUDGET: a reel's viewers are gone by second 5 and almost nobody reaches 60 s (a 65 s reel kept ~0% after the first 10 s). Spoken Hinglish runs ~2.9 words/s, so
# TOTAL_WORDS = 85 is a ~30 s reel. Short is not weak: every beat keeps ONE concrete idea plus its reason, nothing is cut by machine; an over-long script is sent back to the
# model with per-beat "tighten to N words" feedback (see budget_problems), and the content/meaning checks still run on the tightened script.
WORDS = (10, 22)      # a body beat: 1-2 spoken sentences, one concrete idea and its reason
HOOK_WORDS = (5, 13)
CTA_WORDS = (8, 20)
TOTAL_WORDS = (52, 85)   # whole spoken script: ~18-30 seconds
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


def budget_problems(beats) -> list[str]:
    """Whole-script length: too long -> per-beat 'tighten to N words' on the longest body beats (the model rewrites them, nothing is cut by machine);
    too short -> the script is thin (a weak reel), so name the beat to enrich."""
    counts = [(b.get("beat"), len(str(b.get("line") or "").split())) for b in beats]
    total = sum(n for _, n in counts)
    lo, hi = TOTAL_WORDS
    out = []
    if total > hi:
        over = total - hi
        body = sorted(((n, name) for i, (name, n) in enumerate(counts) if i > 0 and name != "cta" and n > WORDS[0] + 2), reverse=True) or sorted(((n, name) for i, (name, n) in enumerate(counts) if i > 0), reverse=True)
        cut = {}
        while over > 0 and body:
            body.sort(reverse=True)
            n, name = body[0]
            cut[name] = cut.get(name, 0) + 1
            body[0] = (n - 1, name)
            over -= 1
            if body[0][0] <= WORDS[0]:
                body.pop(0)
        by = {name: n for name, n in counts}
        for name, c in cut.items():
            out.append(f"{name}: script is {total} words, the reel must stay under {hi} (about 30 seconds); tighten this beat from {by[name]} to {by[name] - c} words max, keep its concrete detail and its reason, cut filler and repeats")
    elif beats and total < lo:
        out.append(f"{beats[min(1, len(beats) - 1)].get('beat')}: script is only {total} words (min {lo}); the reel is too thin, add one concrete detail and its reason")
    return out


def problems(script, sheet, style, focus=None):
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
        if not lo <= n <= hi + 3:
            out.append(f"{b.get('beat')}: line has {n} words (want {lo}-{hi}; explain it in full spoken sentences, not a slogan)")
        cited = [facts[i] for i in b.get("facts") or [] if i in facts]
        if any(i not in facts for i in b.get("facts") or []):
            out.append(f"{b.get('beat')}: cites a fact id that is not on the sheet")
        allowed = set().union(*[_nums(f["claim"]) | _nums(f.get("figure") or "") for f in cited]) if cited else set()
        allowed |= _nums(capabilities(focus))                  # '24x7' / '24 hours' is a listed capability of the service, so it is backed
        stray = _nums(COUNT.sub(" ", line + " " + str(b.get("screen") or ""))) - allowed
        if stray:
            out.append(f"{b.get('beat')}: number(s) {sorted(stray)} not backed by a cited fact")
    out += budget_problems(beats)
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
            out.append("cta: must say what the viewer gets (how the setup works step by step, or honest advice on whether it fits; never a demo or sample)")
    for b in beats:
        if b.get("emotion") not in EMOTIONS:
            b["emotion"] = DEFAULT_EMOTION.get(b.get("beat"), "calm")
    if "payoff" in names and not any(b.get("facts") for b in beats if b.get("beat") == "payoff") and "before-after" != style["id"]:
        out.append("payoff needs a cited verified fact")
    return out


def capabilities(focus) -> str:
    """What the service in focus really does (config/services.json), as one string for the writer and the meaning check."""
    f = focus or {}
    return "; ".join([str(f.get("pitch") or f.get("name") or "")] + [str(c) for c in f.get("capabilities") or []]).strip("; ")


def fidelity(script, sheet, ask, focus=None):
    """One more model pass that only checks MEANING against the WHOLE fact sheet. Flags only: a number or cause that contradicts or changes a fact, an outcome promised that no fact claims,
    a source or brand named that no fact names, or a line that is unintelligible. Plain-language explanation of WHY (common sense, no new figure) is allowed. -> list of issues."""
    facts = {f["id"]: f"{f['claim']} (source: {f.get('source')})" for f in sheet.get("facts", [])}
    rows = [{"beat": b.get("beat"), "line": b.get("line"), "cites": b.get("facts") or []} for b in script.get("beats", [])]
    prompt = ("You are an editor checking spoken lines against ALL verified facts. Flag a line ONLY if: (1) it changes or contradicts a number or cause stated in a fact; (2) it promises an outcome "
              "no fact claims AND is not a capability of the service in focus (e.g. 'calls will stop'; but 'the customer does not have to wait' is a true capability of an instant-reply chatbot and is FINE); (3) it names a company, person or study that no fact names; (4) it is unintelligible when heard once. "
              "Do NOT flag plain-language explanations, examples or reasons that add no figure or name, and do NOT flag plain statements of what the service does (see SERVICE CAPABILITIES): "
              "those are true even when no fact repeats them. Flag only invented figures, guaranteed sales/revenue results, named clients or testimonials, and contradictions of a fact. Each issue must say exactly how to fix it.\n"
              "SERVICE CAPABILITIES (true, may be stated): " + capabilities(focus) + "\n"
              "Return JSON {\"issues\": [\"beat: problem and the exact fix\"]}, empty if fine.\nFACTS: " + json.dumps(facts, ensure_ascii=False) + "\nLINES: " + json.dumps(rows, ensure_ascii=False))
    try:
        res = llm.ask_json(ask, prompt, "You check whether lines are faithful and clear. JSON only.")
        return [str(x) for x in (res or {}).get("issues", [])][:4] if isinstance(res, dict) else []
    except Exception:
        return []


def repair_missing(script, style, ask, focus, sheet):
    """The model sometimes stops one beat early (no `cta`). Instead of throwing the whole script away, ask for ONLY the missing beat(s), in the voice of the beats already written."""
    have = {b.get("beat"): b for b in script.get("beats") or [] if isinstance(b, dict)}
    miss = [n for n in style["beats"] if n not in have]
    if not miss or len(miss) > 2 or any(n not in style["beats"] for n in have):
        return script
    rows = [{"beat": n, "line": have[n].get("line")} for n in style["beats"] if n in have]
    kw = sheet.get("keyword") or ""
    prompt = (f"A short-video script for {focus.get('name')} is missing its beat(s) {miss}. Existing beats, in order: {json.dumps(rows, ensure_ascii=False)}\n"
              f"Write ONLY the missing beat(s), continuing in the same Hinglish voice (Roman letters, everyday spoken Hindi). A normal beat is {WORDS[0]}-{WORDS[1]} words in 1-2 spoken sentences; "
              f"the cta is {CTA_WORDS[0]}-{CTA_WORDS[1]} words, ONE ask only: tell the viewer to send the word {kw or 'the keyword'} and say exactly what they get (how the setup would work, or honest advice on whether it fits; never a demo or sample). "
              f"No numbers except 3 steps style counts. Return JSON {{\"beats\": [{{\"beat\": \"{miss[0]}\", \"line\": \"spoken\", \"screen\": \"<=8 words\", \"visual\": \"what is shown\", \"emotion\": \"warm\", \"facts\": []}}], \"cta\": \"the one ask if cta is missing\"}}")
    try:
        data = llm.ask_json(ask, prompt, SYS)
        new = {b.get("beat"): b for b in (data or {}).get("beats", []) if isinstance(b, dict) and b.get("beat") in miss and b.get("line")}
    except Exception:
        return script
    if set(new) != set(miss):
        return script
    for b in new.values():
        b.setdefault("facts", [])
    script["beats"] = [have.get(n) or new[n] for n in style["beats"]]
    if "cta" in new:
        script["cta"] = str(new["cta"]["line"])
    return script


BEAT_RX = re.compile(r"\b(pain|poke|fix|payoff|recap|cta)\b")


def by_beat(bad, beats):
    """Split rejection reasons into {beat name: [reason, ...]}. Returns (per_beat, global_reasons): a reason that names no beat (or is about the whole script) is global."""
    names = [b.get("beat") for b in beats]
    per, glob = {}, []
    for p in bad:
        msg = re.sub(r"^(meaning|skills|marketing):\s*", "", p)
        head = msg.split(":", 1)[0] if ":" in msg else ""
        found = [n for n in BEAT_RX.findall(head) if n in names]
        if not found and re.match(r"(hook|opens with)", msg) and names:
            found = [names[0]]
        if not found or msg.startswith("beats must be"):
            glob.append(p)
            continue
        for n in found:
            per.setdefault(n, []).append(msg.split(":", 1)[1].strip() if ":" in msg else msg)
    return per, glob


def repair_beats(script, per, style, ask, focus, sheet, voice="", strict=False):
    """Ask for a rewrite of ONLY the beats that failed, with the exact reasons for each; every other beat stays word for word. -> (script, True if anything changed)."""
    beats = script.get("beats") or []
    have = {b.get("beat"): b for b in beats}
    targets = [n for n in style["beats"] if n in per and n in have]
    if not targets:
        return script, False
    facts = {f["id"]: f for f in sheet.get("facts", [])}
    ctx = [{"beat": n, "line": have[n].get("line"), "fixed": n not in targets} for n in style["beats"] if n in have]
    prompt = (f"Service: {focus.get('name')}. A short-video script was rejected. Rewrite ONLY the beat(s) {targets}; all other beats stay exactly as they are and are shown for context.\n"
              f"SCRIPT: {json.dumps(ctx, ensure_ascii=False)}\n"
              "WHAT IS WRONG (fix exactly these and nothing else):\n" + "\n".join(f"- {n}: " + " | ".join(per[n]) for n in targets) + "\n"
              f"RULES: Hinglish in Roman letters; a body beat is {WORDS[0]}-{WORDS[1]} words, the hook {HOOK_WORDS[0]}-{HOOK_WORDS[1]}, the cta {CTA_WORDS[0]}-{CTA_WORDS[1]} words; the cta asks for the ONE keyword "
              f"{sheet.get('keyword') or ''} and says what they get; every digit must come from a cited fact id (or be 24x7); capabilities you may state: {capabilities(focus)}. Never promise a result.\n"
              + ("STRICT MODE (earlier rewrites were still rejected): the line may ONLY restate what the cited fact says, in plain Hinglish, as a description of how things are. No prediction (no rahega/hoga/badhega), no outcome, no claim beyond the fact's own words.\n" if strict else "") +
              f"VERIFIED FACTS: {json.dumps(list(facts.values()), ensure_ascii=False)}\nVOICE: {voice[:500]}\n{scriptlessons.prompt_block(4)}"
              'Return JSON {"beats": [{"beat": "<name>", "line": "spoken", "screen": "<=8 words", "visual": "what is shown", "emotion": "warm", "steps": ["fix only: 2-3 strings of at most 7 words each, in the order the line says them"], "facts": ["ids"]}]} with ONLY the rewritten beats.')
    try:
        data = llm.ask_json(ask, prompt, SYS)
        new = {b.get("beat"): b for b in (data or {}).get("beats", []) if isinstance(b, dict) and b.get("beat") in targets and b.get("line")}
    except Exception:
        return script, False
    if not new:
        return script, False
    for n, b in new.items():
        b.setdefault("facts", have[n].get("facts") or [])
        b.setdefault("emotion", have[n].get("emotion") or DEFAULT_EMOTION.get(n, "warm"))
        have[n] = {**have[n], **b}
    script["beats"] = [have[n] for n in style["beats"] if n in have]
    script["hook"] = str(script["beats"][0].get("line") or script.get("hook") or "")
    if "cta" in new:
        script["cta"] = str(new["cta"]["line"])
    return script, True


def derive_steps(line: str) -> list[str]:
    """2-3 on-screen steps (7 words max each) taken from the fix line's OWN clauses, in order. [] when the line has fewer than two clauses."""
    parts = [p.strip(" ,.;:!?") for p in re.split(r"(?<=[.!?])\s+|,\s+|\s+(?:phir|fir|aur phir|uske baad|aur)\s+", str(line or ""), flags=re.I)]
    parts = [" ".join(p.split()[:7]) for p in parts if len(p.split()) >= 2]
    if len(parts) > 3:
        parts = [parts[0], parts[len(parts) // 2], parts[-1]]
    return parts if len(parts) >= 2 else []


def normalize_steps(script):
    """The fix beat's `steps` is display text only. When the model left it missing or too long, build it from the beat's own spoken clauses (nothing new is invented)
    instead of spending a rewrite round on it."""
    fix = next((b for b in script.get("beats") or [] if b.get("beat") == "fix"), None)
    if fix is None:
        return script
    steps = [str(x).strip() for x in (fix.get("steps") or []) if str(x).strip()]
    if not 2 <= len(steps) <= 3 or any(len(x.split()) > 7 for x in steps):
        fix["steps"] = derive_steps(fix.get("line")) or steps
    return script


def check_all(script, sheet, style, focus, ask):
    """Every check in order; the cheap deterministic ones first, model passes only when those are clean."""
    normalize_steps(script)
    bad = problems(script, sheet, style, focus) + marketingskills.script_problems(script, focus) + contentskills.problems(script)
    if not bad:
        bad = [f"meaning: {x}" for x in fidelity(script, sheet, ask, focus)]
    if not bad:
        bad = [f"skills: {x}" for x in contentskills.audit(script, ask)] + [f"marketing: {x}" for x in marketingskills.audit(script, focus, ask)]
    return bad


def run(sheet, focus, style, ask=None, voice=None, max_tries=4, repair_rounds=3):
    sheet = {**sheet, "keyword": sheet.get("keyword") or focus.get("dm_keyword") or ""}
    """-> master script dict. Raises ValueError if no valid script after max_tries (caller's stage() reports it)."""
    ask = ask or llm.gemini
    voice = voice if voice is not None else config.voice()
    fixes = ""
    today = sheet.get("date") or datetime.date.today().isoformat()
    for _ in range(max_tries):
        prompt = f"""Service in focus: {focus.get('name')} - {focus.get('pitch', '')}
STYLE: {style['name']} - {style['how']}
Beats, in this exact order: {style['beats']}
VERIFIED FACTS (the ONLY facts you may use; cite by id):
{json.dumps(sheet['facts'], ensure_ascii=False)}
VOICE: {voice[:900]}
LANGUAGE (strict): every spoken line is HINGLISH in Roman letters, everyday spoken Hindi with English tech words, like talking to a shop owner. Example: "Raat 11 baje customer ne WhatsApp kiya, aur aapne subah reply diya. Tab tak woh dusri dukaan chala gaya." Not translated-sounding Hindi, not plain English.

Write ONE script with EXACTLY {len(style['beats'])} beats, in this order: {style['beats']}. The LAST beat is `{style['beats'][-1]}`; never stop early and never drop it. Any digit you speak or put on screen (other than a clock time or an '3 steps' style count) must come from a cited fact or from the capabilities list below; otherwise say it in words with no digit. Rules: no greeting or intro; one idea; 
SPOKEN LINES: the hook is {HOOK_WORDS[0]}-{HOOK_WORDS[1]} words. Every other beat is {WORDS[0]}-{WORDS[1]} words in 1-2 full spoken sentences, and the CTA {CTA_WORDS[0]}-{CTA_WORDS[1]}. TOTAL budget for the whole script: {TOTAL_WORDS[0]}-{TOTAL_WORDS[1]} words (about 25-30 seconds: viewers leave by second 5, so the reel is SHORT). Short must not mean weak: one concrete idea per beat plus its reason, no filler, no repeating what the last beat said.
FIRST 8 SECONDS: the hook ends on an unfinished consequence or a question; the POKE (beat 2) must then give the first surprising, specific answer (a thing, a time, a cost) so there is a reason to keep watching; never spend beat 2 only restating the problem.
EXPLAIN, don't announce: pain = the moment AND why it hurts (what it costs: time, a lost customer); poke = why the obvious fix fails, the reason in plain words; fix = each step with a one-clause reason ("pehle ..., kyunki ..."); payoff = what the fact MEANS for this owner in plain words (do the arithmetic only if every number comes from a fact); recap = loop back to the pain.
Use helping words (kyunki, isliye, matlab, jaise ki, phir, taaki, lekin) so each line connects to the one before it. A line must make sense when heard once, with no screen.
CAPABILITIES: you may state what the service in focus does even when no fact says it, because it is true: {capabilities(focus)}. Never promise a business result (more sales, a number of leads).\nSTATISTICS: say a figure exactly as its fact states it. "X% of calls are repeat questions" never becomes "X% of calls will stop"; do not invent an outcome the fact does not claim.
Vary sentence length and mood inside a beat: a short punchy sentence, then a longer explaining one; a question where you are talking to the owner; "!" only for a real payoff.

HOOK: a specific scene or number from the facts (a time, a thing, a loss), never a general statement or "the myth". PAIN/POKE: one concrete moment the owner has lived. FIX: walk through 2-3 concrete steps in the spoken line AND list them in `steps` (each 7 words max). PAYOFF: only a fact from the sheet, source named in words. CTA: the keyword {sheet.get('keyword', '')} plus exactly what they get and why it helps them (e.g. "Agar aapki website pe bhi yahi dikkat hai, toh comment mein BOT likho. Main aapko 3-step setup bhejunga, taaki aap kal se hi isse try kar sako.").
Give each beat an `emotion` for the voice-over, one of: curious, empathetic, urgent, calm, excited, warm. plain Hinglish; every number must come from a cited fact and the
source is named in words when a figure is spoken; no invented clients, results or testimonials; replace any vague line with a concrete detail from the facts or delete it; read each line aloud
and cut filler. Also give 5 alternative first lines using 5 different hook formulas (question, number, myth, scene, bold claim).
Return JSON: {{"hooks": ["...x5"], "beats": [{{"beat": "pain", "line": "spoken", "screen": "<=8 words on screen", "visual": "what is shown", "emotion": "empathetic", "steps": ["only for the fix beat"], "facts": ["f1"]}}], "cta": "the one ask", "linkedin_english": "2-3 plain English sentences of the same idea"}}
{marketingskills.block('script', focus, today)}{contentskills.block('script')}{scriptlessons.prompt_block()}{fixes}"""
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
                  "marketing": {"keyword": marketingskills.cta_for(focus)["keyword"], "gets": marketingskills.cta_for(focus)["gets"], "pillar": marketingskills.pillar(today)}, "language": "hinglish", "facts": sheet["facts"], "topic": sheet.get("topic"), "service": focus.get("id") or focus.get("name"), "keyword": sheet.get("keyword")}
        script = repair_missing(script, style, ask, focus, sheet)
        bad = check_all(script, sheet, style, focus, ask)
        for _round in range(repair_rounds):                  # concrete feedback: rewrite ONLY the failing beats, keep the rest word for word
            if not bad:
                return script
            scriptlessons.record(bad)
            per, glob = by_beat(bad, script.get("beats") or [])
            if glob or not per:
                break                                        # a whole-script problem: only a fresh draft can fix it
            script, changed = repair_beats(script, per, style, ask, focus, sheet, voice)
            if not changed:
                break
            bad = check_all(script, sheet, style, focus, ask)
        if bad:                                              # last resort before a fresh draft: one strict rewrite that may only restate the facts
            per, glob = by_beat(bad, script.get("beats") or [])
            if per and not glob:
                script, changed = repair_beats(script, per, style, ask, focus, sheet, voice, strict=True)
                if changed:
                    bad = check_all(script, sheet, style, focus, ask)
        if not bad:
            return script
        scriptlessons.record(bad)
        fixes = "Your last script was rejected: " + "; ".join(bad[:6]) + ". Fix exactly these and keep everything else."
    raise ValueError("no valid script after targeted repairs - " + fixes[:300])
