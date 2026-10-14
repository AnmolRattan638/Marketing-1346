"""Offline tests for the analytics sync. Fixtures mirror the documented response shapes of the Bluesky public API,
the Instagram Graph API (insights + refresh) and Zernio's GET /v1/analytics. No network, no keys."""
import datetime as dt, json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import requests
from src import analytics as A, config, llm
from src.agents import strategist

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
SECRET = "IGQWRSECRETTOKEN1234567890"


class Resp:
    def __init__(self, j=None, status=200):
        self._j, self.status_code, self.content, self.text = j, status, b"x", json.dumps(j)

    def json(self):
        return self._j


def fresh_dirs():
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "drafts").mkdir()
    config.DATA, config.DRAFTS = tmp, tmp / "drafts"
    return tmp


def iso(days_ago, hour=6):
    return (NOW - dt.timedelta(days=days_ago)).replace(hour=hour).strftime("%Y-%m-%dT%H:%M:%S+0000")


# ------------------------------------------------------------------ fake APIs
def bsky_get(url, params=None, headers=None, timeout=None):
    me = {"did": "did:plc:me", "handle": "ar.bsky.social"}
    if url.endswith("getProfile"):
        return Resp({"followersCount": 21, "followsCount": 40, "postsCount": 12})
    return Resp({"feed": [
        {"post": {"uri": "at://did:plc:me/app.bsky.feed.post/3kaaa", "author": me, "likeCount": 4, "replyCount": 1, "repostCount": 2, "quoteCount": 1,
                  "record": {"text": "A 5-field contact form feels like homework on a phone screen", "createdAt": "2026-10-10T08:12:00.000Z"}}},
        {"post": {"uri": "at://did:plc:other/app.bsky.feed.post/3kbbb", "author": {"handle": "someone.else"}, "likeCount": 99, "record": {"text": "x", "createdAt": "2026-10-11T08:00:00.000Z"}},
         "reason": {"$type": "app.bsky.feed.defs#reasonRepost"}},                                   # a repost: must be skipped
    ]})


def ig_get_factory(fail_batch_for=None, expired=False, refresh_token="NEW" + SECRET):
    media = [
        {"id": "m_reel", "caption": "Long contact form dekh kar customers page chhod dete hain.\n\n#web", "media_type": "VIDEO", "media_product_type": "REELS",
         "permalink": "https://instagram.com/reel/1", "timestamp": iso(2), "like_count": 3, "comments_count": 1},
        {"id": "m_img", "caption": "Old image post about something", "media_type": "IMAGE", "media_product_type": "FEED",
         "permalink": "https://instagram.com/p/2", "timestamp": iso(5), "like_count": 1, "comments_count": 0},
        {"id": "m_story", "caption": "", "media_type": "IMAGE", "media_product_type": "STORY", "timestamp": iso(1)},
        {"id": "m_old", "caption": "ancient", "media_type": "IMAGE", "media_product_type": "FEED", "timestamp": iso(200)},
    ]
    values = {"m_reel": {"reach": 250, "views": 614, "likes": 37, "comments": 16, "shares": 20, "saved": 4, "total_interactions": 77,
                         "ig_reels_avg_watch_time": 11000, "reels_skip_rate": 63.6},
              "m_img": {}}                                                    # Meta returns an EMPTY set when data is unavailable

    def get(url, params=None, headers=None, timeout=None):
        params = params or {}
        if expired:
            return Resp({"error": {"message": "Error validating access token: Session has expired", "code": 190, "type": "OAuthException"}}, 400)
        if "refresh_access_token" in url:
            return Resp({"access_token": refresh_token, "token_type": "bearer", "expires_in": 5183944})
        if url.endswith("/me"):
            return Resp({"username": "ar_designs", "followers_count": 8, "follows_count": 14, "media_count": 6})
        if url.endswith("/me/media"):
            return Resp({"data": media})
        mid = url.split("/")[-2]
        metric = params["metric"]
        if fail_batch_for == mid and "," in metric:                           # one unsupported metric fails the whole batch
            return Resp({"error": {"message": "(#100) metric not supported for this media", "code": 100}}, 400)
        data = [{"name": m, "period": "lifetime", "values": [{"value": values[mid][m]}]} for m in metric.split(",") if m in values.get(mid, {})]
        return Resp({"data": data})
    return get


