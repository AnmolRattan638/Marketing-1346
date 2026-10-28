"""Publishers: Buffer, Zernio, Upload-Post. Rotates the first-choice tool daily and falls back per platform."""
import datetime as dt
import os
import requests
from . import buffer, config, direct


class Buffer:
    name, secrets, multi_image = "buffer", ["BUFFER_API_KEY"], True

    def __init__(self):
        self._ch = None

    def post(self, platform, text, image_url, image_path, images=None):
        if self._ch is None:
            self._ch = buffer.channel_map()
        if platform not in self._ch:
            raise RuntimeError("channel not connected")
        p = buffer.create_post(self._ch[platform], text, [i["url"] for i in images] if images else image_url)
        return f"sent to Buffer {p.get('id')} (due {p.get('dueAt') or 'now'})"


class Zernio:
    name, secrets, multi_image = "zernio", ["ZERNIO_API_KEY"], True
    base = "https://zernio.com/api/v1"

    def __init__(self):
        self._acc = None

    def _h(self):
        return {"Authorization": f"Bearer {os.environ['ZERNIO_API_KEY']}"}

    def post(self, platform, text, image_url, image_path, images=None):
        if self._acc is None:
            r = requests.get(f"{self.base}/accounts", headers=self._h(), timeout=60)
            r.raise_for_status()
            self._acc = {}
            for a in r.json().get("accounts", []):
                if a.get("isActive", True):
                    self._acc.setdefault(a["platform"], a["_id"])
        if platform not in self._acc:
            raise RuntimeError("account not connected")
        body = {"content": text, "publishNow": True, "platforms": [{"platform": platform, "accountId": self._acc[platform]}]}
        if images:                                           # a carousel: the order of mediaItems is the slide order
            body["mediaItems"] = [{"url": i["url"], "type": "image"} for i in images]
        elif image_url:
            body["mediaItems"] = [{"url": image_url, "type": "image"}]
        r = requests.post(f"{self.base}/posts", headers=self._h(), json=body, timeout=120)
        if not r.ok:
            raise RuntimeError(f"{r.status_code} {r.text[:200]}")
        return f"posted {r.json().get('post', {}).get('_id')}"


class UploadPost:
    name, secrets = "upload-post", ["UPLOAD_POST_API_KEY", "UPLOAD_POST_USER"]
    base = "https://api.upload-post.com/api"

    def post(self, platform, text, image_url, image_path):
        h = {"Authorization": f"Apikey {os.environ['UPLOAD_POST_API_KEY']}"}
        data = {"user": os.environ["UPLOAD_POST_USER"], "platform[]": [platform], "title": text}
        if image_path:
            with open(config.ROOT / image_path, "rb") as f:
                r = requests.post(f"{self.base}/upload_photos", headers=h, data=data,
                                  files=[("photos[]", (os.path.basename(image_path), f, "image/jpeg"))], timeout=180)
        else:
            r = requests.post(f"{self.base}/upload_text", headers=h, data=data, timeout=120)
        if not r.ok:
            raise RuntimeError(f"{r.status_code} {r.text[:200]}")
        j = r.json()
        if j.get("success") is False:
            raise RuntimeError(str(j)[:200])
        return f"sent {j.get('request_id') or j.get('job_id') or ''}".strip()


class LimeSocial:
    name, secrets, platforms = "limesocial", ["LIMESOCIAL_API_KEY"], ("instagram",)   # LinkedIn is paid-only there
    base = "https://api.limesocial.io/v1"

    def post(self, platform, text, image_url, image_path):
        user = os.getenv(f"LIMESOCIAL_{platform.upper()}_USERNAME")
        if not user:
            raise RuntimeError(f"secret LIMESOCIAL_{platform.upper()}_USERNAME not set")
        body = {"title": text, "accounts": [{"platform": platform, "username": user}]}
        if image_url:
            path, body["mediaUrl"] = "/post/image", [image_url]
        elif platform == "linkedin":
            path = "/post/text"
        else:
            raise RuntimeError("Instagram needs an image")
        r = requests.post(self.base + path, headers={"Authorization": os.environ["LIMESOCIAL_API_KEY"]}, json=body, timeout=120)
        j = r.json() if r.content else {}
        if not r.ok or j.get("success") is False:
            raise RuntimeError(f"{r.status_code} {str(j.get('error') or j)[:200]}")
        return f"queued {j.get('data', {}).get('request_id')}"


