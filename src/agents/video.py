"""Agent 4b: 30-second reel as THREE 10-second Google Flow clips, written in the owner's own film style (config/reel_style.json).
One outline call plans the whole reel (hook, one voiceover line and one end frame per clip), then one call per clip writes the beat
sheet and the paste-ready Flow paragraph. The look (lens, light, desk, laptop) is constant and added by code, so the three clips match;
only the story objects change per service. Runs on Groq for now (gemma is too small for detailed prompts)."""
import re
from .. import config, ideas, llm

TIMES = ["0-10s", "10-20s", "20-30s"]
FPS = 60
BANNED = re.compile(r"(₹|\bINR\b|\bRs\.?\s?\d|%|\bprice[sd]?\b|\bcost[s]?\b|\bguarantee|\bfree\b|\b\d+\s*(days?|hours?|minutes?|weeks?|x)\b|[ऀ-ॿ])", re.I)


def style():
    return config.load_json(config.ROOT / "config" / "reel_style.json", {})


def kit(st, service_id):
    sv = st.get("services", {})
    return {**sv.get("_default", {}), **sv.get(service_id, {})}


def keyword(service_id):
    for s in config.services().get("services", []):
        if s["id"] == service_id:
            return s.get("dm_keyword", "")
    return ""


def words(s):
    return len((s or "").split())


def header(st, kt, i):
    """The constant film look, added by code to every clip so the three clips match."""
    w = st["world"]
    look = st["film_look"].replace("{lens}", st["lenses"][min(i, len(st["lenses"]) - 1)])
    return (f"Generate a 10-second vertical 9:16 video, {look}. Set on {w['desk']}, with {w['laptop']} showing {kt['screen']}, "
            f"{w['lamp']}, {w['air']}. {w['emblem'].capitalize()}. {st['light_turn']}")


def outline(plan, focus, hook, guidance, st, kt, kw):
    acts = "\n".join(f"- {a['time']} {a['name']}: {a['beats']}" for a in st["acts"])
    prompt = f"""Plan a 30-second vertical reel for: {plan['topic']} (service: {focus['name']}).
Hook: {hook}
Strategist note: {guidance}

REEL RULES (from vidIQ public guidance; they override anything below that is weaker):
{ideas.rules_text()}

Google Flow generates ONE 10-second clip per prompt, so the reel is THREE clips (0-10s, 10-20s, 20-30s) that continue one another. You plan only the outline now.
The film world is fixed: {kt['screen']}, a person seen only as hands or a reflection. The story object for this service: {kt['metaphor']}. Closing action: {kt['closing_action']}.
Act plan:
{acts}

- hook_first_3s: on-screen text (3-7 words, top third) + spoken line (5-10 words). The visual payoff appears in the FIRST SECOND.
- Clip 1 spoken line: a specific problem or result in 12 words or fewer (no greeting, no brand intro).
- Clip 2: how it works or the proof, one idea.
- Clip 3: the result plus ONE next step, spoken naturally: DM the word {kw}. The very last frame hands back to the opening (for example it ends on the question the first line answers) so a replay feels natural.
- Every spoken line: 25 words or fewer so it fits in 10 seconds, simple English or light Hinglish in Roman letters. No prices, timeframes, results or guarantees.
- end_frame: one sentence describing the exact last frame of the clip, so the next clip can open from it.
Return JSON: {{"hook_first_3s": "...", "parts": [{{"goal": "...", "voiceover": "...", "end_frame": "...", "audio_motif": "..."}}, {{"goal": "...", "voiceover": "...", "end_frame": "...", "audio_motif": "..."}}, {{"goal": "...", "voiceover": "...", "end_frame": "...", "audio_motif": "..."}}]}}"""
    out = llm.ask_json(llm.groq, prompt, "You write short, honest, non-salesy reel scripts for Google Flow.")
    parts = (out.get("parts") or [])[:3]
    while len(parts) < 3:
        parts.append({"goal": "", "voiceover": "", "end_frame": "", "audio_motif": ""})
    out["parts"] = parts
    return out


def clip_prompt(i, part, prev_end, outl, st, kt, kw, issues=""):
    last = i == 2
    ex = st["example_beat"]
    opens = ("It opens from the previous clip's last frame: " + prev_end) if prev_end else "It opens cold on the problem, with the first frame already moving (the FIRST SECOND carries the hook)."
    closes = (" This final frame hands back to the opening of the reel and leaves clean empty space for the DM keyword " + kw + ".") if last else ""
    fix = ("\nFIX THESE PROBLEMS FROM YOUR LAST TRY: " + issues) if issues else ""
    return f"""Write clip {i + 1} of 3 of a 30-second film, in the exact style of the example. Google Flow makes this clip alone, so describe every element: subject, objects, materials, light, colour temperature, lens, camera move, sound.

FILM STYLE (fixed, do not change it): {header(st, kt, i)}
Story object: {kt['metaphor']}. Hero prop: {kt['hero_prop']}.
This clip ({TIMES[i]}): {st['acts'][i]['name']}. Goal: {part.get('goal')}. Beats to cover: {st['acts'][i]['beats']}.
Spoken line (voiceover, exact words, do not change): "{part.get('voiceover')}"
{opens}
It ends on this frame: {part.get('end_frame')}.{closes}
Audio motif: {part.get('audio_motif')}. {st['audio']['timeline']} Voiceover tone: {st['audio']['voiceover']}.
Camera moves to choose from: {', '.join(st['camera_moves'])}. Textures: {', '.join(st['texture'])}.

RULES:
{chr(10).join('- ' + r for r in st['rules'])}

EXAMPLE of one beat (style only, never copy it):
{ex}

Write 8-10 beats that cover 0-10 seconds without gaps. Each beat: "start" and "end" in whole seconds of THIS clip (0-10), "visual" (30-60 words, every element named), "feel" (ONE short Roman-script Hinglish line), "camera" (lens, aperture, move), "audio" (what is heard at that moment).
Then write "paste": 4 or 5 items {{"start", "end", "text"}} for the paste version: each text is 30-60 words of continuous visual direction (camera, subject, light, on-screen UI) with no labels, covering 0-10 seconds without gaps.
Then "sync": ONE line: when the voiceover starts and ends, the sound under it, and what the viewer sees at that moment.
Return JSON: {{"beats": [{{"start": 0, "end": 1, "visual": "...", "feel": "...", "camera": "...", "audio": "..."}}], "paste": [{{"start": 0, "end": 3, "text": "..."}}], "sync": "..."}}{fix}"""