def zernio_get_factory(status=200, access=True):
    def get(url, params=None, headers=None, timeout=None):
        assert headers["Authorization"] == "Bearer zk_test", headers
        if status != 200:
            return Resp({"error": "x"}, status)
        return Resp({"hasAnalyticsAccess": access, "pagination": {"page": 1, "pages": 1},
                     "accounts": [{"platform": "linkedin", "isActive": True, "followersCount": 55, "username": "anmol"}],
                     "posts": [
                         {"_id": "z1", "content": "Still losing leads to long contact forms? Most mobile visitors bounce.", "publishedAt": iso(3), "platform": "linkedin",
                          "mediaType": "image",
                          "platforms": [{"platform": "linkedin", "platformPostId": "urn:li:share:1", "status": "published", "syncStatus": "synced",
                                         "platformPostUrl": "https://linkedin.com/feed/update/1",
                                         "analytics": {"impressions": 410, "reach": 0, "views": 0, "likes": 9, "comments": 2, "shares": 1, "saves": 0, "clicks": 0,
                                                       "reelsSkipRate": 0, "igReelsAvgWatchTime": 0}}]},
                         {"_id": "z2", "content": "Instagram caption posted through Zernio about chatbots for hotels", "publishedAt": iso(2), "platform": "instagram",
                          "mediaProductType": "REELS",
                          "platforms": [{"platform": "instagram", "platformPostId": "999", "status": "published", "syncStatus": "pending", "analytics": {"likes": 0}}]},
                         {"_id": "z3", "content": "A boosted ad", "publishedAt": iso(2), "platform": "instagram", "isAd": True, "platforms": []},
                     ]})
    return get


def router(*getters):
    def get(url, params=None, headers=None, timeout=None):
        if "public.api.bsky.app" in url:
            return getters[0](url, params, headers, timeout)
        if "instagram.com" in url:
            return getters[1](url, params, headers, timeout)
        return getters[2](url, params, headers, timeout)
    return get


ENV_ALL = {"BLUESKY_HANDLE": "ar.bsky.social", "IG_ACCESS_TOKEN": SECRET, "ZERNIO_API_KEY": "zk_test"}

# ------------------------------------------------------------------ 1. collectors
rows, acct = A.collect_bluesky("@ar.bsky.social", bsky_get)
assert len(rows) == 1 and rows[0]["metrics"]["likes"] == 4 and rows[0]["metrics"]["shares"] == 3 and acct["bluesky"]["followers"] == 21, rows
assert rows[0]["metrics"]["reach"] is None, "Bluesky has no reach: must be n/a, not 0"
try:
    A.collect_bluesky("me@gmail.com", bsky_get)
    raise SystemExit("email handle must be rejected")
except A.AnalyticsError as e:
    assert "email" in str(e)

rows, acct = A.collect_instagram(SECRET, ig_get_factory(fail_batch_for="m_reel"), now=NOW)
by = {r["id"]: r for r in rows}
assert set(by) == {"m_reel", "m_img"}, "stories and posts older than 60 days must be skipped"
reel = by["m_reel"]["metrics"]
assert reel["views"] == 614 and reel["shares"] == 20 and reel["saves"] == 4 and reel["avg_watch_s"] == 11 and reel["skip_rate"] == 63.6, reel
assert by["m_reel"]["format"] == "reel" and by["m_img"]["format"] == "image"
img = by["m_img"]["metrics"]
assert img["reach"] is None and img["views"] is None and img["shares"] is None, "empty insights must stay n/a, never 0"
assert img["likes"] == 1 and img["comments"] == 0, "like_count/comments_count from the media list are the fallback"
assert acct["instagram"]["followers"] == 8

