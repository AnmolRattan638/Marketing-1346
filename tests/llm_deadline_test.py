import os, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import llm
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
