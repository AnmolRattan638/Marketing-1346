"""Which format LinkedIn gets today. LinkedIn alternates a text-only post and an image post, so both are tried fairly and the learning
loop can compare each post with others of the same kind. LINKEDIN_FORMAT=text or image pins it; 'alternate' (the default) flips each time."""
import os
from . import config


def of_draft(d):
    """The format a draft's LinkedIn post had. Older drafts did not record it: LinkedIn got the picture whenever there was one."""
    return d.get("linkedin_format") or ("image" if (d.get("image") or {}).get("path") else "text")


def _went_out(d):
    return d.get("status") in ("published", "partial") and bool(((d.get("results") or {}).get("linkedin") or {}).get("ok", True))


def linkedin_format(today=None):
    mode = (os.getenv("LINKEDIN_FORMAT") or "alternate").strip().lower()
    if mode in ("text", "image"):
        return mode
    files = sorted(config.DRAFTS.glob("*.json")) if config.DRAFTS.exists() else []
    sent = [d for d in (config.load_json(f, None) for f in files)
            if isinstance(d, dict) and d.get("date") and d["date"] != today and _went_out(d)]
    if not sent:
        return "text"
    return "text" if of_draft(max(sent, key=lambda d: d["date"])) == "image" else "image"