zrows, zacc = A.collect_zernio("zk_test", zernio_get_factory(), now=NOW)
zb = {r["id"]: r for r in zrows}
assert "z3" not in zb and len(zrows) == 2, "ads are excluded"
li = zb["urn:li:share:1"]["metrics"]
assert li["impressions"] == 410 and li["reach"] is None and li["views"] is None and li["skip_rate"] is None, "Zernio's 0 for 'not provided' must become n/a"
assert zb["999"]["metrics"]["likes"] is None, "a pending sync must not report numbers"
assert zacc["linkedin"]["followers"] == 55
for status, access in ((402, True), (200, False)):
    try:
        A.collect_zernio("zk_test", zernio_get_factory(status, access), now=NOW)
        raise SystemExit("plan problem must raise")
    except A.AnalyticsError as e:
        assert e.plan

# ------------------------------------------------------------------ 2. full sync: merge, matching, storage
tmp = fresh_dirs()
config.save_json(config.DRAFTS / "2026-10-11.json", {"date": "2026-10-11", "status": "published", "service": "chatbot", "topic": "The Friction-Free Enquiry", "hook_style": "Question",
                                                      "posts": {"instagram": "Long contact form dekh kar customers page chhod dete hain.\n\n",
                                                                "linkedin": "Still losing leads to long contact forms? Most mobile visitors bounce.",
                                                                "bluesky": "A 5-field contact form feels like homework on a phone screen"}})
alerts = []
data = A.sync(env=ENV_ALL, get=router(bsky_get, ig_get_factory(), zernio_get_factory()), now=NOW, alert=alerts.append)
cov = data["coverage"]
assert cov["instagram"]["source"] == "instagram", "the direct Instagram source beats Zernio when both work"
assert cov["bluesky"]["source"] == "bluesky" and cov["linkedin"]["source"] == "zernio"
plat = {(r["platform"], r["id"]): r for r in data["posts"]}
assert ("instagram", "999") not in plat, "Zernio's Instagram rows are ignored when the direct source works"
for key in (("instagram", "m_reel"), ("linkedin", "urn:li:share:1"), ("bluesky", "at://did:plc:me/app.bsky.feed.post/3kaaa")):
    assert plat[key]["matched"] and plat[key]["matched"]["service"] == "chatbot", (key, plat[key]["matched"])
assert plat[("instagram", "m_img")]["matched"] is None
assert data["accounts"]["linkedin"]["followers"] == 55 and data["accounts"]["instagram"]["followers"] == 8
assert data["ig_token"]["changed"] is True and data["ig_token"]["expires_at"], "weekly refresh recorded"
assert any("different token" in a for a in alerts)
raw = (tmp / "analytics.json").read_text()
assert SECRET not in raw and "NEW" + SECRET not in raw and "zk_test" not in raw, "no secret may ever reach the committed file"

# no commit churn: same data, a few hours later the same day -> file untouched
before = (tmp / "analytics.json").read_bytes()
A.sync(env=ENV_ALL, get=router(bsky_get, ig_get_factory(), zernio_get_factory()), now=NOW + dt.timedelta(hours=5), alert=alerts.append)
assert (tmp / "analytics.json").read_bytes() == before, "an unchanged sync must not rewrite the file"
A.sync(env=ENV_ALL, get=router(bsky_get, ig_get_factory(), zernio_get_factory()), now=NOW + dt.timedelta(days=1), alert=alerts.append)
assert (tmp / "analytics.json").read_bytes() != before, "a new day adds a follower snapshot"

# ------------------------------------------------------------------ 3. fallbacks and failure isolation
tmp = fresh_dirs()
data = A.sync(env={"ZERNIO_API_KEY": "zk_test"}, get=zernio_get_factory(), now=NOW, alert=alerts.append)
assert data["coverage"]["instagram"]["source"] == "zernio", "no IG token: Zernio is the Instagram fallback"
assert data["coverage"]["bluesky"]["source"] == "zernio" and "no posts found" in data["coverage"]["bluesky"]["note"], "Zernio is also the Bluesky fallback"
assert data["sources"]["bluesky"]["ok"] is None and data["sources"]["instagram"]["ok"] is None

