"""Agent 4b: the 30-second reel as THREE 10-second Google Flow clips, written in the cinematic indie-film style of config/reel_style.json.

One planning call (the story and the three spoken lines), then one call per clip. Each clip is written twice from one structured answer:
  * the BEAT SHEET (the director's version): 8-10 beats of 1-2 seconds with frame numbers, each with Visual, Story Feel, Camera & Lens and Audio Cue;
  * the FLOW PROMPT (what is pasted into Google Flow): the same film header on every clip, 4 beats of 2-3 seconds, and one audio line with the voiceover.
The code, not the model, builds the header, the timestamps and the frame numbers, so the three clips always match. A clip that fails its checks twice
becomes a plain fallback clip, so the reel is never lost. The model is Groq (GPT-OSS 120B) through llm.prompt_writer, with Gemma as the fallback."""
import re

from .. import config, ideas, llm

TIMES = ["0-10s", "10-20s", "20-30s"]
FPS = 60
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
SYS = "You are a film director who writes short, honest, non-salesy reel scripts and exact, richly detailed prompts for Google Flow."

DEFAULT_FILM = {"genre": "non-commercial indie-film style cinematic micro-story", "brand": "AR Designs", "camera": "ARRI Alexa Mini LF",
                "capture": "4K resolution, 60fps", "stock": "Kodak Vision3 500T film emulation with rich halation",
                "lens": {"1": "100mm Macro Anamorphic lens", "2": "100mm Macro Anamorphic lens", "3": "50mm Anamorphic lens"},
                "opening": {"1": "A deeply relatable", "2": "Continuing the", "3": "The final act of a"}}
DEFAULT_WORLD = {"set": "a minimalist white workspace with a Nordic oak wood desk", "light": "a warm 3200K tungsten desk lamp casting soft diffused shadows",
                 "cold": "the cold blue glow of the laptop screen", "hero": "a Space Silver MacBook Pro", "screen": "a sleek dark-mode interface",
                 "props": "a matte-white architectural lamp", "texture": "brushed aluminium, glass reflections and dust motes in the lamp light",
                 "person": "only hands or a soft blurred reflection, never a clear face", "signature": "one deliberate physical action that proves the idea"}


def style():
    return config.load_json(config.ROOT / "config" / "reel_style.json", {}) or {}


def world_for(focus):
    st = style().get("worlds") or {}
    w = dict(DEFAULT_WORLD)
    w.update(st.get("default") or {})
    w.update((st.get("services") or {}).get((focus or {}).get("id")) or {})
    return w


def world_text(w):
    return (f"Set: {w['set']}. Light: {w['light']}; the problem is lit by {w['cold']}. Hero object: {w['hero']}. On its screen: {w['screen']}. "
            f"Other props: {w['props']}. Texture: {w['texture']}. The person: {w['person']}. Signature action: {w['signature']}.")


def header(i, w):
    """The film header that opens every Flow prompt: the same camera, stock, light and set on all three clips."""
    f = {**DEFAULT_FILM, **(style().get("film") or {})}
    n = str(i)
    opening = (f.get("opening") or {}).get(n) or DEFAULT_FILM["opening"][n]
    lens = (f.get("lens") or {}).get(n) or DEFAULT_FILM["lens"][n]
    return (f"{opening} {f['genre']} for '{f['brand']}', shot on {f['camera']} with a {lens}, {f['capture']}, {f['stock']}, "
            f"{w['light']}, in {w['set']}, featuring {w['hero']}.")


def _mmss(s):
    return f"{s // 60:02d}:{s % 60:02d}"


def _words(t):
    return len(re.findall(r"\S+", str(t or "")))


def _int(v):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def beat_sheet(beats, i):
    """The director's version. Timestamps run across the whole reel (clip 2 starts at 00:10); frame numbers restart in every clip."""
    off, out = (i - 1) * 10, []
    for b in beats:
        out.append(f"[{_mmss(off + b['start'])} - {_mmss(off + b['end'])}] Frame {b['start'] * FPS + 1}-{b['end'] * FPS}: {b['title']}\n"
                   f"Visual: {b['visual']}\nStory Feel: {b['feel']}\nCamera & Lens: {b['camera']}\nAudio Cue: {b['audio']}")
    return "\n\n".join(out)


