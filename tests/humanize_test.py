"""Offline test: open-humanizer (vendored, unmodified) is wrapped in guards. A rewrite is used only if every check passes; any failure keeps the original post."""
import hashlib, json, os, pathlib, sys, time
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
for k in ("HUMANIZE", "HUMANIZE_API_KEY", "HUMANIZE_MODEL", "HUMANIZE_BASE_URL", "HUMANIZE_TARGET", "HUMANIZE_BUDGET", "GROQ_API_KEY", "GROQ_API_KEYS", "RUN_DEADLINE_EPOCH") + tuple(f"GROQ_API_KEY_{i}" for i in range(2, 10)):
    os.environ.pop(k, None)
from src import humanize as h
REAL_ENGINE = h._engine

focus = next(s for s in json.load(open(REPO / "config/services.json"))["services"] if s["id"] == "chatbot")
HOOK = "Most customers message at night and nobody answers."
P1 = "A shop owner in Pune told me she loses a few chats every evening because she is busy with real customers. By the time she checks WhatsApp the person has already messaged someone else."
P2 = "A simple chatbot answers the first question, collects the name and asks when to call back, so the conversation does not go cold while she is at the counter."
CTA = "Comment BOT and I will send you the setup steps."
TAGS = "#chatbot #smallbusiness"
ORIG = "\n\n".join([HOOK, P1, P2, CTA, TAGS])
GOOD = ("She loses chats every evening. Real customers keep her busy, and when she finally opens WhatsApp in Pune the other person has long since messaged someone else.\n\n"
        "A chatbot can take the first question, note the name and ask when to call back. The chat stays warm while she's at the counter.")
VENDOR_SHA = hashlib.sha256((REPO / "third_party/open-humanizer/open_humanizer/pipeline.py").read_bytes()).hexdigest()

# 0. the vendored package is untouched and loads
src = REPO / "third_party/open-humanizer"
assert len([p for p in src.rglob("*") if p.is_file() and "__pycache__" not in p.parts]) == 24 and (src / "LICENSE").exists() and (src / "tests/test_pipeline.py").exists(), "nothing was removed from the upstream repo"
pipeline_cls, pm = h._load()
orig_sys = pm.get_humanizer_system_prompt()

# 1. guards (problems): the safe rewrite passes, each kind of damage is caught
sep = "\n\n"
full = lambda body: sep.join([HOOK, body, CTA, TAGS])
old_body = P1 + sep + P2
assert h.problems(ORIG, full(GOOD), "instagram", focus, sep) == [], h.problems(ORIG, full(GOOD), "instagram", focus, sep)
bad = {
    "numbers": GOOD.replace("every evening", "5 times every evening"),
    "lost name": GOOD.replace("WhatsApp", "the app"),
    "lost city": GOOD.replace("Pune", "town"),
    "dash": GOOD.replace("evening.", "evening \u2014 it hurts."),
    "markdown": GOOD.replace("A chatbot", "**A chatbot**"),
    "bullets": GOOD + "\n\n- first\n- second",
    "one block": GOOD.replace("\n\n", " "),
    "too long": GOOD + " " + "Extra filler sentence that keeps going on and on. " * 6,
    "too short": "She loses chats. A chatbot helps.",
    "preamble": "Here is the rewrite: " + GOOD,
    "script switch": GOOD + " \u0928\u092e\u0938\u094d\u0924\u0947",
    "rule break": GOOD.replace("A chatbot can", "It's not a chat problem, it's a speed problem. A chatbot can"),
}
for name, body in bad.items():
    why = h.problems(ORIG, full(body) if name not in ("one block",) else full(body), "instagram", focus, sep)
    assert why, f"'{name}' must be rejected"
assert not h.problems(ORIG, ORIG, "instagram", focus, sep), "an unchanged post is fine"
li_ok = "\n\n".join([HOOK] + ["This is a plain sentence about how small shops answer their chats during the day. " * 3] * 6 + [CTA])
assert h.problems(li_ok, li_ok.replace("plain sentence", "simple sentence"), "linkedin", focus, sep) == [], "a 300+ word LinkedIn post stays in its window"
assert any("window" in w or "length" in w for w in h.problems(li_ok, HOOK + sep + "short body " * 10 + sep + CTA, "linkedin", focus, sep))

# 2. what is sent: only the body; hook, CTA (keyword), hashtags stay verbatim and never leave
blocks = ORIG.split(sep)
a, b = h._run(blocks, focus["dm_keyword"])
assert (a, b) == (1, 3) and sep.join(blocks[a:b]) == P1 + sep + P2

