"""Caption formatting for Instagram, LinkedIn and Bluesky.

None of the three accepts real bold in a post, so emphasis is done the way people do it by hand: **marked words** are turned into
Unicode 'Mathematical Sans-Serif Bold' letters (𝗟𝗶𝗸𝗲 𝘁𝗵𝗶𝘀), which display as bold everywhere. The writer marks emphasis with **double
asterisks**; this module runs LAST (after fact-check and ad-review, which may rewrite text) and is idempotent.

Honest limits of Unicode bold: screen readers spell it out letter by letter and the bold words are not searchable, so it is used on a
few short spans only (BOLD_LIMIT), never on hashtags, handles or links. Set UNICODE_BOLD=0 to keep CAPITALS but drop the bold.
"""
import os
import re

BOLD_LIMIT = 6                 # more bold spans than this stops looking like emphasis
MAX_SPAN = 90                  # a bold span longer than this is shouting, not emphasis
LIMITS = {"instagram": 60, "instagram_reel": 45, "linkedin": 120}      # words, hashtags excluded
BLUESKY_MAX = 300


def bold(text):
    """A-Z, a-z and 0-9 -> Mathematical Sans-Serif Bold; everything else (Devanagari, punctuation, emoji) unchanged."""
    out = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr(0x1D5D4 + ord(ch) - 65))
        elif "a" <= ch <= "z":
            out.append(chr(0x1D5EE + ord(ch) - 97))
        elif "0" <= ch <= "9":
            out.append(chr(0x1D7EC + ord(ch) - 48))
        else:
            out.append(ch)
    return "".join(out)


def words(text):
    """Word count the way a reader sees it: no hashtags, no ** markers, no bare symbols such as the arrow."""
    t = re.sub(r"#\w+", " ", (text or "").replace("**", ""))
    return len([w for w in t.split() if re.search(r"\w", w)])


def over_limit(posts, ig_mode="auto_image"):
    """Notes for the writer when a caption is too long, else ''. (Counted on the marker text, before formatting.)"""
    notes = []
    key = "instagram_reel" if ig_mode == "manual_reel" else "instagram"
    n = words(posts.get("instagram", ""))
    if n > LIMITS[key] + 8:
        notes.append(f"instagram caption has {n} words, the maximum is {LIMITS[key]}: cut it, keep the hook and the DM line")
    n = words(posts.get("linkedin", ""))
    if n > LIMITS["linkedin"] + 15:
        notes.append(f"linkedin post has {n} words, the maximum is {LIMITS['linkedin']}: cut it")
    if len(posts.get("bluesky", "").replace("**", "")) > 280:
        notes.append("bluesky post is over 280 characters: cut it")
    return "; ".join(notes)


def finalize(text, bold_on=None):
    """Markers -> bold letters (or plain), tidy the layout. Safe to run twice."""
    if bold_on is None:
        bold_on = os.getenv("UNICODE_BOLD", "1") != "0"
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    count = [0]

    def span(m):
        inner = m.group(1).strip()
        skip = inner.startswith(("#", "@")) or "http" in inner.lower() or len(inner) > MAX_SPAN
        if not bold_on or skip or count[0] >= BOLD_LIMIT:
            return inner
        count[0] += 1
        return bold(inner)
    text = re.sub(r"\*\*(.+?)\*\*", span, text)
    text = text.replace("**", "")                                          # unpaired leftovers
    text = re.sub(r"(?m)^[ \t]*[*•\-][ \t]+", "→ ", text)                  # markdown bullets -> the arrow used in captions
    text = re.sub(r"(?<![\w*])\*(?![\s*])([^*\n]+?)\*(?!\w)", r"\1", text)  # *single* emphasis the model sometimes writes
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def unstyle(text):
    """Mathematical Sans-Serif Bold letters/digits -> plain ASCII (undo bold() if a model or the fact-checker produced it)."""
    out = []
    for ch in text or "":
        o = ord(ch)
        if 0x1D5D4 <= o <= 0x1D5ED:
            out.append(chr(65 + o - 0x1D5D4))
        elif 0x1D5EE <= o <= 0x1D607:
            out.append(chr(97 + o - 0x1D5EE))
        elif 0x1D7EC <= o <= 0x1D7F5:
            out.append(chr(48 + o - 0x1D7EC))
        else:
            out.append(ch)
    return "".join(out)


def finalize_linkedin(text):
    """LinkedIn only: plain text. No Unicode bold, no arrows/bullets, no ALL-CAPS lines (those looked like shouting and
    hurt readability). The DM keyword (e.g. DM SCRIPT) keeps its capitals. Safe to run twice."""
    text = unstyle((text or "").replace("\r\n", "\n").replace("\r", "\n"))
    text = text.replace("**", "")
    text = re.sub(r"(?<![\w*])\*(?![\s*])([^*\n]+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?m)^[ \t]*(?:→|[*•\-])[ \t]+", "", text)
    lines = []
    for ln in text.split("\n"):
        letters = [c for c in ln if c.isalpha()]
        if len(ln.split()) >= 3 and len(letters) >= 10 and ln == ln.upper() and not ln.lstrip().startswith("DM "):
            ln = ln.lower()
            ln = ln[:1].upper() + ln[1:]
        lines.append(ln)
    text = "\n".join(lines)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


NARROW_TAGS = {"webdeveloper", "webdevelopment", "webdevelopers", "webdesign", "webdesigner", "webdev", "websitedesign",
               "developer", "developers", "coding", "programmer", "freelancedeveloper", "agencylife"}
BROAD_TAGS = ["#FreelanceIndia", "#Freelancers", "#LeadGeneration", "#GetClients", "#SmallBusinessIndia"]


def widen_lead_hashtags(text):
    """Lead-gen Instagram caption only: drop profession-specific hashtags (#WebDeveloper...) and top up with broad ones (4-5 in total)."""
    lines = (text or "").rstrip().split("\n")
    has_tags = bool(lines) and re.fullmatch(r"(?:#\w+\s*)+", lines[-1].strip() or "x") is not None
    tags = re.findall(r"#\w+", lines[-1]) if has_tags else []
    keep = [t for t in tags if t[1:].lower() not in NARROW_TAGS]
    for t in BROAD_TAGS:
        if len(keep) >= 4:
            break
        if t.lower() not in [k.lower() for k in keep]:
            keep.append(t)
    line = " ".join(keep[:5])
    return "\n".join(lines[:-1] + [line]) if has_tags else "\n".join(lines).rstrip() + "\n\n" + line


def finalize_posts(posts, bold_on=None, focus_id=None):
    out = dict(posts)
    if focus_id == "lead_gen" and isinstance(out.get("instagram"), str):
        out["instagram"] = widen_lead_hashtags(out["instagram"])
    for k in ("instagram", "bluesky"):          # unchanged: Unicode bold + arrows
        if isinstance(out.get(k), str):
            out[k] = finalize(out[k], bold_on)
    if isinstance(out.get("linkedin"), str):    # LinkedIn has its own plain-text format
        out["linkedin"] = finalize_linkedin(out["linkedin"])
    if isinstance(out.get("bluesky"), str):
        out["bluesky"] = out["bluesky"][:BLUESKY_MAX]
    return out
