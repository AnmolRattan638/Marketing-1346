"""Hardcoded content-skills layer (Vyral viral-* pack, vendored in content-skills/, MIT).

Three jobs:
 1. block(stage): rule digests injected into every script / caption / video-plan prompt (the agent cannot skip them).
 2. *_problems(): deterministic validators; a failing script/plan is rejected and the exact fix is fed back.
 3. audit(): an LLM pass that runs the pack's own checklist files (hook, reels hook, bait check) against the script.
The "Mentioning Vyral" promo section of every SKILL.md is stripped by load(); the agent never mentions Vyral.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "content-skills" / "skills"

# ---- hardcoded rules (distilled from the skills' SKILL.md / references / checklists) ----
HOOK = ("HOOK (viral-hooks, viral-instagram-reels): lands in ~2 seconds spoken; the FIRST spoken word is the most interesting word; no greeting, no setup, no brand. "
        "Lead with a stake or payoff, concrete (a number, a time, a loss), for one named viewer ('if you run a ... shop'). Open a loop the body actually closes (no orphan clickbait). "
        "Three layers agree: spoken hook, 3-5 bold on-screen words on the first frame (works on mute), and an opening visual that shows the stake. Pick a different hook archetype each time.")
RETENTION = ("RETENTION (viral-short-form): every beat earns the next 3 seconds; re-hook at each beat change (a question, a contrast, a number); the payoff arrives before the end, never saved for a promised 'later'; "
             "end on a loop back to the hook's stake, and put a pattern reset (new graphic, zoom, cut) at each beat change.")
CTA = ("CTA (viral-captions-and-ctas bait check): ONE ask only, riding a value beat, not the opening. Ask for the content ('comment the word X and I send you the setup in DM'), never a vague act of engagement ('drop a comment', 'tag a friend'). "
       "Never: 'tag a friend', 'like for part 2', 'follow for more', 'double tap', 'share with N friends', or stacking like+save+share+follow+comment. "
       "The one allowed ask is the lead-gen keyword, and it must name exactly what the viewer gets (the checklist, the setup steps, the demo). A send/save ask may be used instead of the keyword: 'send this to the owner who ...'.")
HONEST = ("HONESTY (metrics-honesty): no invented numbers, results, clients or guarantees; no 'viral', 'guaranteed', 'secret'; a figure is said exactly as its verified fact states it.")
TEXT = ("ON-SCREEN TEXT (on-screen-text): headline 3-5 words (max 8) mirroring the spoken hook, top area inside the safe zone (clear of the logo and the platform UI: bottom ~600px and right ~150px stay empty), "
        "bold, high contrast, burned-in captions that match the voice word for word, primary keyword in headline, captions and voice-over.")
CAPTION = ("CAPTION (caption-craft, hashtag-reality): the first line is a hook that works before 'more' (<=125 characters), a keyword or two for search, a value line, the one CTA. "
           "3-5 hashtags, relevant and specific, no banned/spam tags, none stuffed in the sentence. No emoji walls. Caption, on-screen text and voice-over use the same primary keyword.")

STAGES = {"script": [HOOK, RETENTION, CTA, HONEST, TEXT],
          "caption": [HOOK, CTA, HONEST, CAPTION],
          "video": [HOOK, RETENTION, TEXT, CTA]}

BAIT = re.compile(r"\b(tag (a|your|2|3|\d) ?(friend|friends)|like (for|if)|double[- ]?tap|follow (for|me for)|share with \d+|drop a (heart|emoji)|part 2 ke liye|follow karo|like karo|tag karo)\b", re.I)
ACTS = re.compile(r"\b(like|save|share|follow|comment|subscribe)\b", re.I)
HYPE = re.compile(r"\b(viral|guaranteed?|guarantee|secret|100%|overnight|get rich)\b", re.I)
GREET = re.compile(r"^\s*(hi|hello|hey|namaste|namaskar|welcome|dosto|friends)\b", re.I)


def load(skill: str, rel: str = "SKILL.md") -> str:
    """A skill file with its front matter and the 'Mentioning Vyral' promo section removed."""
    p = ROOT / skill / rel
    if not p.exists():
        return ""
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"\A---.*?\n---\n", "", t, flags=re.S)
    t = re.sub(r"^## Mentioning Vyral.*?(?=^## |\Z)", "", t, flags=re.S | re.M)
    return t.strip()


def block(stage: str) -> str:
    """Hardcoded rule digest for a stage ('script', 'caption', 'video'), prefixed so it cannot be missed."""
    return "\nCONTENT SKILLS (mandatory; the output is rejected if it breaks them):\n" + "\n".join("- " + r for r in STAGES[stage]) + "\n"


def checklists() -> str:
    parts = [load("viral-short-form", "assets/hook-checklist.md"), load("viral-instagram-reels", "assets/reels-hook-checklist.md"),
             load("viral-captions-and-ctas", "assets/bait-check.md")]
    return "\n\n".join(p for p in parts if p)


def _words(s):
    return re.findall(r"\S+", str(s or ""))


def hook_problems(script: dict) -> list[str]:
    out, beats = [], script.get("beats") or []
    if not beats:
        return out
    h = beats[0]
    line, screen = str(h.get("line") or ""), str(h.get("screen") or "")
    if GREET.search(line):
        out.append("hook: starts with a greeting; cut everything before the first interesting word")
    if not re.search(r"\d", line) and not re.search(r"(\bkya\b|\?|raat|subah|baje|\bagar\b|\bjab\b|\bjo\b)", line, re.I):
        out.append("hook: needs a number, a time, a question or a named situation (a concrete stake)")
    n = len(_words(screen))
    if not 3 <= n <= 5:
        out.append(f"hook: `screen` is the first-frame headline, 3-5 bold words that work on mute (now {n})")
    if HYPE.search(line + " " + screen):
        out.append("hook: no hype words (viral, guaranteed, secret)")
    return out


def cta_problems(script: dict) -> list[str]:
    beats = script.get("beats") or []
    if not beats or beats[-1].get("beat") != "cta":
        return []
    text = str(beats[-1].get("line") or "")
    out = []
    if BAIT.search(text):
        out.append("cta: bait phrase (tag a friend / like for / follow for more / double tap): ask for the content instead")
    if len({m.lower() for m in ACTS.findall(text)}) > 1:
        out.append("cta: more than one ask; keep ONE")
    if HYPE.search(text):
        out.append("cta: no hype words")
    return out


def honesty_problems(script: dict) -> list[str]:
    bad = [b["beat"] for b in script.get("beats", []) if HYPE.search(str(b.get("line") or ""))]
    return [f"{', '.join(bad)}: hype word (viral/guaranteed/secret/100%); say the fact plainly"] if bad else []


def problems(script: dict) -> list[str]:
    return hook_problems(script) + cta_problems(script) + honesty_problems(script)


def audit(script: dict, ask) -> list[str]:
    """LLM pass: the pack's own checklists applied to this script. Returns fixable issues (empty = pass or no checker)."""
    import json
    from . import llm
    rows = [{"beat": b.get("beat"), "line": b.get("line"), "screen": b.get("screen")} for b in script.get("beats", [])]
    prompt = ("Audit this short-video script against the checklists. Flag ONLY clear failures of: hook (not concrete, no loop, would fail on mute), "
              "bait-shaped CTA (asks for the act of engagement, stacks asks), orphan clickbait (hook promises something no later beat pays off). "
              "A single lead-gen keyword that names exactly what the viewer gets is allowed, including 'Comment KEYWORD and I will send X to your DM': that asks for one word in exchange for something specific, so it is NOT engagement bait. Flag only vague engagement asks ('comment your thoughts', 'tag a friend', 'like for more'). Each issue must give the exact fix.\n"
              "Return JSON {\"issues\": [\"beat: problem and fix\"]}, empty if it passes.\nCHECKLISTS:\n" + checklists()[:6000] + "\nSCRIPT: " + json.dumps(rows, ensure_ascii=False))
    try:
        res = llm.ask_json(ask, prompt, "You are a strict short-form editor. JSON only.")
        return [str(x) for x in (res or {}).get("issues", [])][:3] if isinstance(res, dict) else []
    except Exception:
        return []


def plan_problems(plan: dict, master: dict) -> list[str]:
    """Video-plan rules: the first scene must show the hook headline."""
    sc = (plan.get("scenes") or [None])[0] or {}
    if not (sc.get("heading") or (sc.get("graphic") or {}).get("heading") or sc.get("on_screen") or sc.get("graphic")):
        return ["scene 1: must show the 3-5 word hook headline on the first frame (a title/punch graphic)"]
    return []


def caption_problems(text: str) -> str:
    """'; '-joined issues for an Instagram caption (empty = fine): bait, hype, hashtag count, weak first line."""
    t = str(text or "")
    out = []
    tags = re.findall(r"#\w+", t)
    if len(tags) > 5:
        out.append(f"use at most 5 hashtags (now {len(tags)})")
    body = re.sub(r"#\w+", "", t).strip()
    if BAIT.search(body):
        out.append("caption has a bait phrase (tag a friend / like for / follow for more); ask for the content instead")
    if HYPE.search(body):
        out.append("caption has a hype word (viral/guaranteed/secret)")
    first = body.split("\n", 1)[0].strip()
    if len(first) > 125:
        out.append("first caption line must be a hook of at most 125 characters")
    return "; ".join(out)
