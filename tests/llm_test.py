"""Offline tests for LLM resilience: a Google 500/503 must switch model instead of sleeping, a bad key must NOT switch,
a failed model is benched, every provider can fail and the request still gets an answer, and the Telegram wait loop survives
network errors. No network, no keys."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import requests
from src import config, llm, tg, process_approvals as pa

os.environ.update(GEMINI_API_KEY="gk-test-123456", TELEGRAM_BOT_TOKEN="123456:TELEGRAMSECRET", TELEGRAM_CHAT_ID="1")
sleeps = []
llm.time.sleep = lambda s: sleeps.append(s)
pa.time.sleep = lambda s: sleeps.append(s)


class Resp:
    def __init__(self, status=200, j=None, text=None, headers=None):
        self.status_code, self._j, self.headers = status, j, headers or {}
        self.text = text if text is not None else json.dumps(j)

    def json(self):
        if self._j is None:
            raise ValueError("not json")
        return self._j


def reset():
    llm._DOWN.clear(); llm.LOG.clear(); llm.FAILURES.clear(); llm._ALIAS.clear(); sleeps.clear()


def ok(text="hello"):
    return Resp(200, {"candidates": [{"content": {"parts": [{"text": text}]}}], "choices": [{"message": {"content": text}}]})


def install(behaviour, calls):
    """behaviour: model -> list of responses/exceptions, used in order (the last one repeats)."""
    def post(url, headers=None, json=None, timeout=None):
        model = (json or {}).get("model") or url.split("/models/")[-1].split(":")[0]
        calls.append((model, json))
        seq = behaviour.get(model, [ok()])
        item = seq[min(sum(1 for m, _ in calls if m == model) - 1, len(seq) - 1)]
        if isinstance(item, Exception):
            raise item
        return item
    llm.requests.post = post


# ------------------------------------------------------------------ _post
reset(); calls = []
install({"m": [Resp(503, text='{"error":{"code":503,"message":"The model is overloaded."}}')]}, calls)
try:
    llm._post("https://x.test/v1/chat", {}, {"model": "m"})
    raise SystemExit("503 must raise")
except llm.ProviderDown as e:
    assert "HTTP 503" in str(e) and "overloaded" in str(e)
assert len(calls) == 2 and len(sleeps) == 1 and sleeps[0] <= 6, ("5xx: one quick retry, then stop", len(calls), sleeps)

reset(); calls = []
install({"m": [Resp(500, text="boom"), ok("recovered")]}, calls)
assert llm._post("https://x.test/v1/chat", {}, {"model": "m"})["choices"][0]["message"]["content"] == "recovered"

reset(); calls = []
install({"m": [Resp(429, text='{"error":{"details":[{"retryDelay":"13s"}]}}'), ok("after wait")]}, calls)
assert llm._post("https://x.test/v1/chat", {}, {"model": "m"})["choices"][0]["message"]["content"] == "after wait" and sleeps == [13.0], sleeps

for status in (400, 401, 403):
    reset(); calls = []
    install({"m": [Resp(status, text='{"error":{"message":"API key not valid gk-test-123456"}}')]}, calls)
    try:
        llm._post("https://x.test/v1/chat", {}, {"model": "m"})
        raise SystemExit("4xx must raise")
    except RuntimeError as e:
        assert not isinstance(e, llm.ProviderDown) and f"HTTP {status}" in str(e) and "gk-test-123456" not in str(e), e
    assert len(calls) == 1 and not sleeps, "a 4xx cannot be fixed by retrying"

reset(); calls = []
install({"m": [requests.ConnectionError("dns"), requests.ConnectionError("dns")]}, calls)
try:
    llm._post("https://x.test/v1/chat", {}, {"model": "m"})
    raise SystemExit("unreachable must raise")
except llm.ProviderDown as e:
    assert "unreachable" in str(e)
reset(); calls = []
install({"m": [Resp(200, j=None, text="<html>")]}, calls)
try:
    llm._post("https://x.test/v1/chat", {}, {"model": "m"})
    raise SystemExit("non-JSON must raise")
except llm.ProviderDown:
    pass

# ------------------------------------------------------------------ Google: switch model on 5xx (Google's own advice)
llm._GMODELS = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-3.8-flash-lite", "gemma-4-31b-it", "gemma-3-27b-it"]
config.GEMINI_MODEL, config.GEMMA_MODEL = "gemini-3.5-flash", "gemma-4-31b-it"
reset(); calls = []
install({"gemini-3.5-flash": [Resp(503, text='{"error":{"code":503,"message":"overloaded"}}')], "gemini-3.8-flash": [ok("from 3.8")]}, calls)
assert llm._gemini("p", "sys") == "from 3.8"
assert [m for m, _ in calls] == ["gemini-3.5-flash", "gemini-3.5-flash", "gemini-3.8-flash"], calls
assert "FAILED google:gemini-3.5-flash (HTTP 503)" in llm.LOG and "google:gemini-3.8-flash" in llm.LOG, llm.LOG
f = llm.FAILURES[0]
assert f["status"] == "503" and "overloaded" in f["error"] and f["model"] == "google:gemini-3.5-flash", f
assert not llm._ALIAS, "a transient 503 must not rename the model for good"
assert sum(sleeps) <= 6, "only one short pause, not 60 seconds"
calls.clear(); sleeps.clear()
assert llm._gemini("p2", "sys") == "from 3.8"
assert [m for m, _ in calls] == ["gemini-3.8-flash"] and not sleeps, ("the benched model must be skipped", calls)
assert "systemInstruction" in calls[0][1], "Gemini keeps the system instruction"

# a retired model (404) is replaced for good
reset(); calls = []
install({"gemini-3.5-flash": [Resp(404, text='{"error":{"message":"models/gemini-3.5-flash is not found"}}')], "gemini-3.8-flash": [ok("new")]}, calls)
assert llm._gemini("p") == "new" and llm._ALIAS == {"gemini-3.5-flash": "gemini-3.8-flash"}

# a bad key must NOT hop between models: it would fail identically everywhere
reset(); calls = []
install({"gemini-3.5-flash": [Resp(403, text='{"error":{"message":"API key not valid"}}')]}, calls)
try:
    llm._gemini("p")
    raise SystemExit("403 must raise")
except RuntimeError as e:
    assert "HTTP 403" in str(e) and not isinstance(e, llm.ProviderDown)
assert [m for m, _ in calls] == ["gemini-3.5-flash"], calls

# Gemma failing (the 500 from today's draft): next Gemma, then a Gemini Flash; Gemma gets the system prompt inside the user message
reset(); calls = []
install({"gemma-4-31b-it": [Resp(500, text='{"error":{"code":500,"status":"INTERNAL"}}')], "gemma-3-27b-it": [Resp(500, text="x")], "gemini-3.8-flash": [ok("flash saved it")]}, calls)
assert llm._gemini("question", "be brief", model="gemma-4-31b-it", _kind="gemma") == "flash saved it"
gemma_body = [b for m, b in calls if m.startswith("gemma")][0]
assert "systemInstruction" not in gemma_body and "be brief" in gemma_body["contents"][0]["parts"][0]["text"]
assert "FAILED google:gemma-4-31b-it (HTTP 500)" in llm.LOG and "google:gemini-3.8-flash" in llm.LOG, llm.LOG

# every Google model down: the wrapper still answers through OpenRouter, then Groq
reset(); calls = []
install({m: [Resp(503, text="down")] for m in llm._GMODELS}, calls)
os.environ.update(OPENROUTER_API_KEY="or-test-123456", GROQ_API_KEY="gq-test-123456")
llm.openrouter = lambda prompt, system="", model=None, temperature=0.7: (_ for _ in ()).throw(RuntimeError("openrouter also down"))
llm._groq = lambda prompt, system="", model=None, temperature=0.6: "from groq"
assert llm.gemini("p", "s") == "from groq" and any(l.startswith("FAILED gemini") for l in llm.LOG), llm.LOG
llm.openrouter = lambda prompt, system="", model=None, temperature=0.7: "from openrouter"
reset(); assert llm.gemini("p", "s") == "from openrouter"

# ------------------------------------------------------------------ OpenRouter: free models are swapped on 5xx, an explicit model is not
import importlib
importlib.reload(llm)
llm.time.sleep = lambda s: sleeps.append(s)
os.environ["OPENROUTER_API_KEY"] = "or-test-123456"
llm._openrouter_free_models = lambda: ["a:free", "b:free"]
config.OPENROUTER_MODEL = ""
reset(); calls = []
install({"a:free": [Resp(503, text="down")], "b:free": [ok("b answered")]}, calls)
assert llm.openrouter("p") == "b answered" and "FAILED openrouter.ai:a:free (HTTP 503)" in llm.LOG
reset(); calls = []
install({"x:free": [Resp(503, text="down")]}, calls)
try:
    llm.openrouter("p", model="x:free")
    raise SystemExit("explicit model must not be swapped")
except llm.ProviderDown:
    pass
n = len(calls)
try:
    llm.openrouter("p", model="x:free")
except llm.ProviderDown as e:
    assert "skipped" in str(e) and len(calls) == n, "a benched explicit model fails instantly without a request"

# ------------------------------------------------------------------ Telegram client: errors become RuntimeError, token never leaks
def boom(*a, **k):
    raise requests.ConnectionError("HTTPSConnectionPool: https://api.telegram.org/bot123456:TELEGRAMSECRET/getUpdates")
tg.requests.post = boom
try:
    tg.get_updates(0, 25)
    raise SystemExit("must raise")
except RuntimeError as e:
    assert "TELEGRAMSECRET" not in str(e) and "network error" in str(e), e
tg.requests.post = lambda *a, **k: Resp(502, j=None, text="<html>Bad gateway</html>")
try:
    tg.get_updates(0, 25)
    raise SystemExit("must raise")
except RuntimeError as e:
    assert "non-JSON" in str(e) and "502" in str(e)

# ------------------------------------------------------------------ wait(): the crash that failed today's run
tmp = pathlib.Path(__import__("tempfile").mkdtemp())
config.DATA = tmp
msgs, state = [], {"pending": True, "calls": 0}
tg.send = lambda text, buttons=None: msgs.append(text)
pa.pending_recent = lambda hours=23.5: state["pending"]

def flaky_poll(st, timeout):                        # three network blips, then the owner taps Approve
    state["calls"] += 1
    if state["calls"] <= 3:
        raise requests.ConnectionError("blip")
    state["pending"] = False
pa.poll = flaky_poll
sleeps.clear(); pa.wait(3600)
assert state["calls"] == 4 and sleeps == [15, 30, 45] and not msgs, (state, sleeps, msgs)

state.update(pending=True, calls=0)                 # a raw non-RuntimeError, as in the real crash: must also be survived
def weird_poll(st, timeout):
    state["calls"] += 1
    raise ValueError("Expecting value: line 1 column 1")
pa.poll = weird_poll
sleeps.clear(); msgs.clear(); pa.wait(3600)         # gives up after 20 errors WITHOUT raising: the safety-net workflow takes over
assert state["calls"] == 20 and any("kept failing" in m for m in msgs), (state, msgs)
assert max(sleeps) == 120, "pauses grow but are capped"

def send_fails(text, buttons=None):
    raise RuntimeError("telegram down")
tg.send = send_fails
state.update(pending=True, calls=0); pa.wait(3600)  # even the notification failing must not crash the run
assert state["calls"] == 20

def webhook_poll(st, timeout):
    raise RuntimeError("Telegram getUpdates failed: Conflict: can't use getUpdates method while webhook is active")
pa.poll = webhook_poll
state.update(pending=True)
try:
    pa.wait(3600)
    raise SystemExit("an active webhook is a real configuration error and must still stop the run")
except SystemExit as e:
    assert "webhook" in str(e).lower()
print("llm test passed: 5xx failover, bad key not switched, circuit breaker, provider chain, OpenRouter swap, Telegram errors, wait() survives")
