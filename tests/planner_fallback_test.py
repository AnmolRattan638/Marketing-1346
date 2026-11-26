"""A spent Groq quota must not kill the reel: the planner and the shared model chain fall back to the other vendors."""
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "video-agent")]
from agent import plan as planmod
from src import llm

# 1) planner: Groq answers 429 (also on the low-effort re-ask) -> Gemini answers
def boom(messages, cfg):
    raise RuntimeError("Groq rate limit hit (429)")
planmod._call_groq = boom
os.environ["GEMINI_API_KEY"] = "g"; os.environ.pop("NVIDIA_API_KEY", None); os.environ.pop("OPENROUTER_API_KEY", None)
llm._gemini = lambda prompt, system="", **kw: 'noise {"scenes": []} noise'
out = planmod._call_planner([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], {})
assert json.loads(out) == {"scenes": []}

# 2) a raw HTTPError from the re-ask path is also caught
import requests
def boom2(messages, cfg):
    raise requests.exceptions.HTTPError("429 Client Error")
planmod._call_groq = boom2
assert json.loads(planmod._call_planner([{"role": "user", "content": "u"}], {})) == {"scenes": []}

# 3) nobody left -> a plain error that names every failure
llm._gemini = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("HTTP 429 gemini"))
try:
    planmod._call_planner([{"role": "user", "content": "u"}], {}); assert False
except RuntimeError as e:
    assert "no model could write the plan" in str(e) and "gemini" in str(e)

# 4) shared chain: Groq down -> Gemini then NVIDIA are tried
calls = []
def g_fail(prompt, system="", **kw): calls.append("gemini"); raise RuntimeError("HTTP 429")
def n_ok(prompt, system="", **kw): calls.append("nvidia"); return "ok"
llm._gemini, llm._nvidia = g_fail, n_ok
os.environ["NVIDIA_API_KEY"] = "n"; os.environ.pop("OPENROUTER_API_KEY", None); os.environ.pop("GROQ_API_KEY", None)
def fake_groq(prompt, system="", **kw): raise RuntimeError("HTTP 429 groq")
fake_groq.__name__ = "_groq"
assert llm._with_fallback(fake_groq)("p") == "ok" and calls == ["gemini", "nvidia"], calls
print("planner fallback ok")
