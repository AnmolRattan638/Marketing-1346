import os, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import llm
REAL_ASK_JSON = llm.ask_json
os.environ.pop("RUN_DEADLINE_EPOCH", None)
assert not llm.out_of_time()
os.environ["RUN_DEADLINE_EPOCH"] = str(time.time() + 600)
assert not llm.out_of_time()
os.environ["RUN_DEADLINE_EPOCH"] = str(time.time() - 1)
assert llm.out_of_time()
called = []
llm.requests.post = lambda *a, **k: called.append(1)
try:
    llm._post("https://x.example/v1", {}, {})
    raise SystemExit("must stop")
except RuntimeError as e:
    assert "time budget" in str(e) and not called, "no network call is made after the deadline"
print("llm deadline test passed")

# a hard quota 429 must raise at once (no sleep/retry loop)
os.environ.pop("RUN_DEADLINE_EPOCH", None)
class R:
    status_code = 429; headers = {}
    text = '{"error":{"code":429,"message":"You exceeded your current quota, please check your plan"}}'
n = []
llm.requests.post = lambda *a, **k: (n.append(1), R())[1]
slept = []
llm.time.sleep = lambda s: slept.append(s)
try:
    llm._post("https://generativelanguage.googleapis.com/x", {}, {})
    raise SystemExit("must raise")
except llm.RateLimited:
    assert len(n) == 1 and not slept, (n, slept)
print("quota test passed")

# strict last-resort rewrite is requested in the prompt
from src.agents import scriptwriter as sw
seen = []
def fake(ask, prompt, sysm, **k):
    seen.append(prompt); return {"beats": [{"beat": "payoff", "line": "Fact bolta hai ki sub two second wali site Google ko achha signal deti hai"}]}
sw.llm.ask_json = fake
style = {"beats": ["pain", "payoff"]}
sc = {"beats": [{"beat": "pain", "line": "x"}, {"beat": "payoff", "line": "site upar rahega"}]}
out, ch = sw.repair_beats(sc, {"payoff": ["promises an outcome"]}, style, None, {"name": "Website"}, {"facts": [{"id": "f1"}], "keyword": "SITE"}, strict=True)
assert ch and "STRICT MODE" in seen[0] and out["beats"][1]["line"].startswith("Fact bolta")
print("strict repair test passed")
# Groq is the primary model; Gemini only if Groq fails
calls = []
llm.groq_keys = lambda: ["k"]
llm.groq = lambda p, s="", **k: (calls.append("groq"), "g")[1]
llm.gemini = lambda p, s="", **k: (calls.append("gemini"), "m")[1]
assert llm.primary("x") == "g" and calls == ["groq"]
def boom(p, s="", **k): raise RuntimeError("HTTP 429")
llm.groq = boom
assert llm.primary("x") == "m"
os.environ["LLM_PRIMARY"] = "gemini"; calls.clear(); llm.groq = lambda p, s="", **k: (calls.append("groq"), "g")[1]
assert llm.primary("x") == "m" and calls == ["gemini"]
os.environ.pop("LLM_PRIMARY")
print("primary model test passed")

# Groq returns no JSON twice -> Gemini answers
replies = iter(["", "no json here"])
llm.groq = lambda p, s="", **k: next(replies)
llm.gemini = lambda p, s="", **k: '{"ok": 1}'
llm.ask_json = REAL_ASK_JSON
assert llm.ask_json(llm.primary, "x") == {"ok": 1}
print("json fallback test passed")

# high reasoning effort on Groq; an empty answer is retried once at low effort
os.environ.pop("GROQ_REASONING_EFFORT", None)
sent = []
def fake_post(url, headers, body, tries=3, timeout=120):
    sent.append((body.get("reasoning_effort"), body.get("max_completion_tokens"), timeout))
    return {"choices": [{"message": {"content": "" if body.get("reasoning_effort") == "high" else "ok"}}]}
llm._post = fake_post
out = llm._chat("https://api.groq.com/openai/v1/chat/completions", "k", "p", "", "openai/gpt-oss-120b", 0.5)
assert out == "ok" and sent[0] == ("high", 16000, 240) and sent[1][0] == "low", sent
sent.clear()
llm._chat("https://api.groq.com/openai/v1/chat/completions", "k", "p", "", "llama-3.3-70b", 0.5)
assert sent[0][0] is None                                   # only the gpt-oss reasoning model gets the setting
print("groq high effort test passed")

# Groq 413 (request over the per-minute token limit): the call retries with a smaller output allowance instead of failing
sizes = []
def fake_post(url, headers, body, tries=3, timeout=120):
    sizes.append(body["max_completion_tokens"])
    if body["max_completion_tokens"] > 4000:
        raise RuntimeError("HTTP 413 from api.groq.com: Request too large")
    return {"choices": [{"message": {"content": "ok"}}]}
llm._post = fake_post
assert llm._chat("https://api.groq.com/openai/v1/chat/completions", "k", "hi", "", "openai/gpt-oss-120b", 0.5) == "ok"
assert sizes == [16000, 8000, 4000], sizes
print("groq 413 shrink test passed")
