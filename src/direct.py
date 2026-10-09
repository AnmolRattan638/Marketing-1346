"""Direct channels that need no scheduler: Bluesky (AT protocol), Mastodon, Discord webhook."""
import datetime as dt
import os
import requests


def _img(image_path):
    from . import config
    return (config.ROOT / image_path).read_bytes() if image_path else None


def bluesky(text, image_path=None):
    s = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession", timeout=60,
                      json={"identifier": os.environ["BLUESKY_HANDLE"], "password": os.environ["BLUESKY_APP_PASSWORD"]})
    s.raise_for_status()
    s = s.json()
    h = {"Authorization": f"Bearer {s['accessJwt']}"}
    record = {"$type": "app.bsky.feed.post", "text": text[:300], "createdAt": dt.datetime.now(dt.timezone.utc).isoformat()}
    data = _img(image_path)
    if data and len(data) < 950_000:      # Bluesky blob limit is ~1 MB
        b = requests.post("https://bsky.social/xrpc/com.atproto.repo.uploadBlob", timeout=120,
                          headers={**h, "Content-Type": "image/jpeg"}, data=data)
        b.raise_for_status()
        record["embed"] = {"$type": "app.bsky.embed.images", "images": [{"alt": "Illustration for the post", "image": b.json()["blob"]}]}
    r = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord", headers=h, timeout=60,
                      json={"repo": s["did"], "collection": "app.bsky.feed.post", "record": record})
    r.raise_for_status()
    return r.json().get("uri", "posted")


def mastodon(text, image_path=None):
    base = os.environ["MASTODON_INSTANCE"].strip().rstrip("/")
    base = base if base.startswith("http") else f"https://{base}"
    h = {"Authorization": f"Bearer {os.environ['MASTODON_TOKEN']}"}
    body = {"status": text[:500]}
    data = _img(image_path)
    if data:
        m = requests.post(f"{base}/api/v2/media", headers=h, timeout=120, files={"file": ("post.jpg", data, "image/jpeg")})
        m.raise_for_status()
        body["media_ids"] = [m.json()["id"]]
    r = requests.post(f"{base}/api/v1/statuses", headers=h, json=body, timeout=60)
    r.raise_for_status()
    return r.json().get("url", "posted")


def discord(text, image_path=None):
    url = os.environ["DISCORD_WEBHOOK_URL"]
    data = _img(image_path)
    if data:
        r = requests.post(url, data={"content": text[:2000]}, files={"file": ("post.jpg", data, "image/jpeg")}, timeout=60)
    else:
        r = requests.post(url, json={"content": text[:2000]}, timeout=60)
    r.raise_for_status()
    return "sent"


# extra channel -> (needed secrets, function, which draft text to use)
EXTRAS = {
    "mastodon": (["MASTODON_INSTANCE", "MASTODON_TOKEN"], mastodon, "bluesky"),
    "discord": (["DISCORD_WEBHOOK_URL"], discord, "linkedin"),
}
