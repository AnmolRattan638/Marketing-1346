"""Direct channel that needs no scheduler: Bluesky (AT protocol)."""
import datetime as dt
import os
import requests


def _img(image_path):
    from . import config
    return (config.ROOT / image_path).read_bytes() if image_path else None


def _blob(path):
    """Image bytes under Bluesky's ~1 MB blob limit (re-encoded smaller when needed), or None."""
    data = _img(path)
    if data and len(data) >= 950_000:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        for q in (82, 72, 62):
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=q, optimize=True)
            if buf.tell() < 950_000:
                return buf.getvalue()
        return None
    return data


def bluesky(text, image_path=None, alt=None, images=None):
    """images = [{"path", "alt"}, ...] posts up to 4 images (Bluesky's maximum, shown as a grid); otherwise the single image_path as before."""
    s = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession", timeout=60,
                      json={"identifier": os.environ["BLUESKY_HANDLE"], "password": os.environ["BLUESKY_APP_PASSWORD"]})
    s.raise_for_status()
    s = s.json()
    h = {"Authorization": f"Bearer {s['accessJwt']}"}
    record = {"$type": "app.bsky.feed.post", "text": text[:300], "createdAt": dt.datetime.now(dt.timezone.utc).isoformat()}
    if images:
        embedded = []
        for it in images[:4]:
            data = _blob(it["path"])
            if data:
                b = requests.post("https://bsky.social/xrpc/com.atproto.repo.uploadBlob", timeout=120, headers={**h, "Content-Type": "image/jpeg"}, data=data)
                b.raise_for_status()
                embedded.append({"alt": (it.get("alt") or "Image for the post")[:1000], "image": b.json()["blob"]})
        if embedded:
            record["embed"] = {"$type": "app.bsky.embed.images", "images": embedded}
    data = _img(image_path) if not images else None
    if data and len(data) < 950_000:      # Bluesky blob limit is ~1 MB
        b = requests.post("https://bsky.social/xrpc/com.atproto.repo.uploadBlob", timeout=120,
                          headers={**h, "Content-Type": "image/jpeg"}, data=data)
        b.raise_for_status()
        record["embed"] = {"$type": "app.bsky.embed.images", "images": [{"alt": (alt or "Image for the post")[:1000], "image": b.json()["blob"]}]}
    r = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord", headers=h, timeout=60,
                      json={"repo": s["did"], "collection": "app.bsky.feed.post", "record": record})
    r.raise_for_status()
    return r.json().get("uri", "posted")
