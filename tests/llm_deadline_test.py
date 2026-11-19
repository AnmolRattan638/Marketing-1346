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
