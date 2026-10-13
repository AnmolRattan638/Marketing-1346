"""Analytics sync: pull post and account numbers from every platform into data/analytics.json,
then boil them down to a short digest of what is weak, for the strategist.

Sources (each optional, each isolated: one failing never stops the others):
  bluesky   public Bluesky API, needs only BLUESKY_HANDLE (no password, no approval)
  instagram Instagram Graph API with IG_ACCESS_TOKEN (Instagram Login, instagram_business_manage_insights)
  zernio    Zernio analytics API with ZERNIO_API_KEY: the only automatic route to LinkedIn personal-profile numbers
            (LinkedIn reports only posts published through Zernio), and the Instagram fallback when there is no IG token

A metric the platform did not report is None ("n/a"), never 0: Meta returns an empty set when data is unavailable and
Zernio uses 0 for 'not provided', so a 0 from there is not trusted as a real zero for reach/impressions/views.
"""
import datetime as dt
import json
import os
import re
import statistics
import requests
from . import config

MAX_POSTS = 150
METRICS = ("impressions", "reach", "views", "likes", "comments", "shares", "saves", "clicks", "reposts",
           "skip_rate", "avg_watch_s", "duration_s")
SECRET_VARS = ("IG_ACCESS_TOKEN", "ZERNIO_API_KEY", "BLUESKY_APP_PASSWORD", "TELEGRAM_BOT_TOKEN")
DIRECT = {"instagram": "instagram", "bluesky": "bluesky"}      # platform -> its direct source (Zernio is the fallback)
MIN_AGE_H = 24          # posts younger than this are too fresh to judge (Meta data can also lag up to 48h)


class AnalyticsError(Exception):
    def __init__(self, msg, expired=False, plan=False):
        super().__init__(msg)
        self.expired, self.plan = expired, plan


# ---------------------------------------------------------------- small helpers
def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def _ts(s):
    if not s:
        return None
    s = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", str(s).replace("Z", "+00:00"))
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def _n(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _pos(x):
    x = _n(x)
    return x if x and x > 0 else None          # Zernio sends 0 for 'not provided'


def _norm(text):
    return re.sub(r"[\W_]+", "", (text or "").lower())


def _scrub(text, env):
    for k in SECRET_VARS:
        v = env.get(k)
        if v and len(v) > 6:
            text = text.replace(v, "***")
    return re.sub(r"access_token=[^&\s'\"]+", "access_token=***", text)


def _row(platform, pid, url, published_at, text, fmt, source, **m):
    return {"platform": platform, "id": str(pid), "url": url, "published_at": published_at,
            "text": (text or "")[:160], "format": fmt, "source": source, "metrics": {k: m.get(k) for k in METRICS}}


def engagement(m):
    """likes + 2*comments + 3*(shares+reposts) + 3*saves; None when the platform reported none of them."""
    if all(m.get(k) is None for k in ("likes", "comments", "shares", "saves")):
        return None
    g = lambda k: m.get(k) or 0
    return g("likes") + 2 * g("comments") + 3 * (g("shares") + g("reposts")) + 3 * g("saves")


def reach_of(m):
    for k in ("reach", "impressions", "views"):
        if m.get(k):
            return m[k]
    return None


# ---------------------------------------------------------------- collectors
def collect_bluesky(handle, get):
    handle = handle.strip().lstrip("@")
    if "@" in handle:
        raise AnalyticsError("BLUESKY_HANDLE looks like an email; set BLUESKY_PUBLIC_HANDLE to your handle (name.bsky.social)")
    base = "https://public.api.bsky.app/xrpc"
    pr = get(f"{base}/app.bsky.actor.getProfile", params={"actor": handle}, timeout=30)
    if pr.status_code >= 400:
        raise AnalyticsError(f"Bluesky profile lookup failed (HTTP {pr.status_code})")
    p = pr.json()
    acct = {"followers": _n(p.get("followersCount")), "following": _n(p.get("followsCount")), "posts": _n(p.get("postsCount"))}
    fr = get(f"{base}/app.bsky.feed.getAuthorFeed", params={"actor": handle, "filter": "posts_no_replies", "limit": 50}, timeout=30)
    if fr.status_code >= 400:
        raise AnalyticsError(f"Bluesky feed lookup failed (HTTP {fr.status_code})")
    rows = []
    for item in fr.json().get("feed", []):
        post = item.get("post") or {}
        if item.get("reason"):                                  # a repost of someone else's post
            continue
        if (post.get("author") or {}).get("handle", "").lower() != handle.lower():
            continue
        rec = post.get("record") or {}
        uri = post.get("uri", "")
        rows.append(_row("bluesky", uri, f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}", rec.get("createdAt"),
                         rec.get("text"), "text", "bluesky", likes=_n(post.get("likeCount")), comments=_n(post.get("replyCount")),
                         shares=(_n(post.get("repostCount")) or 0) + (_n(post.get("quoteCount")) or 0)))
    return rows, {"bluesky": acct}


