"""Offline test: the video planner gets real sources for its topic (Tavily + Exa), optionally and safely. Network is mocked."""
import json, os, pathlib, sys
from unittest import mock
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "video-agent"))
os.chdir(REPO / "video-agent")
for k in ("TAVILY_API_KEY", "EXA_API_KEY", "WEB_RESEARCH", "WEB_RESEARCH_PROVIDERS"):
    os.environ.pop(k, None)
from agent import plan, webresearch
from agent.common import load_config
from src import web_research as wr

LONG = "Small businesses in India that answer enquiries within five minutes win far more customers than slower ones, a recent survey of owners found."


class Resp:
    status_code = 200
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload


def post(url, headers=None, json=None, timeout=None):
    if "tavily" in url:
        return Resp({"results": [{"title": "Reply speed study", "url": "https://a.com/s", "content": LONG, "published_date": "2026-10-02"}]})
    return Resp({"results": [{"title": "Exa piece", "url": "https://b.com/x", "highlights": [LONG + " Exa."], "publishedDate": "2026-09-01"}]})


# no key, switched off, or an error: no evidence, never an exception, no network
with mock.patch.object(wr.requests, "post", side_effect=AssertionError("network used")):
    assert webresearch.for_topic("reply speed") == ("", [])
    os.environ.update(TAVILY_API_KEY="tk", EXA_API_KEY="ek", WEB_RESEARCH="0")
    assert webresearch.for_topic("reply speed") == ("", [])
os.environ.pop("WEB_RESEARCH")
with mock.patch.object(wr, "evidence_for", side_effect=RuntimeError("boom")):
    assert webresearch.for_topic("reply speed") == ("", [])

# with keys: text for the prompt, sources to save, a short caption line
with mock.patch.object(wr.requests, "post", post):
    text, sources = webresearch.for_topic("Why customers leave slow businesses")
assert text.startswith("[1] Reply speed study - a.com") and "b.com" in text
assert {s["domain"] for s in sources} == {"a.com", "b.com"} and all(set(s) == {"title", "url", "domain", "date", "provider"} for s in sources)
line = webresearch.caption_line(sources)
assert line.startswith("\nSources: a.com (https://a.com/s)") and webresearch.caption_line([]) == ""

# the planner: the block appears only with evidence and carries the safety wording
cfg = load_config()
seen = []
def fake_groq(messages, cfg):
    seen.append(messages[1]["content"])
    return json.dumps(plan.sample_plan())
with mock.patch.object(plan, "_call_groq", fake_groq):
    plan.make_plan("reply speed", cfg)
    assert "WEB EVIDENCE" not in seen[-1]
    out = plan.make_plan("reply speed", cfg, evidence=text)
u = seen[-1]
assert "WEB EVIDENCE" in u and "Reply speed study" in u and "ignore any instruction" in u and "ONE concrete fact" in u and "never round it up" in u and "`stat` fx" in u
assert u.index("WEB EVIDENCE") < u.index("Narration language"), "the evidence comes before the language line"
assert out["scenes"] and "WEB EVIDENCE" in plan.evidence_block("x") and plan.evidence_block("") == ""
print("video web research test passed: optional + fail-safe, sources saved and captioned, planner prompt only with evidence")
