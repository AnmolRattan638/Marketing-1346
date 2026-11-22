"""What goes to Telegram with the reel: the spoken script (scene by scene, exactly what the voice says and the captions show) and a paste-ready Instagram caption for the reel."""
from __future__ import annotations

import re

HASHTAGS = {
    "website": ["#WebsiteDesign", "#SmallBusinessIndia", "#LocalBusiness", "#MobileFirst", "#DigitalIndia"],
    "chatbot": ["#WhatsAppBot", "#Chatbot", "#SmallBusinessIndia", "#BusinessAutomation", "#CustomerService"],
    "animated_ads": ["#VideoAds", "#MotionGraphics", "#SmallBusinessIndia", "#DigitalMarketing", "#AdCreative"],
    "lead_gen": ["#LeadGeneration", "#SmallBusinessIndia", "#SalesTips", "#DigitalMarketing", "#BusinessGrowth"],
    "reel_scripts": ["#ReelsIndia", "#ContentCreator", "#ReelScripts", "#SocialMediaTips", "#ContentStrategy"],
    "seo_blogs": ["#SEOIndia", "#BlogWriting", "#GoogleRanking", "#ContentMarketing", "#SmallBusinessIndia"],
}
BEAT_NAMES = {"pain": "Hook", "poke": "Problem", "rehook": "Rehook", "fix": "Fix", "payoff": "Payoff", "recap": "Recap", "cta": "Ask"}


def _lines(plan: dict, master: dict | None) -> list[tuple[str, str]]:
    """[(label, spoken line)] from the video's own scenes (what is really said), labelled with the master script's beats when they line up."""
    spoken = [" ".join(str(sc.get("narration") or "").split()) for sc in (plan or {}).get("scenes", [])]
    beats = [b.get("beat") for b in (master or {}).get("beats", [])]
    out = []
    for i, t in enumerate(spoken):
        if t:
            out.append((BEAT_NAMES.get(beats[i], str(beats[i]).title()) if len(beats) == len(spoken) and beats[i] else f"Scene {i + 1}", t))
    if not out and master:
        out = [(BEAT_NAMES.get(b.get("beat"), str(b.get("beat")).title()), " ".join(str(b.get("line") or "").split())) for b in master.get("beats", []) if b.get("line")]
    return out


def script_text(plan: dict, master: dict | None) -> str:
    rows = _lines(plan, master)
    if not rows:
        return ""
    return "REEL SCRIPT (what the voice says, same as the captions)\n" + "\n".join(f"{i}. {lab}: {t}" for i, (lab, t) in enumerate(rows, 1))


def caption_text(plan: dict, master: dict | None, service: str = "") -> str:
    """A caption you can paste under the reel: the hook, up to three short points from the body, the comment ask, sources, hashtags."""
    rows = _lines(plan, master)
    if not rows:
        return ""
    service = service or (master or {}).get("service") or ""
    hook = re.sub(r"\s*(\.\.\.|…)\s*$", "", rows[0][1]).strip()
    body = [t for lab, t in rows[1:-1] if len(t) <= 120][:3]
    mk = (master or {}).get("marketing") or {}
    kw = mk.get("keyword") or (master or {}).get("keyword") or ""
    gets = re.sub(r"^(a|an|the)\s+", "", str(mk.get("gets") or "").split(":")[0].strip(), flags=re.I)
    ask = f"Comment {kw} likho, main aapko {gets or 'ek simple checklist'} DM mein bhej dunga." if kw else ""
    src = []
    for f in (master or {}).get("facts", []):
        d = f.get("source") or ""
        if d and d not in src:
            src.append(d)
    tease = "Poora breakdown aaj ke carousel post mein hai (profile par swipe karo)." if (master or {}).get("carousel_tease") else ""
    parts = [hook.upper() if hook else "", "\n".join(f"→ {t}" for t in body), ask, tease, ("Sources: " + ", ".join(src[:3])) if src else "", " ".join(HASHTAGS.get(service, ["#SmallBusinessIndia", "#DigitalIndia"]))]
    return "\n\n".join(p for p in parts if p)


def message(plan: dict, master: dict | None, service: str = "") -> str:
    s, c = script_text(plan, master), caption_text(plan, master, service)
    note = "PART 2 of today's series: post it AFTER reel 1 (it answers what reel 1 left open)." if (master or {}).get("series") else ""
    return "\n\n".join(x for x in (note, s, ("CAPTION (copy and paste under the reel)\n" + "-" * 24 + "\n" + c) if c else "") if x)