def flow_prompt(clip, i, w, voiceover):
    """What is pasted into Google Flow: header, 4 beats of 2-3 seconds, one audio line that carries the exact voiceover."""
    off = (i - 1) * 10
    lines = [header(i, w)]
    for b in clip["flow_beats"]:
        lines.append(f"[{_mmss(b['start'])}-{_mmss(b['end'])} / Story {off + b['start']}-{off + b['end']}s] {b['text']}")
    audio = clip["audio"].strip()
    audio += "" if audio.endswith((".", "!", "?")) else "."
    delivery = (clip.get("delivery") or "Warm, conversational").strip().rstrip(".")
    vo = voiceover.replace('"', "'").strip()
    lines.append(f"Audio & Voiceover Sync: {audio} {delivery[:1].upper() + delivery[1:]} voiceover: \"{vo}\"" if vo else f"Audio & Voiceover Sync: {audio} No spoken words in this clip.")
    return "\n".join(lines)


def _spans(items, name):
    probs, pos = [], 0
    for k, b in enumerate(items, 1):
        if b["start"] != pos:
            probs.append(f"{name} {k} must start at {pos}s (no gap, no overlap)")
        if b["end"] <= b["start"]:
            probs.append(f"{name} {k} must end after it starts")
        pos = b["end"]
    if pos != 10:
        probs.append(f"the {name}s must end exactly at 10s, they end at {pos}s")
    return probs


def check_clip(raw):
    """-> (clean clip, problems). Problems are specific, so the retry can fix exactly them."""
    if not isinstance(raw, dict):
        return None, ["reply with ONE JSON object"]

    def listof(key, fields):
        out = []
        for b in raw.get(key) or []:
            if isinstance(b, dict):
                d = {"start": _int(b.get("start")), "end": _int(b.get("end"))}
                d.update({f: " ".join(str(b.get(f) or "").split()) for f in fields})
                out.append(d)
        return out
    beats = listof("beats", ("title", "visual", "feel", "camera", "audio"))
    flow = listof("flow_beats", ("text",))
    audio = " ".join(str(raw.get("audio") or "").split())
    delivery = " ".join(str(raw.get("delivery") or "").split())
    probs = []
    if not 6 <= len(beats) <= 10:
        probs.append(f"'beats' needs 6-10 beats of 1-2 seconds, got {len(beats)}")
    if not 3 <= len(flow) <= 5:
        probs.append(f"'flow_beats' needs 4 beats of 2-3 seconds, got {len(flow)}")
    for name, items in (("beat", beats), ("flow beat", flow)):
        if items and any(b["start"] is None or b["end"] is None for b in items):
            probs.append(f"every {name} needs whole-second 'start' and 'end'")
        elif items:
            probs += _spans(items, name)
    for k, b in enumerate(beats, 1):
        if _words(b["visual"]) < 25:
            probs.append(f"beat {k}: visual is too thin (25+ words: the objects with material, colour and state, the action, the light, the texture)")
        if _words(b["camera"]) < 5:
            probs.append(f"beat {k}: camera needs one named move and one named lens")
        if _words(b["feel"]) < 4 or not b["title"] or not b["audio"]:
            probs.append(f"beat {k}: needs a title, a Story Feel line (4+ words) and an audio cue")
    for k, b in enumerate(flow, 1):
        if _words(b["text"]) < 35:
            probs.append(f"flow beat {k} is too thin (35+ words: camera, action, light, texture)")
    if _words(audio) < 15:
        probs.append("'audio' is too thin (15+ words: the sounds in order, the stop and the final tail)")
    blob = " ".join([audio, delivery] + [str(v) for b in beats + flow for v in b.values()])
    if DEVANAGARI.search(blob):
        probs.append("Roman letters only: no Devanagari")
    return {"beats": beats, "flow_beats": flow, "audio": audio, "delivery": delivery}, probs


def basic_clip(i, w, part):
    """Plain, valid clip used only when the model cannot produce a checked one twice: the world, the story of the clip and the voiceover."""
    story = (part.get("story") or "").strip().rstrip(".")
    lens = ({**DEFAULT_FILM, **(style().get("film") or {})}.get("lens") or {}).get(str(i)) or DEFAULT_FILM["lens"][str(i)]
    text1 = (f"{story}. A slow micro-dolly push-in on {w['hero']} in {w['set']}, shot on a {lens}, lit by {w['light']}, with {w['texture']}." if story else
             f"A slow micro-dolly push-in on {w['hero']} in {w['set']}, shot on a {lens}, lit by {w['light']}, with {w['texture']}.")
    text2 = f"The screen shows {w['screen']}. {w['signature'][:1].upper() + w['signature'][1:]}, then the camera settles into a calm, balanced composition with {w['props']} in soft focus."
    return {"beats": [], "flow_beats": [{"start": 0, "end": 5, "text": text1}, {"start": 5, "end": 10, "text": text2}],
            "audio": "Soft room tone, rhythmic key presses and a warm ambient pad that settles under the voiceover.", "delivery": "Warm, conversational"}


