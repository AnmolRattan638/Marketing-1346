"""Offline test: LinkedIn is pinned to one publisher (Buffer first); Instagram and Bluesky keep the general order."""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import publish

calls = []
def make(name, fail_linkedin=False):
    class P:
        secrets, platforms = [], ("instagram", "linkedin", "bluesky")
        def post(self, platform, text, image_url, image_path):
            calls.append((platform, name))
            if fail_linkedin and platform == "linkedin":
                raise RuntimeError("down")
            return "ok"
    P.name = name
    return P

def run(classes, general, env=None):
    calls.clear()
    for k in ("PUBLISHER_ORDER", "LINKEDIN_PUBLISHER_ORDER"):
        os.environ.pop(k, None)
    os.environ.update(env or {})
    publish.PROVIDERS = classes
    publish.choose_order = lambda provs, today=None: sorted(provs, key=lambda p: general.index(p.name))
    draft = {"posts": {"instagram": "i", "linkedin": "l", "bluesky": "b"}, "image": {"path": "x.jpg"}, "hooks": [{"text": "h"}]}
    res = publish.publish_draft(draft)
    return dict(calls), res

general = ["zernio", "socialapi", "buffer"]          # today's (rotated) general order: Buffer would be LAST
# 1. default: LinkedIn -> Buffer, Instagram/Bluesky -> the general first choice
c, res = run([make("buffer"), make("zernio"), make("socialapi")], general)
assert c == {"linkedin": "buffer", "instagram": "zernio", "bluesky": "zernio"}, c
# 2. Buffer fails: other tools are only a fallback for LinkedIn
calls.clear()
c, res = run([make("buffer", fail_linkedin=True), make("zernio"), make("socialapi")], general)
assert res["linkedin"]["ok"] and res["linkedin"]["detail"].startswith("zernio"), res
# 3. strict pin: only the named tool(s); failure is reported, no fallback
c, res = run([make("buffer", fail_linkedin=True), make("zernio")], general, {"LINKEDIN_PUBLISHER_ORDER": "buffer"})
assert not res["linkedin"]["ok"] and "buffer: down" in res["linkedin"]["detail"] and res["instagram"]["ok"], res
c, res = run([make("buffer"), make("zernio")], general, {"LINKEDIN_PUBLISHER_ORDER": "zernio"})
assert c["linkedin"] == "zernio", c
# 4. an explicit global PUBLISHER_ORDER is respected for LinkedIn unless LINKEDIN_PUBLISHER_ORDER is set
c, res = run([make("buffer"), make("zernio")], ["zernio", "buffer"], {"PUBLISHER_ORDER": "zernio,buffer"})
assert c["linkedin"] == "zernio", c
# 5. no Buffer secrets/tool configured: nothing changes
c, res = run([make("zernio"), make("socialapi")], general)
assert c["linkedin"] == "zernio" and c["instagram"] == "zernio", c
print("linkedin publisher test passed: LinkedIn pinned to Buffer first, fallback only on failure, Instagram/Bluesky order unchanged")