class SocialAPI:
    """SocialAPI.ai (keys start with sapi_key_). Supports Instagram and LinkedIn, not Bluesky."""
    name, secrets, platforms = "socialapi", ["SOCIALAPI_KEY"], ("instagram", "linkedin")
    base = "https://api.social-api.ai/v1"

    def __init__(self):
        self._acc = None

    def _h(self):
        return {"Authorization": f"Bearer {os.environ['SOCIALAPI_KEY']}"}

    def post(self, platform, text, image_url, image_path):
        if self._acc is None:
            r = requests.get(f"{self.base}/accounts", headers=self._h(), timeout=60)
            r.raise_for_status()
            self._acc = {}
            for a in r.json().get("data", []):
                self._acc.setdefault(a["platform"], a["id"])
        if platform not in self._acc:
            raise RuntimeError("account not connected")
        body = {"text": text, "publish_now": True, "targets": [{"account_id": self._acc[platform]}]}
        if image_url:
            body["media"] = [{"source_type": "url", "source": image_url}]
        elif platform == "instagram":
            raise RuntimeError("Instagram needs an image")
        r = requests.post(f"{self.base}/posts", headers=self._h(), json=body, timeout=120)
        j = r.json() if r.content else {}
        if r.status_code != 201:      # 207 = partial, 422 = all targets failed
            errs = [t.get("error") for t in j.get("targets", []) if t.get("error")] or [j]
            raise RuntimeError(f"{r.status_code} {str(errs)[:200]}")
        return f"publishing {j.get('id')}"


class BlueskyDirect:
    name, secrets, platforms = "bluesky-direct", ["BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"], ("bluesky",)
    multi_image = True
    alt = None      # set by publish_draft before posting

    def post(self, platform, text, image_url, image_path, images=None):
        return direct.bluesky(text, image_path, alt=self.alt, images=[{"path": i["path"], "alt": i["alt"]} for i in images] if images else None)


PROVIDERS = [Buffer, Zernio, UploadPost, LimeSocial, SocialAPI, BlueskyDirect]


def image_alt(draft):
    """Honest alt text: say what the image really is (a designed card with the hook, an AI image, or the owner's own design)."""
    img = draft.get("image") or {}
    try:
        hook = draft["hooks"][draft.get("chosen_hook", 0)]["text"]
    except Exception:
        hook = draft.get("topic") or ""
    if img.get("ai_generated"):
        return f"AI-generated illustration for a post about: {hook}"[:1000]
    return f"Graphic with the text: {hook}"[:1000] if hook else "Graphic for the post"


def choose_order(provs, today=None):
    """PUBLISHER_ORDER (e.g. 'buffer,zernio') pins which tools are used and in what order, with no daily rotation.
    Unset = the original behaviour: use every tool that has secrets and rotate the first choice daily."""
    wanted = [n.strip().lower() for n in (os.getenv("PUBLISHER_ORDER") or "").split(",") if n.strip()]
    if wanted:
        by_name = {p.name: p for p in provs}
        pinned = [by_name[n] for n in wanted if n in by_name]
        if pinned:
            return pinned
    day = (today or dt.date.today()).timetuple().tm_yday
    start = day % len(provs)      # rotate the first choice daily
    return provs[start:] + provs[:start]


