"""Publishers: Buffer, Zernio, Upload-Post. Rotates the first-choice tool daily and falls back per platform."""
import datetime as dt
import os
import requests
from . import buffer, config, direct


class Buffer:
    name, secrets = "buffer", ["BUFFER_API_KEY"]

    def __init__(self):
        self._ch = None

    def post(self, platform, text, image_url, image_path):
        if self._ch is None:
            self._ch = buffer.channel_map()
        if platform not in self._ch:
            raise RuntimeError("channel not connected")
        p = buffer.create_post(self._ch[platform], text, image_url)
        return f"queued {p.get('id')}"


class Zernio:
    name, secrets = "zernio", ["ZERNIO_API_KEY"]
    base = "https://zernio.com/api/v1"

    def __init__(self):
        self._acc = None

    def _h(self):
        return {"Authorization": f"Bearer {os.environ['ZERNIO_API_KEY']}"}

    def post(self, platform, text, image_url, image_path):
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
        if image_url:
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

    def post(self, platform, text, image_url, image_path):
        return direct.bluesky(text, image_path)


PROVIDERS = [Buffer, Zernio, UploadPost, LimeSocial, SocialAPI, BlueskyDirect]


def publish_draft(draft):
    """Returns {platform: {"ok": bool, "detail": str}}."""
    provs = [P() for P in PROVIDERS if all(os.getenv(s) for s in P.secrets)]
    if not provs:
        return {p: {"ok": False, "detail": "no publisher secrets configured"} for p in config.PLATFORMS}
    start = dt.date.today().timetuple().tm_yday % len(provs)      # rotate the first choice daily
    order = provs[start:] + provs[:start]
    image_path = (draft.get("image") or {}).get("path")
    image_url = f"https://raw.githubusercontent.com/{config.REPO}/{config.BRANCH}/{image_path}" if image_path else None
    results = {}
    for p in config.PLATFORMS:
        if p == "instagram" and not image_url:
            results[p] = {"ok": False, "detail": "Instagram needs an image and none was generated"}
            continue
        errors = []
        for prov in order:
            if getattr(prov, "platforms", None) and p not in prov.platforms:
                continue
            try:
                results[p] = {"ok": True, "detail": f"{prov.name}: {prov.post(p, draft['posts'][p], image_url, image_path)}"}
                break
            except Exception as e:
                errors.append(f"{prov.name}: {str(e)[:120]}")
        else:
            results[p] = {"ok": False, "detail": " | ".join(errors)[:400]}
    return results
