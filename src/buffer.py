"""Buffer GraphQL API (https://developers.buffer.com): publish approved posts to the queue."""
import json, os
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


def create_post(channel_id, text, image_url=None):
    assets = f", assets: [{{ image: {{ url: {_s(image_url)} }} }}]" if image_url else ""
    q = (f"mutation {{ createPost(input: {{ text: {_s(text)}, channelId: {_s(channel_id)}, "
         f"schedulingType: automatic, mode: addToQueue{assets} }}) {{ "
         f"... on PostActionSuccess {{ post {{ id dueAt }} }} ... on MutationError {{ message }} }} }}")
    res = _gql(q)["createPost"]
    if res.get("post"):
        return res["post"]
    raise RuntimeError(res.get("message", "unknown Buffer error"))