def _graph(get, url, token, **params):
    r = get(url, params={**params, "access_token": token}, timeout=40)
    try:
        j = r.json()
    except ValueError:
        j = {}
    if r.status_code >= 400 or "error" in j:
        e = j.get("error") or {}
        msg = e.get("message") or (r.text or "")[:150]
        expired = e.get("code") == 190 or "expired" in msg.lower() or "invalid oauth" in msg.lower()
        raise AnalyticsError(f"Instagram API HTTP {r.status_code} code {e.get('code')}: {msg}"[:230], expired=expired)
    return j


def _parse_insights(j):
    out = {}
    for item in j.get("data", []):
        vals = item.get("values") or []
        v = vals[0].get("value") if vals else (item.get("total_value") or {}).get("value")
        if _n(v) is not None:
            out[item.get("name")] = v
    return out


def _ig_insights(get, base, token, media, budget):
    reel = media.get("media_product_type") == "REELS"
    metrics = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"]
    if reel:
        metrics += ["ig_reels_avg_watch_time", "reels_skip_rate"]
    try:
        budget[0] -= 1
        return _parse_insights(_graph(get, f"{base}/{media['id']}/insights", token, metric=",".join(metrics)))
    except AnalyticsError as e:
        if e.expired:
            raise
    out, fails = {}, 0                                           # one unsupported metric fails the whole call: retry one by one
    for m in metrics:
        if budget[0] <= 0 or fails >= 3:
            break
        try:
            budget[0] -= 1
            out.update(_parse_insights(_graph(get, f"{base}/{media['id']}/insights", token, metric=m)))
            fails = 0
        except AnalyticsError as e:
            if e.expired:
                raise
            fails += 1
    return out


def collect_instagram(token, get, version="v25.0", now=None, days=60):
    now = now or utcnow()
    base = f"https://graph.instagram.com/{version}"
    me = _graph(get, f"{base}/me", token, fields="username,followers_count,follows_count,media_count")
    acct = {"followers": _n(me.get("followers_count")), "following": _n(me.get("follows_count")), "posts": _n(me.get("media_count")),
            "username": me.get("username")}
    media = _graph(get, f"{base}/me/media", token, limit=50,
                   fields="id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count").get("data", [])
    budget, rows = [120], []
    for md in media:
        t = _ts(md.get("timestamp"))
        if not t or (now - t).days > days or md.get("media_product_type") == "STORY":
            continue
        ins = _ig_insights(get, base, token, md, budget) if budget[0] > 0 else {}
        fmt = {"REELS": "reel"}.get(md.get("media_product_type")) or {"CAROUSEL_ALBUM": "carousel", "IMAGE": "image", "VIDEO": "video"}.get(md.get("media_type"), "post")
        watch = ins.get("ig_reels_avg_watch_time")
        rows.append(_row("instagram", md["id"], md.get("permalink"), md.get("timestamp"), md.get("caption"), fmt, "instagram",
                         reach=ins.get("reach"), views=ins.get("views"),
                         likes=ins.get("likes", _n(md.get("like_count"))), comments=ins.get("comments", _n(md.get("comments_count"))),
                         shares=ins.get("shares"), saves=ins.get("saved"),
                         skip_rate=ins.get("reels_skip_rate"), avg_watch_s=(watch / 1000 if watch else None)))
    return rows, {"instagram": acct}


