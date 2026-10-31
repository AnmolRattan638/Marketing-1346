"""Provider-agnostic LLM layer (stdlib only). Any OpenAI-compatible endpoint works: OpenAI,
OpenRouter, Ollama (/v1), vLLM, LM Studio. ``MockLLM`` is an offline stand-in for tests/demos."""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from typing import Callable, Protocol


class LLMClient(Protocol):
    def complete(self, system: str, user: str, *, json_mode: bool = False,
                 temperature: float = 0.0, max_tokens: int = 800) -> str: ...


def extract_json(text: str):
    """Pull the first JSON object/array out of an LLM reply (handles ``` fences and chatter)."""
    if text is None:
        raise ValueError("empty reply")
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    t = re.sub(r"^```(?:json)?|```$", "", t.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        s, e = t.find(open_c), t.rfind(close_c)
        if s != -1 and e > s:
            try:
                return json.loads(t[s:e + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON found in reply: {text[:120]!r}")


class OpenAICompatClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None,
                 timeout: float = 120.0):
        self.base_url = (base_url or os.getenv("VIRALSIM_LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("VIRALSIM_LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        self.model = model or os.getenv("VIRALSIM_LLM_MODEL") or "gpt-4o-mini"
        self.timeout = timeout

    def complete(self, system, user, *, json_mode=False, temperature=0.0, max_tokens=800) -> str:
        body = {"model": self.model, "temperature": temperature, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)["choices"][0]["message"]["content"]


class MockLLM:
    """Deterministic offline stand-in. NOT a predictor: replies are hash-seeded so tests are stable."""
    def __init__(self, responder: Callable[[str, str], str] | None = None):
        self.responder, self.calls = responder, []

    def complete(self, system, user, *, json_mode=False, temperature=0.0, max_tokens=800) -> str:
        self.calls.append((system, user))
        if self.responder:
            return self.responder(system, user)
        h = int(hashlib.sha256((system + user).encode()).hexdigest(), 16)
        u = lambda k: ((h >> (8 * k)) & 0xFF) / 255.0
        acts = ["like", "reply", "share", "ignore", "dislike", "post"]
        return json.dumps({"action": acts[int(u(0) * 5.99)], "content": "(mock reply)",
                           "sentiment": ["positive", "neutral", "negative", "mixed"][int(u(1) * 3.99)],
                           "sentiment_score": round(u(2) * 2 - 1, 2),
                           "like": u(3) < .5, "comment": u(4) < .2, "share": u(5) < .15, "quote": u(6) < .05})


def get_client(kind: str | None = None) -> LLMClient:
    kind = (kind or os.getenv("VIRALSIM_LLM") or "mock").lower()
    return MockLLM() if kind == "mock" else OpenAICompatClient()