CLIP_TEMPLATE = """You are the director and cinematographer of clip {i} of 3 (story seconds {a}-{z}) of a cinematic indie-film style reel for {brand}. Write the same ten seconds in TWO versions.
CONCEPT of the whole reel: {concept}
THIS CLIP: {story}
ARC for this clip: {arc}
EXACT WORDS SPOKEN IN THIS CLIP: {voiceover}
{prev_line}
{next_line}

THE WORLD (use these exact objects, materials and lights; do not invent a different set): {world}

STYLE RULES (binding):
{rules}

VOCABULARY to draw from (use exact, named choices like these): camera moves: {moves}. Lenses: {lenses}. Textures: {textures}. Sounds: {sounds}.

VERSION 1, "beats" (the director's beat sheet): 8 to 10 beats of 1 to 2 seconds that cover seconds 0 to 10 with no gap and no overlap. Each beat has:
- "title": 3-6 words, like "The Cold Open" or "The Deliberate Rejection";
- "visual": 35-60 words. Name every object with its material, colour and state, say exactly what moves and how, where the light falls and what the texture is;
- "feel": ONE line of 8-20 words, the inner feeling, in Roman Hinglish (English letters only);
- "camera": ONE named camera move and ONE named lens, with the aperture, 10-25 words;
- "audio": the sound in this beat, plus the exact spoken words if the voiceover falls here.
VERSION 2, "flow_beats" (pasted into Google Flow): 4 beats of 2 to 3 seconds that cover 0 to 10 with no gap. Each "text" is 50-90 words in plain English: the camera move and lens, the exact action, what is on screen, the light and the texture, merged into one rich description. No Story Feel lines and no Hinglish feelings here.
"audio": 40-70 words, the sound timeline of the ten seconds in order (silence, first sound, rhythm, stop, pad, tail). Do NOT put the spoken words in it.
"delivery": 4-10 words on how the voice sounds, for example "Intimate, grounded, conversational".
Times are whole seconds from 0 to 10 inside this clip. Never write a person's clear face, a real brand or logo, a price, a client, a result or a guarantee.
Return JSON: {{"beats": [{{"start": 0, "end": 1, "title": "...", "visual": "...", "feel": "...", "camera": "...", "audio": "..."}}], "flow_beats": [{{"start": 0, "end": 3, "text": "..."}}], "audio": "...", "delivery": "..."}}"""


def write_clip(i, ctx):
    """One clip, checked. -> (clip, None) or (None, problems)."""
    prompt = CLIP_TEMPLATE.format(**ctx)
    probs, notes = [], ""
    for _ in range(2):
        try:
            raw = llm.ask_json(llm.prompt_writer, prompt + notes, SYS)
        except Exception as e:
            print(f"[video] clip {i} failed: {e}")
            return None, [f"the model failed: {str(e)[:100]}"]
        clip, probs = check_clip(raw)
        if not probs:
            return clip, None
        print(f"[video] clip {i} rejected: {'; '.join(probs)[:200]}")
        notes = "\nYOUR LAST ANSWER HAD THESE PROBLEMS. Fix every one and keep the rest: " + "; ".join(probs[:8])
    return None, probs