def choose_linkedin_order(provs, general):
    """LinkedIn only (Instagram and Bluesky keep `general`). The same tool every day, so timing and look stay consistent.
    LINKEDIN_PUBLISHER_ORDER (e.g. 'buffer' or 'buffer,zernio') pins it: only those tools are used, in that order.
    Not set: Buffer goes first and the other tools are a fallback ONLY if Buffer fails. If you pinned all platforms with
    PUBLISHER_ORDER and did not set a LinkedIn order, LinkedIn follows that pin."""
    by_name = {p.name: p for p in provs}
    wanted = [n.strip().lower() for n in (os.getenv("LINKEDIN_PUBLISHER_ORDER") or "").split(",") if n.strip()]
    pinned = [by_name[n] for n in wanted if n in by_name]
    if pinned:
        return pinned
    if (os.getenv("PUBLISHER_ORDER") or "").strip() or "buffer" not in by_name:
        return general
    return [by_name["buffer"]] + [p for p in general if p.name != "buffer"]


def publish_draft(draft):
    """Returns {platform: {"ok": bool, "detail": str}}."""
    provs = [P() for P in PROVIDERS if all(os.getenv(s) for s in P.secrets)]
    if not provs:
        return {p: {"ok": False, "detail": "no publisher secrets configured"} for p in config.PLATFORMS}
    order = choose_order(provs)
    alt = image_alt(draft)
    for prov in order:
        prov.alt = alt
    image_path = (draft.get("image") or {}).get("path")
    image_url = f"https://raw.githubusercontent.com/{config.REPO}/{config.BRANCH}/{image_path}" if image_path else None
    results = {}
    manual_ig = draft.get("instagram_mode") == "manual_reel"
    car = draft.get("carousel") or {}
    raw = lambda rel: f"https://raw.githubusercontent.com/{config.REPO}/{config.BRANCH}/{rel}"

    def slides_for(p):
        """Every slide for Instagram and LinkedIn; Bluesky allows 4 images, so it gets the planned subset. None = a normal single-image post."""
        paths, alts = car.get("paths") or [], car.get("alts") or []
        if len(paths) < 2:
            return None
        idx = (car.get("bluesky") or list(range(min(4, len(paths))))) if p == "bluesky" else list(range(len(paths)))
        return [{"url": raw(paths[i]), "path": paths[i], "alt": alts[i] if i < len(alts) else image_alt(draft)} for i in idx if i < len(paths)]

    for p in config.PLATFORMS:
        if p == "instagram" and manual_ig:      # Wednesday: you post the reel yourself
            continue
        if p == "instagram" and not image_url:
            results[p] = {"ok": False, "detail": "Instagram needs an image and none was generated"}
            continue
        img_url, img_path = (None, None) if (p == "linkedin" and draft.get("linkedin_format") == "text") else (image_url, image_path)
        multi = slides_for(p) if img_url else None

        def attempt(images):
            errors = []
            for prov in (choose_linkedin_order(provs, order) if p == "linkedin" else order):
                if getattr(prov, "platforms", None) and p not in prov.platforms:
                    continue
                if images and not getattr(prov, "multi_image", False):
                    continue                                  # this tool cannot post several images
                try:
                    done = prov.post(p, draft["posts"][p], img_url, img_path, images=images) if images else prov.post(p, draft["posts"][p], img_url, img_path)
                    return f"{prov.name}: {done}" + (f" ({len(images)} slides)" if images else ""), errors
                except Exception as e:
                    errors.append(f"{prov.name}: {str(e)[:120]}")
            return None, errors

        detail, errors = attempt(multi)
        if detail is None and multi:                          # the carousel could not go out: the post still goes out as the single hook image
            single, more = attempt(None)
            if single:
                detail = f"{single} (single image; carousel failed: {' | '.join(errors)[:160] or 'no tool that can post several images'})"
            errors += more
        results[p] = {"ok": True, "detail": detail} if detail else {"ok": False, "detail": " | ".join(errors)[:400] or "no publisher available"}
    return results
