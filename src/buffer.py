"""Buffer GraphQL API (https://developers.buffer.com): publish approved posts to the queue."""
import datetime as dt, json, os
import requests

URL = "https://api.buffer.com"


def _gql(query):
    r = requests.post(URL, timeout=60, json={"query": query},
                      headers={"Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}"})
    r.raise_for_status()
    d = r.json()
    if d.get("errors"):
        raise RuntimeError(str(d["errors"])[:400])
    return d["data"]


def _s(v):
    return json.dumps(v, ensure_ascii=False)


def channel_map():
    orgs = _gql("query { account { organizations { id name } } }")["account"]["organizations"]
    out = {}
    for o in orgs:
        chans = _gql(f"query {{ channels(input: {{ organizationId: {_s(o['id'])} }}) {{ id name service }} }}")["channels"]
        for c in chans:
            out.setdefault(c["service"].lower(), c["id"])
    return out


def _due_soon(minutes=2):
    t = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=minutes)
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def create_post(channel_id, text, image_url=None):
    """Publish NOW, not "add to queue": addToQueue waits for the next slot in the channel's Buffer posting
    schedule, and if that channel has no schedule slots the post sits there for ever (it was reported as
    "queued" and never appeared on LinkedIn). Try shareNow first; if the API rejects it, schedule 2 minutes ahead."""
    urls = list(image_url) if isinstance(image_url, (list, tuple)) else ([image_url] if image_url else [])      # several images = a carousel, in this order
    assets = ", assets: [" + ", ".join(f"{{ image: {{ url: {_s(u)} }} }}" for u in urls) + "]" if urls else ""
    modes = ["mode: shareNow", f"mode: customScheduled, dueAt: {_s(_due_soon())}"]
    last = None
    for m in modes:
        q = (f"mutation {{ createPost(input: {{ text: {_s(text)}, channelId: {_s(channel_id)}, "
             f"schedulingType: automatic, {m}{assets} }}) {{ "
             f"... on PostActionSuccess {{ post {{ id dueAt }} }} ... on MutationError {{ message }} }} }}")
        try:
            res = _gql(q)["createPost"]
        except RuntimeError as e:        # e.g. the API does not know this mode
            last = e
            continue
        if res.get("post"):
            return res["post"]
        last = RuntimeError(res.get("message", "unknown Buffer error"))
    raise last