tmp = fresh_dirs()                                           # nothing configured at all: no crash, every platform says so
data = A.sync(env={}, get=(lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network call expected"))), now=NOW, alert=alerts.append)
assert all(c["ok"] is False and "no automatic source" in c["note"] for c in data["coverage"].values()), data["coverage"]
assert all(s["ok"] is None for s in data["sources"].values()) and data["posts"] == []

tmp = fresh_dirs()
alerts.clear()
data = A.sync(env=ENV_ALL, get=router(bsky_get, ig_get_factory(expired=True), zernio_get_factory(402)), now=NOW, alert=alerts.append)
assert data["sources"]["bluesky"]["ok"] and data["sources"]["instagram"]["ok"] is False and data["sources"]["zernio"]["ok"] is False
assert data["coverage"]["bluesky"]["ok"], "Bluesky still synced although the others failed"
assert data["coverage"]["linkedin"]["ok"] is False and "plan" in data["coverage"]["linkedin"]["note"]
assert len([a for a in alerts if "expired" in a]) == 1
A.sync(env=ENV_ALL, get=router(bsky_get, ig_get_factory(expired=True), zernio_get_factory(402)), now=NOW + dt.timedelta(hours=6), alert=alerts.append)
assert len([a for a in alerts if "expired" in a]) == 1, "the expired-token alert fires once, not every sync"

# an exception that carries the token in its text is scrubbed before it is stored
def leaky(url, params=None, headers=None, timeout=None):
    raise requests.exceptions.ConnectionError(f"HTTPSConnectionPool: {url}?access_token={SECRET}&fields=x")
tmp = fresh_dirs()
data = A.sync(env={"IG_ACCESS_TOKEN": SECRET}, get=leaky, now=NOW, alert=lambda m: None)
assert SECRET not in json.dumps(data) and "***" in data["sources"]["instagram"]["error"], data["sources"]["instagram"]

# a failing source keeps the last good rows (marked stale) and alerts exactly once, on the second failure
tmp = fresh_dirs()
alerts.clear()
env = {"BLUESKY_HANDLE": "ar.bsky.social"}
A.sync(env=env, get=bsky_get, now=NOW, alert=alerts.append)
down = lambda url, params=None, headers=None, timeout=None: Resp({}, 503)
for i in range(1, 5):
    d = A.sync(env=env, get=down, now=NOW + dt.timedelta(hours=6 * i), alert=alerts.append)
    assert len(d["posts"]) == 1 and d["coverage"]["bluesky"]["ok"] is False and d["coverage"]["bluesky"]["stale_since"]
assert len([a for a in alerts if "failed twice" in a]) == 1, alerts

# token about to expire: one alert per day
tmp = fresh_dirs()
alerts.clear()
config.save_json(tmp / "analytics.json", {"ig_token": {"checked_at": NOW.isoformat(), "expires_at": (NOW + dt.timedelta(days=5)).isoformat()}})
for hrs in (0, 3, 6):          # all within one day (a new day deliberately re-sends the reminder)
    A.sync(env={"IG_ACCESS_TOKEN": SECRET}, get=ig_get_factory(), now=NOW + dt.timedelta(hours=hrs), alert=alerts.append)
assert len([a for a in alerts if "expires in" in a]) == 1, alerts

# ------------------------------------------------------------------ 4. weak-signal detection
def post(plat, pid, days, eng_likes, reach, fmt="image", skip=None, hook="Stat", svc="website", hours=None, none=False):
    t = (NOW - dt.timedelta(hours=hours)) if hours else (NOW - dt.timedelta(days=days))
    m = {k: None for k in A.METRICS}
    if not none:
        m.update(likes=eng_likes, comments=0, shares=0, saves=0, reach=reach, skip_rate=skip)
    return {"platform": plat, "id": pid, "url": None, "published_at": t.isoformat(), "text": pid, "format": fmt, "source": "t", "metrics": m,
            "matched": {"date": t.date().isoformat(), "service": svc, "hook_style": hook, "topic": f"topic {pid}"}}


data = {"updated_at": NOW.isoformat(), "accounts": {"instagram": {"followers": 8}, "bluesky": {"followers": 21}},
        "snapshots": [{"date": "2026-10-06", "followers": {"instagram": 8}}],
        "coverage": {"instagram": {"ok": True, "source": "instagram", "note": None}, "bluesky": {"ok": True, "source": "bluesky", "note": None},
                     "linkedin": {"ok": False, "source": None, "note": "no automatic source configured (add manual numbers to metrics.json)"}},
        "posts": [post("instagram", "fresh", None, 0, 10, fmt="reel", skip=90, hours=6),             # too fresh: ignored
                  post("instagram", "r1", 1.3, 0, 40, fmt="reel", skip=80, hook="Question", svc="chatbot"),
                  post("instagram", "r2", 2.2, 0, 55, fmt="reel", skip=70, hook="Question", svc="chatbot"),
                  post("instagram", "i1", 3, 0, 60),
                  post("instagram", "i2", 4, 6, 90),
                  post("instagram", "pending", 5, 0, 0, none=True)]}                                  # no numbers yet: must not count as zero
ids = {s["id"] for s in A.weak_signals(data, NOW)}
assert {"zero_engagement_streak", "high_skip_rate", "follower_stall", "weak_format", "weak_hook_style", "weak_service", "no_data"} <= ids, ids
streak = [s for s in A.weak_signals(data, NOW) if s["id"] == "zero_engagement_streak"][0]
assert "last 3 settled posts" in streak["detail"], streak
assert not any(s["platform"] == "bluesky" for s in A.weak_signals(data, NOW)), "an account with no posts must not be flagged"
text, sig = A.digest(data, NOW)
assert "WEAK SIGNALS" in text and "NO LIVE DATA" in text and "n/a" in text and "linkedin" in text, text
assert "fresh" not in text.split("WEAK SIGNALS")[0].split("best")[-1], "fresh posts must not be named as best/worst"
assert A.digest({}, NOW) == ("", [])

# healthy account: nothing flagged
good = {"updated_at": NOW.isoformat(), "accounts": {"instagram": {"followers": 100}}, "snapshots": [{"date": "2026-10-06", "followers": {"instagram": 90}}],
        "coverage": {"instagram": {"ok": True, "source": "instagram", "note": None}},
        "posts": [post("instagram", f"g{i}", i + 1.5, 10, 300, fmt="image") for i in range(5)]}
for r in good["posts"]:
    r["metrics"].update(shares=3, saves=2)                       # people share and save these posts
assert A.weak_signals(good, NOW) == [], A.weak_signals(good, NOW)

# ------------------------------------------------------------------ 5. the strategist receives the digest
seen = {}
llm.strategist_model = lambda prompt, system="", **k: seen.__setitem__("p", prompt) or json.dumps({"stage": "s", "summary": "x", "guidance": "g", "instructions": {}, "manual_tips": []})
strategist.guide([], {}, {"name": "Chatbot"}, "2026-10-13", {"facts_rules": []}, "DIGEST-MARK weak: hooks")
assert "DIGEST-MARK" in seen["p"] and "NOT zero" in seen["p"] and "weakest area" in seen["p"] and "Live analytics are NOT available" not in seen["p"]
strategist.guide([], {}, {"name": "Chatbot"}, "2026-10-13", {"facts_rules": []})
assert "Live analytics are NOT available" in seen["p"]
# manual stats grow every time the owner adds a screenshot's numbers: the END of a long file must still reach the strategist
strategist.guide([], {"filler": "x" * 6000, "linkedin": "TAIL-MARK-LINKEDIN"}, {"name": "Chatbot"}, "2026-10-13", {"facts_rules": []})
assert "TAIL-MARK-LINKEDIN" in seen["p"], "metrics.json was silently cut off before the end"
# bold-formatted drafts (Unicode bold) still match the posted text, whether the platform keeps the bold or flattens it
from src import captions as _C
bold_draft = {"date": "2026-10-12", "status": "published", "service": "chatbot", "topic": "T", "hook_style": "Q",
              "posts": {"instagram": _C.finalize("**STOP LOSING LEADS** to slow replies every single night\n\n→ more", bold_on=True)}}
for posted in (bold_draft["posts"]["instagram"], "STOP LOSING LEADS to slow replies every single night\n\n→ more"):
    row = {"platform": "instagram", "id": "x", "published_at": iso(1), "text": posted}
    assert A.match_drafts([row], [bold_draft])[0]["matched"]["service"] == "chatbot", posted
print("analytics test passed: collectors, merge, matching, no-zero-for-missing, isolation, scrubbing, alerts, weak signals, strategist")