def refresh_instagram_token(token, get):
    """Long-lived tokens last 60 days; a refresh (allowed once the token is 24h old) restarts that clock."""
    r = get("https://graph.instagram.com/refresh_access_token", params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    j = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in j:
        raise AnalyticsError(f"token refresh refused: {(j.get('error') or {}).get('message', r.status_code)}"[:200])
    return {"expires_in": _n(j.get("expires_in")), "changed": bool(j.get("access_token")) and j["access_token"] != token}


def collect_zernio(key, get, now=None, days=60):
    now = now or utcnow()
    base, h = "https://zernio.com/api/v1", {"Authorization": f"Bearer {key}"}
    rows, accounts = [], {}
    for page in range(1, 6):
        r = get(f"{base}/analytics", headers=h, timeout=60,
                params={"fromDate": (now - dt.timedelta(days=days)).date().isoformat(), "limit": 100, "page": page})
        if r.status_code == 402:
            raise AnalyticsError("Zernio analytics are not enabled on this plan (HTTP 402)", plan=True)
        if r.status_code == 401:
            raise AnalyticsError("ZERNIO_API_KEY was rejected (HTTP 401)")
        if r.status_code >= 400:
            raise AnalyticsError(f"Zernio analytics HTTP {r.status_code}")
        j = r.json()
        if j.get("hasAnalyticsAccess") is False:
            raise AnalyticsError("Zernio analytics are not enabled on this plan (hasAnalyticsAccess=false)", plan=True)
        for a in j.get("accounts") or []:
            if a.get("isActive", True) and _n(a.get("followersCount")) is not None:
                accounts.setdefault(a.get("platform"), {"followers": a["followersCount"], "username": a.get("username")})
        for p in j.get("posts") or []:
            if p.get("isAd"):
                continue
            entries = p.get("platforms") or [{"platform": p.get("platform"), "platformPostId": p.get("_id"), "analytics": p.get("analytics"),
                                              "platformPostUrl": p.get("platformPostUrl"), "syncStatus": "synced", "status": "published"}]
            for e in entries:
                if e.get("status") == "failed" or not e.get("platform"):
                    continue
                an = e.get("analytics") or {}
                ok = e.get("syncStatus", "synced") == "synced" and bool(an)
                fmt = ("reel" if p.get("mediaProductType") == "REELS" else p.get("mediaType") or "post")
                m = dict(impressions=_pos(an.get("impressions")), reach=_pos(an.get("reach")), views=_pos(an.get("views")),
                         likes=_n(an.get("likes")), comments=_n(an.get("comments")), shares=_n(an.get("shares")), saves=_n(an.get("saves")),
                         clicks=_n(an.get("clicks")), skip_rate=_pos(an.get("reelsSkipRate")),
                         avg_watch_s=(_pos(an.get("igReelsAvgWatchTime")) or 0) / 1000 or None, duration_s=_n(an.get("videoDurationSeconds"))) if ok else {}
                rows.append(_row(e["platform"], e.get("platformPostId") or p.get("_id"), e.get("platformPostUrl") or p.get("platformPostUrl"),
                                 p.get("publishedAt"), p.get("content"), fmt, "zernio", **m))
        if page >= ((j.get("pagination") or {}).get("pages") or 1):
            break
    return rows, accounts


# ---------------------------------------------------------------- matching posts to the drafts that produced them
def match_drafts(rows, drafts):
    """Attach {date, service, hook_style, topic} to each row by comparing the start of the text (fallback: the one same-day post)."""
    index = {}
    for d in drafts:
        if d.get("status") in ("published", "partial"):
            for plat, text in (d.get("posts") or {}).items():
                key = _norm(text)[:40]
                if len(key) >= 20:
                    index[(plat, key)] = d
    for r in rows:
        d = index.get((r["platform"], _norm(r.get("text"))[:40])) if len(_norm(r.get("text"))) >= 20 else None
        if d is None:                                           # fallback: exactly one draft and one post that day
            t = _ts(r.get("published_at"))
            same = [x for x in drafts if x.get("status") in ("published", "partial") and t and x.get("date") == t.date().isoformat()]
            peers = [x for x in rows if x["platform"] == r["platform"] and _ts(x.get("published_at")) and t and _ts(x["published_at"]).date() == t.date()]
            d = same[0] if len(same) == 1 and len(peers) == 1 else None
        r["matched"] = {k: d.get(k) for k in ("date", "service", "hook_style", "topic")} if d else None
    return rows


# ---------------------------------------------------------------- storage
def path():
    return config.DATA / "analytics.json"


def load():
    return config.load_json(path(), {})


def _core(d):
    return json.dumps({k: d.get(k) for k in ("accounts", "posts", "snapshots", "coverage", "sources", "ig_token", "alerts")}, sort_keys=True, default=str)


def _default_alert(msg):
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from . import tg
        tg.send(msg)
    else:
        print("ALERT:", msg)


def sync(env=None, get=None, now=None, alert=None):
    """Run every configured source, merge, match to drafts, save. Never raises for a source failure. Returns the data dict."""
    env, get, now, alert = env or os.environ, get or requests.get, now or utcnow(), alert or _default_alert
    old = load()
    prev_src = old.get("sources") or {}
    results, sources = {}, {}
    plan = {
        "bluesky": (env.get("BLUESKY_PUBLIC_HANDLE") or env.get("BLUESKY_HANDLE"), lambda v: collect_bluesky(v, get)),
        "instagram": (env.get("IG_ACCESS_TOKEN"), lambda v: collect_instagram(v, get, env.get("IG_API_VERSION") or "v25.0", now)),
        "zernio": (env.get("ZERNIO_API_KEY"), lambda v: collect_zernio(v, get, now)),
    }
    expired = {}
    for name, (secret, fn) in plan.items():
        if not secret:
            sources[name] = {"ok": None, "error": "not configured", "fails": 0}
            continue
        try:
            results[name] = fn(secret)
            sources[name] = {"ok": True, "error": None, "fails": 0}
        except Exception as e:                                  # one platform failing must never stop the rest
            msg = _scrub(str(e), env)[:220]
            sources[name] = {"ok": False, "error": msg, "fails": (prev_src.get(name) or {}).get("fails", 0) + 1}
            expired[name] = bool(getattr(e, "expired", False))
    # --- merge: per platform, the direct source if it worked, else Zernio, else keep the previous rows (marked stale)
    platforms = list(config.PLATFORMS)
    rows, accounts, coverage = [], dict(old.get("accounts") or {}), {}
    for p in platforms:
        chosen = next((s for s in (DIRECT.get(p), "zernio") if s and s in results), None)
        if chosen:
            prows = [r for r in results[chosen][0] if r["platform"] == p]
            accounts[p] = {**(accounts.get(p) or {}), **{k: v for k, v in (results[chosen][1].get(p) or {}).items() if v is not None}}
            note = None
            if not prows and chosen == "zernio":
                note = ("connected through Zernio but no posts found" + (" (LinkedIn only reports posts published through Zernio)" if p == "linkedin" else ""))
            coverage[p] = {"source": chosen, "ok": True, "note": note}
            rows += prows
        else:
            tried = [s for s in (DIRECT.get(p), "zernio") if s and sources[s]["ok"] is False]
            coverage[p] = {"source": None, "ok": False,
                           "note": ("source failing: " + sources[tried[0]]["error"]) if tried else "no automatic source configured (add manual numbers to metrics.json)"}
            kept = [r for r in old.get("posts", []) if r["platform"] == p]
            if kept:
                coverage[p]["stale_since"] = old.get("updated_at")
            rows += kept
    drafts = [config.load_json(f, {}) for f in sorted(config.DRAFTS.glob("*.json"))] if config.DRAFTS.exists() else []
    rows = match_drafts(rows, [d for d in drafts if isinstance(d, dict)])
    rows.sort(key=lambda r: r.get("published_at") or "", reverse=True)
    data = {"posts": rows[:MAX_POSTS], "accounts": accounts, "coverage": coverage, "sources": sources}
    # --- daily follower snapshot, last 90 days
    snaps = [s for s in old.get("snapshots", []) if s.get("date") != now.date().isoformat()]
    snaps.append({"date": now.date().isoformat(), "followers": {p: a.get("followers") for p, a in accounts.items() if a.get("followers") is not None}})
    data["snapshots"] = snaps[-90:]
    # --- Instagram token keep-alive (weekly) and expiry tracking
    tok, igt = env.get("IG_ACCESS_TOKEN"), dict(old.get("ig_token") or {})
    checked = _ts(igt.get("checked_at"))
    if tok and sources["instagram"]["ok"] and (not checked or (now - checked).days >= 6):
        try:
            rf = refresh_instagram_token(tok, get)
            igt.update(checked_at=now.isoformat(timespec="seconds"), changed=rf["changed"],
                       expires_at=(now + dt.timedelta(seconds=rf["expires_in"])).isoformat(timespec="seconds") if rf["expires_in"] else igt.get("expires_at"))
        except Exception as e:
            igt["refresh_error"] = _scrub(str(e), env)[:160]
    data["ig_token"] = igt
    # --- alerts (each fires once, not every sync)
    sent = dict(old.get("alerts") or {})
    day = now.date().isoformat()

    def once(key, msg, daily=False):
        marker = day if daily else "sent"
        if sent.get(key) != marker:
            alert(msg)
            sent[key] = marker
    for name, s in sources.items():
        if s["ok"]:
            for k in [k for k in sent if k.startswith(name + ":")]:
                sent.pop(k)
        elif s["ok"] is False:
            if expired.get(name):
                once(f"{name}:expired", "Analytics sync: the Instagram access token has expired or is invalid. Generate a new long-lived token and update the IG_ACCESS_TOKEN secret. Until then the strategist has no Instagram numbers.")
            elif s["fails"] == 2:
                once(f"{name}:failing", f"Analytics sync: {name} has failed twice in a row: {s['error']}")
    exp = _ts(igt.get("expires_at"))
    if exp and (exp - now).days <= 10:
        once("ig_token:expiring", f"Analytics sync: the Instagram token expires in {max((exp - now).days, 0)} days and could not be extended. Generate a new one and update IG_ACCESS_TOKEN.", daily=True)
    if igt.get("changed"):
        once("ig_token:changed", "Analytics sync: Instagram returned a different token string when refreshing. The saved IG_ACCESS_TOKEN may stop working about 60 days after it was created; generate a new long-lived token and update the secret.")
    data["alerts"] = sent
    # --- write only when something real changed (no commit noise from timestamps)
    if _core(data) != _core(old):
        data["updated_at"] = now.isoformat(timespec="seconds")
        config.save_json(path(), data)
    else:
        data["updated_at"] = old.get("updated_at") or now.isoformat(timespec="seconds")
    return data


# ---------------------------------------------------------------- what is weak?
def _age_h(r, now):
    t = _ts(r.get("published_at"))
    return (now - t).total_seconds() / 3600 if t else None


def _delta(data, p, days, now):
    cur = (data.get("accounts", {}).get(p) or {}).get("followers")
    if cur is None:
        return None
    best = None
    for s in data.get("snapshots", []):
        f, t = (s.get("followers") or {}).get(p), _ts(s.get("date"))
        if f is None or not t:
            continue
        gap = abs((now - t).days - days)
        if gap <= max(2, days // 3) and (best is None or gap < best[0]):
            best = (gap, f)
    return None if best is None else cur - best[1]


def weak_signals(data, now=None):
    """Deterministic findings from the numbers (no LLM): the strategist is told these facts, it does not have to find them."""
    now, sig = now or utcnow(), []
    posts = data.get("posts", [])
    for p, cov in (data.get("coverage") or {}).items():
        if not cov.get("ok"):
            sig.append({"id": "no_data", "platform": p, "detail": f"no live numbers ({cov.get('note')}); do not read missing data as zero"})
        elif cov.get("note"):
            sig.append({"id": "no_posts_seen", "platform": p, "detail": cov["note"]})
    for p in (data.get("coverage") or {}):
        mature = [r for r in posts if r["platform"] == p and (_age_h(r, now) or 0) >= MIN_AGE_H and engagement(r["metrics"]) is not None
                  and (_age_h(r, now) or 0) <= 24 * 30]
        mature.sort(key=lambda r: r["published_at"], reverse=True)
        streak = 0
        for r in mature:
            if engagement(r["metrics"]) == 0:
                streak += 1
            else:
                break
        if streak >= 3:
            sig.append({"id": "zero_engagement_streak", "platform": p, "detail": f"the last {streak} settled posts got zero likes, comments, shares and saves"})
        followers = (data.get("accounts", {}).get(p) or {}).get("followers")
        reaches = [reach_of(r["metrics"]) for r in mature if reach_of(r["metrics"])]
        if len(reaches) >= 3 and followers and statistics.median(reaches) < 0.25 * followers:
            sig.append({"id": "low_reach", "platform": p, "detail": f"median reach {statistics.median(reaches):.0f} is under a quarter of {followers} followers: posts are barely shown"})
        d7 = _delta(data, p, 7, now)
        recent7 = [r for r in posts if r["platform"] == p and (_age_h(r, now) or 9e9) <= 24 * 7]
        if d7 is not None and d7 <= 0 and len(recent7) >= 3:
            sig.append({"id": "follower_stall", "platform": p, "detail": f"{len(recent7)} posts in 7 days and followers changed by {d7:+d}"})
        reels = [r["metrics"]["skip_rate"] for r in mature if r.get("format") == "reel" and r["metrics"].get("skip_rate") is not None]
        if reels and statistics.mean(reels) >= 60:
            sig.append({"id": "high_skip_rate", "platform": p, "detail": f"reels lose {statistics.mean(reels):.0f}% of viewers in the first 3 seconds across {len(reels)} reels: the hook is not stopping the scroll"})
        viewed = [r for r in mature if (reach_of(r["metrics"]) or 0) >= 100]
        if len(viewed) >= 3 and sum((r["metrics"].get("shares") or 0) + (r["metrics"].get("saves") or 0) for r in viewed) == 0:
            sig.append({"id": "viewed_not_shared", "platform": p, "detail": f"{len(viewed)} posts reached 100+ people but none was shared or saved: seen, not valued"})
        for dim in ("service", "hook_style", "format"):
            groups = {}
            for r in mature:
                reach, eng = reach_of(r["metrics"]), engagement(r["metrics"])
                key = r.get(dim) if dim == "format" else (r.get("matched") or {}).get(dim)
                if key and reach and eng is not None:
                    groups.setdefault(key, []).append(eng / reach)
            full = {k: statistics.mean(v) for k, v in groups.items() if len(v) >= 2}
            if len(full) >= 2:
                best, worst = max(full, key=full.get), min(full, key=full.get)
                if full[best] > 0 and full[worst] <= 0.5 * full[best]:
                    sig.append({"id": "weak_" + dim, "platform": p, "detail": f"by {dim.replace('_', ' ')}, '{worst}' earns {full[worst] / full[best]:.0%} of what '{best}' earns per person reached"})
    exp = _ts((data.get("ig_token") or {}).get("expires_at"))
    if exp and (exp - now).days <= 10:
        sig.append({"id": "token_expiring", "platform": "instagram", "detail": f"Instagram token expires in {max((exp - now).days, 0)} days"})
    return sig


def _label(r):
    m = r.get("matched") or {}
    return f'"{(m.get("topic") or r.get("text") or "")[:42]}"' + (f" ({m.get('service')}/{m.get('hook_style')})" if m.get("service") else "")


def digest(data, now=None):
    """(text for the strategist, list of weak signals). Empty text when there is no data at all."""
    now = now or utcnow()
    if not data or (not data.get("posts") and not data.get("accounts")):
        return "", []
    sig = weak_signals(data, now)
    upd = _ts(data.get("updated_at"))
    out = [f"Synced {upd.strftime('%Y-%m-%d %H:%M UTC') if upd else 'unknown'}" + (f" ({(now - upd).days} days ago: STALE)" if upd and (now - upd).days >= 2 else "")
           + f". Posts under {MIN_AGE_H}h old are excluded from judgement and Meta data can lag up to 48h. n/a = not reported, not zero."]
    settled = 0
    for p in data.get("coverage", {}):
        acct, cov = data.get("accounts", {}).get(p) or {}, data["coverage"][p]
        rows = [r for r in data.get("posts", []) if r["platform"] == p and (_age_h(r, now) or 9e9) <= 24 * 30]
        mature = [r for r in rows if (_age_h(r, now) or 0) >= MIN_AGE_H and engagement(r["metrics"]) is not None]
        settled += len(mature)
        fol = acct.get("followers")
        line = f"{p}: " + (f"{fol} followers" if fol is not None else "followers n/a")
        for days in (7, 30):
            d = _delta(data, p, days, now)
            if d is not None:
                line += f" ({d:+d} in {days}d)"
        line += f"; {len(rows)} posts in 30d"
        if not cov.get("ok"):
            out.append(line + f"; NO LIVE DATA ({cov.get('note')})")
            continue
        if mature:
            engs = [engagement(r["metrics"]) for r in mature]
            line += f"; median engagement {statistics.median(engs):.0f}"
            reaches = [reach_of(r["metrics"]) for r in mature if reach_of(r["metrics"])]
            if reaches:
                line += f", median reach {statistics.median(reaches):.0f}"
            best, worst = max(mature, key=lambda r: engagement(r["metrics"])), min(mature, key=lambda r: engagement(r["metrics"]))
            line += f"; best {_label(best)} eng {engagement(best['metrics'])}"
            if worst is not best:
                line += f"; worst {_label(worst)} eng {engagement(worst['metrics'])}"
        out.append(line)
    if settled < 10:
        out.append(f"Only {settled} settled posts in 30 days across all platforms: treat patterns as hints, not proof.")
    out.append("WEAK SIGNALS: " + ("none found" if not sig else ""))
    out += [f"- [{s['platform']}] {s['detail']}" for s in sig]
    return "\n".join(out)[:3200], sig


def load_digest(now=None):
    return digest(load(), now)