def check(c, part, last, kw):
    bad = []
    beats, paste = c.get("beats") or [], c.get("paste") or []
    if not 6 <= len(beats) <= 11:
        bad.append(f"{len(beats)} beats (need 8-10)")
    for b in beats:
        if words(b.get("visual")) < 20 or not (b.get("feel") and b.get("camera") and b.get("audio")):
            bad.append(f"beat {b.get('start')}-{b.get('end')} is too thin: visual 30-60 words and feel, camera, audio all present")
            break
    if not 3 <= len(paste) <= 6 or any(words(p.get("text")) < 25 for p in paste):
        bad.append("paste version needs 4-5 items of 30-60 words each")
    if not (c.get("sync") or "").strip():
        bad.append("sync line missing")
    if words(part.get("voiceover")) > 25:
        bad.append("voiceover over 25 words")
    blob = " ".join([str(c.get("sync", ""))] + [str(b.get(k, "")) for b in beats for k in ("visual", "feel", "camera", "audio")] + [str(p.get("text", "")) for p in paste])
    m = BANNED.search(blob)
    if m:
        bad.append(f"banned word or number '{m.group(0)}' (no prices, timeframes, results, guarantees or Hindi script)")
    return bad


def render(c, part, i, st, kt):
    """Beat sheet + paste paragraph + sync line, formatted the way the owner writes them."""
    t0 = i * 10
    lines = [f"CLIP {i + 1}/3 | {TIMES[i]} | {st['acts'][i]['name']}", ""]
    for n, b in enumerate(c["beats"], 1):
        s, e = int(b.get("start", 0)), int(b.get("end", 0))
        lines += [f"Beat {n} | 00:{s:02d}-00:{e:02d} | frames {s * FPS}-{e * FPS} | Story {t0 + s}-{t0 + e}s",
                  f"Visual: {b['visual'].strip()}", f"Story Feel: {b['feel'].strip()}",
                  f"Camera & Lens: {b['camera'].strip()}", f"Audio Cue: {b['audio'].strip()}", ""]
    lines.append(f"Audio & Voiceover Sync: {c['sync'].strip()}")
    paste = [header(st, kt, i)]
    for p in c["paste"]:
        s, e = int(p.get("start", 0)), int(p.get("end", 0))
        paste.append(f"[00:{s:02d}-00:{e:02d} / Story {t0 + s}-{t0 + e}s] {p['text'].strip()}")
    paste.append(f"Audio & Voiceover Sync: {c['sync'].strip()} Voiceover: \"{part.get('voiceover', '').strip()}\"")
    return "\n".join(lines).strip(), "\n\n".join(paste)


def run(plan, focus, posts, guidance=""):
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    st, kt, kw = style(), kit(style(), focus.get("id", "")), keyword(focus.get("id", ""))
    outl = outline(plan, focus, hook, guidance, st, kt, kw)
    out_parts, issues_all, prev_end = [], [], ""
    for i, part in enumerate(outl["parts"]):
        issues = ""
        for attempt in (0, 1):
            c = llm.ask_json(llm.groq, clip_prompt(i, part, prev_end, outl, st, kt, kw, issues), "You write detailed, concrete film direction for Google Flow.")
            bad = check(c, part, i == 2, kw)
            if not bad:
                break
            issues = "; ".join(bad)
        if bad and any("banned" in b for b in bad):
            raise ValueError(f"reel clip {i + 1} still has banned content: {issues}")
        if not c.get("beats") or not c.get("paste"):
            raise ValueError(f"reel clip {i + 1} came back without beats or a paste version")
        issues_all += [f"clip {i + 1}: {b}" for b in bad]
        sheet, paste = render(c, part, i, st, kt)
        out_parts.append({"time": TIMES[i], "voiceover": part.get("voiceover", ""), "flow_prompt": paste, "beat_sheet": sheet, "sync": c.get("sync", "")})
        prev_end = part.get("end_frame", "")
    return {"hook_first_3s": outl.get("hook_first_3s", ""), "continuity": header(st, kt, 0), "parts": out_parts,
            "voiceover": " ".join(p["voiceover"] for p in out_parts).strip(), "dm_keyword": kw, "issues": issues_all}
