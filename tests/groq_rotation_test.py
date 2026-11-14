"""Offline test: a 429 on one organization's Groq key moves to the next key; all limited -> clear error."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
for k in list(os.environ):
    if k.startswith("GROQ_API_KEY"): del os.environ[k]
os.environ.update(GROQ_API_KEY="k1", GROQ_API_KEY_2="k2", GROQ_API_KEY_3="", GROQ_API_KEY_4="k4")
from agent import groqkeys, plan as planmod
assert sorted(groqkeys.keys()) == ["k1", "k2", "k4"] and sorted(groqkeys.rotated()) == ["k1", "k2", "k4"]
class R:
    def __init__(s, c, body=""): s.status_code, s.text, s._b = c, "x", body
    def json(s): return {"choices": [{"message": {"content": s._b}}]}
    def raise_for_status(s): pass
used = []
def post(url, headers, json=None, timeout=0, **k):
    used.append(headers["Authorization"][7:]); return R(200, "ok") if headers["Authorization"].endswith("k4") else R(429)
planmod.requests.post = post; planmod.time.sleep = lambda s: None
cfg = {"planner": {"model": "m1", "fallback_models": []}}
assert planmod._call_groq([], cfg) == "ok" and used[-1] == "k4"
planmod.requests.post = lambda *a, **k: R(429)
try: planmod._call_groq([], cfg); assert False
except RuntimeError as e: assert "all 3 key(s)" in str(e)
# main repo
from src import llm
assert sorted(llm.groq_keys()) == ["k1", "k2", "k4"]
seen = []
def chat(url, key, prompt, system, model, temp, tries=3):
    seen.append((key, tries))
    if key != "k4": raise llm.RateLimited("429")
    return "fine"
llm._chat = chat
assert llm._groq("p") == "fine" and seen[-1][0] == "k4"
llm._chat = lambda *a, **k: (_ for _ in ()).throw(llm.RateLimited("429"))
try: llm._groq("p"); assert False
except llm.RateLimited: pass
print("groq rotation ok")