# 3. fake engine: accepted rewrite is reassembled around the untouched hook, CTA and hashtags
sent, os.environ["GROQ_API_KEY"] = [], "k1"
class Fake:
    def __init__(self, result): self.result = result
    def humanize(self, body, max_retries, target_score):
        sent.append((body, max_retries, target_score, pm.get_humanizer_system_prompt()))
        return self.result(body) if callable(self.result) else self.result
ok = {"status": "success", "final_score": 12.0, "text": GOOD, "metrics_history": [{"ai_percentage": 80.0}, {"ai_percentage": 12.0}]}
h._engine = lambda key: Fake(ok)
new, rep = h.humanize_text(ORIG, "instagram", focus, time.time() + 60)
assert rep["status"] == "humanized" and (rep["ai_before"], rep["ai_after"]) == (80.0, 12.0)
assert new == sep.join([HOOK, GOOD, CTA, TAGS]) and new.startswith(HOOK) and CTA in new and new.endswith(TAGS)
body, retries, target, system = sent[0]
assert body == P1 + sep + P2 and HOOK not in body and "BOT" not in body and "#chatbot" not in body, "the hook, the CTA and the hashtags were not sent"
assert retries == 1 and target == 15.0 and "HOUSE RULES" in system and orig_sys in system, "the package's own rules plus ours"
assert pm.get_humanizer_system_prompt() == orig_sys, "the package is restored exactly after the call"

# 4. every way to keep the original
def kept(result, why):
    h._engine = lambda key: Fake(result)
    t, r = h.humanize_text(ORIG, "instagram", focus, time.time() + 60)
    assert t == ORIG and r["status"] in ("kept", "error"), (why, r)
    return r
kept({**ok, "text": bad["numbers"]}, "numbers")
kept({**ok, "text": GOOD, "final_score": 90.0, "metrics_history": [{"ai_percentage": 80.0}]}, "critic says worse")
assert "already reads human" in kept({"status": "success", "final_score": 4.0, "text": P1 + sep + P2, "metrics_history": [{"ai_percentage": 4.0}]}, "already human")["reason"]
short = ORIG.replace(P1, "Short.").replace(P2, "Also short.")
h._engine = lambda key: (_ for _ in ()).throw(AssertionError("must not be called for a short post"))
t, r = h.humanize_text(short, "instagram", focus, time.time() + 60)
assert t == short and r["status"] == "skipped"

# 5. keys: a rate-limited key moves on to the next, all failing keeps the original, other errors stop at once
class Limited(Exception):
    status_code = 429
tried = []
def engine_for(key):
    tried.append(key)
    return Fake(ok) if key == "k2" else Fake(lambda body: (_ for _ in ()).throw(Limited("rate limit reached")))
h._engine, h.llm.groq_keys = engine_for, lambda: ["k1", "k2", "k3", "k4"]
t, r = h.humanize_text(ORIG, "instagram", focus, time.time() + 60)
assert r["status"] == "humanized" and tried == ["k1", "k2"]
tried.clear(); h._engine = lambda key: (tried.append(key), Fake(lambda body: (_ for _ in ()).throw(Limited("429"))))[1]
t, r = h.humanize_text(ORIG, "instagram", focus, time.time() + 60)
assert t == ORIG and r["status"] == "error" and len(tried) == h.MAX_KEYS and "Limited" in r["reason"]
tried.clear(); h._engine = lambda key: (tried.append(key), Fake(lambda body: (_ for _ in ()).throw(ValueError("bad model"))))[1]
t, r = h.humanize_text(ORIG, "instagram", focus, time.time() + 60)
assert t == ORIG and r["status"] == "error" and len(tried) == 1, "a non-limit error does not burn the other keys"
t, r = h.humanize_text(ORIG, "instagram", focus, time.time() - 1)
assert t == ORIG and r["reason"] == "out of time"