def run(plan, focus, posts, guidance="", brand=None):
    """-> {"hook_first_3s", "concept", "parts": [{"time", "voiceover", "story", "flow_prompt", "beat_sheet"}], "voiceover", "warnings"}"""
    hook = plan["hooks"][plan.get("chosen_hook", 0)]["text"]
    st, w = style(), world_for(focus)
    kw = (focus or {}).get("dm_keyword") or ""
    rules_brand = "\n".join(f"- {r}" for r in ((brand or {}).get("facts_rules") or []))
    brand_block = f"\nBRAND RULES (binding; nothing in the reel may break them):\n{rules_brand}\n" if rules_brand else ""
    prompt = f"""Plan a 30-second vertical reel, told as a cinematic micro-story, for: {plan['topic']} (service: {(focus or {}).get('name')}).
Hook: {hook}
Strategist note: {guidance}

REEL RULES (from vidIQ public guidance; they override anything below that is weaker):
{ideas.rules_text()}
{brand_block}
THE WORLD every clip is filmed in: {world_text(w)}

Google Flow generates ONE 10-second clip per prompt, so write THREE standalone clips (0-10s, 10-20s, 20-30s). Each clip must work on its own, because Flow will not remember the previous one.
- Part 1 (0-10s): the first spoken line is a specific problem or result in 12 words or fewer (no greeting, no brand intro) and the visual payoff appears in the FIRST SECOND. {(st.get('arc') or {}).get('1', '')}
- Part 2 (10-20s): show how it works or the proof, one idea, as one visible action. {(st.get('arc') or {}).get('2', '')}
- Part 3 (20-30s): the result plus ONE next step, spoken naturally{f' (say DM {kw})' if kw else ' (a DM keyword)'}; the very last line or frame hands back to the opening (for example it ends on the question the first line answers) so a replay feels natural. {(st.get('arc') or {}).get('3', '')}
- Each part's spoken line: 25 words or fewer so it fits in 10 seconds, simple English or light Hinglish in Roman letters.
- "concept": ONE visible physical story the three clips tell, in 30 words or fewer.
- "story" of each part: what happens in that clip, in 30 words or fewer.
Return JSON: {{"hook_first_3s": "on-screen text (3-7 words, top third) + spoken line (5-10 words)", "concept": "...", "parts": [{{"time": "0-10s", "voiceover": "...", "story": "..."}}, {{"time": "10-20s", "voiceover": "...", "story": "..."}}, {{"time": "20-30s", "voiceover": "...", "story": "..."}}]}}"""
    out = llm.ask_json(llm.prompt_writer, prompt, SYS)
    raw_parts = [p for p in (out.get("parts") or []) if isinstance(p, dict)][:3]
    while len(raw_parts) < 3:
        raw_parts.append({})
    concept = " ".join(str(out.get("concept") or plan["topic"]).split())
    rules = "\n".join(f"{n}. {r}" for n, r in enumerate(st.get("rules") or [], 1))
    voc = st.get("vocabulary") or {}
    f = {**DEFAULT_FILM, **(st.get("film") or {})}
    warnings, parts, prev = [], [], ""
    for i, p in enumerate(raw_parts, 1):
        vo = " ".join(str(p.get("voiceover") or out.get("voiceover") if i == 1 else p.get("voiceover") or "").split())
        story = " ".join(str(p.get("story") or "").split())
        nxt = " ".join(str(raw_parts[i].get("story") or "").split()) if i < 3 else ""
        ctx = {"i": i, "a": (i - 1) * 10, "z": i * 10, "brand": f["brand"], "concept": concept, "story": story or concept,
               "arc": (st.get("arc") or {}).get(str(i), ""), "voiceover": f'"{vo}"' if vo else "nothing: this clip has no spoken words",
               "prev_line": (f'The previous clip ended on this frame: "{prev[:300]}". Open on a frame that continues from it.' if prev else
                             "This is the opening clip: open on the problem in the very first second, in silence or near-silence."),
               "next_line": (f"The next clip is about: {nxt}. End on a frame that sets it up." if nxt else
                             "This is the final clip: end on a locked, clean wide frame with empty space for typography, on the question the opening line answers, and let the sound fade back into the silence of clip 1."),
               "world": world_text(w), "rules": rules, "moves": ", ".join(voc.get("camera_moves") or []), "lenses": ", ".join(voc.get("lenses") or []),
               "textures": ", ".join(voc.get("texture") or []), "sounds": ", ".join(voc.get("sound") or [])}
        clip, probs = write_clip(i, ctx)
        if clip is None:
            warnings.append(f"reel clip {i}: the model could not write a checked clip ({'; '.join(probs)[:120]}), so a plain fallback clip is used. Read it before you generate.")
            clip = basic_clip(i, w, {"story": story or concept})
        parts.append({"time": p.get("time") or TIMES[i - 1], "voiceover": vo, "story": story, "flow_prompt": flow_prompt(clip, i, w, vo),
                      "beat_sheet": beat_sheet(clip["beats"], i)})
        prev = clip["flow_beats"][-1]["text"]
    if kw and kw.lower() not in parts[2]["voiceover"].lower():
        warnings.append(f"reel: the last spoken line does not say the DM keyword ({kw}); add it when you record.")
    return {"hook_first_3s": out.get("hook_first_3s", ""), "concept": concept, "parts": parts,
            "voiceover": " ".join(p["voiceover"] for p in parts if p["voiceover"]).strip(), "warnings": warnings}
