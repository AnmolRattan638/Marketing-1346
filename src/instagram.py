"""Live Instagram snapshot via the Instagram API (Instagram Login). Optional: needs INSTAGRAM_ACCESS_TOKEN."""
import os
import requests


def snapshot():
    tok = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if not tok:
        return None
    base = f"https://graph.instagram.com/{os.getenv('INSTAGRAM_API_VERSION', 'v23.0')}"

    def get(path, **params):
        r = requests.get(f"{base}/{path}", params={**params, "access_token": tok}, timeout=60)
        r.raise_for_status()
        return r.json()

    prof = get("me", fields="username,followers_count,follows_count,media_count")
    media = get("me/media", fields="id,caption,media_type,timestamp,like_count,comments_count", limit=12).get("data", [])
    for i, m in enumerate(media):
        m["caption"] = (m.get("caption") or "")[:120]
        if i < 6:   # reach/saves need extra permission; best effort only
            try:
                ins = get(f"{m['id']}/insights", metric="reach,saved,shares").get("data", [])
                m["insights"] = {x["name"]: (x.get("values") or [{}])[0].get("value") for x in ins}
            except Exception:
                pass
    return {"profile": prof, "recent_posts": media}