# 6. humanize_posts: never raises, replies and untouched platforms come back as they were, switches work
h._engine = lambda key: Fake(ok)
posts = {"instagram": ORIG, "linkedin": ORIG, "bluesky": "Short post.", "replies": ["x", "y"]}
out, report = h.humanize_posts(posts, focus)
assert out["replies"] == ["x", "y"] and out["bluesky"] == "Short post." and report["platforms"]["instagram"]["status"] == "humanized" and report["platforms"]["bluesky"]["status"] == "skipped"
assert "linkedin" not in report["platforms"] and out["linkedin"] == ORIG, "LinkedIn is skipped by default: the text that passed its own gate is what gets posted"
assert "instagram humanized (Critic AI 80.0% -> 12.0%)" in h.summary_line(report) and "bluesky skipped" in h.summary_line(report)
h._engine = lambda key: (_ for _ in ()).throw(RuntimeError("boom"))
out, report = h.humanize_posts(posts, focus, skip=())
assert out == posts and report["platforms"]["linkedin"]["status"] == "error", "an engine bug leaves every post as it was"
os.environ["HUMANIZE"] = "0"
assert h.humanize_posts(posts, focus) == (posts, {}) and not h.enabled()
os.environ.pop("HUMANIZE"); os.environ.pop("GROQ_API_KEY"); h.llm.groq_keys = lambda: []
assert not h.enabled() and h.humanize_posts(posts, focus) == (posts, {}), "no key, no call"
os.environ["HUMANIZE_API_KEY"] = "own"; assert h.enabled(); os.environ.pop("HUMANIZE_API_KEY")
real_load = h._load
os.environ["GROQ_API_KEY"] = "k1"; h.llm.groq_keys = lambda: ["k1"]
h._load = lambda: (_ for _ in ()).throw(ImportError("No module named 'openai'"))
out, report = h.humanize_posts(posts, focus)
assert out == posts and "not available" in report["error"] and "not available" in h.summary_line(report)
h._load = real_load

# 7. the REAL vendored pipeline and the real OpenAI SDK over a fake Groq endpoint (no network): critic, writer, the endpoint, key and model
import openai
try:
    import httpx2 as httpx             # openai 3.x brings its own copy of httpx under this name
except ImportError:
    import httpx
seen = []
def groq(request):
    body = json.loads(request.content)
    msgs = body["messages"]
    system, user = msgs[0]["content"], msgs[-1]["content"]            # the Critic sends one message, the Writer a system prompt and a user prompt
    seen.append((str(request.url), request.headers["authorization"], body["model"], system, user))
    if request.headers["authorization"] == "Bearer limited":
        return httpx.Response(429, json={"error": {"message": "Rate limit reached", "type": "tokens", "code": "rate_limit_exceeded"}})
    if "AI Detector" in system:                                        # the Critic: the original reads 80% AI, the rewrite 12%
        score = 12.0 if "chats every evening" in user and "A shop owner" not in user else 80.0
        content = json.dumps({"overall_ai_percentage": score, "flagged_sentences": [], "is_undetectable": score < 10})
    else:                                                              # the Writer
        content = GOOD
    return httpx.Response(200, json={"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                                     "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                                     "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
real_openai = openai.OpenAI
openai.OpenAI = lambda **kw: real_openai(**kw, http_client=httpx.Client(transport=httpx.MockTransport(groq)))
h._engine = REAL_ENGINE
h.llm.groq_keys = lambda: ["limited", "good"]
t, r = h.humanize_text(ORIG, "instagram", focus, time.time() + 60)
openai.OpenAI = real_openai
assert r["status"] == "humanized", r
assert t == sep.join([HOOK, GOOD, CTA, TAGS]) and (r["ai_before"], r["ai_after"]) == (80.0, 12.0), (t, r)
url, auth, model, system, user = seen[-1]
assert seen[0][1] == "Bearer limited" and any(s[1] == "Bearer good" for s in seen), "429 on the first key, the second key did the work"
assert all(s[0] == "https://api.groq.com/openai/v1/chat/completions" and s[2] == h.DEFAULT_MODEL for s in seen)
writer = next(s for s in seen if "investigative journalist" in s[3])
assert "HOUSE RULES" in writer[3] and "HUMAN STYLOMETRIC FLOW" in writer[3], "the real Writer prompt = the package's own rules + ours"
assert "A shop owner in Pune" in writer[4] and "BOT" not in writer[4] and HOOK not in writer[4] and "#chatbot" not in writer[4], "and only the body was sent"
assert pm.get_humanizer_system_prompt() == orig_sys and hashlib.sha256((REPO / "third_party/open-humanizer/open_humanizer/pipeline.py").read_bytes()).hexdigest() == VENDOR_SHA
print("humanize test passed: vendored repo intact, body-only, 12 kinds of damage rejected, key rotation, fail-open everywhere, real pipeline + SDK over a fake Groq endpoint")
