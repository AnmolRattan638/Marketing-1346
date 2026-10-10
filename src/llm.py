import json, os, re, time
import requests
from . import config


class RateLimited(RuntimeError):
    pass


def _post(url, headers, body, tries=3, timeout=120):
    last = None
    for i in range(tries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                last = RateLimited(f"429 {r.text[:200]}") if r.status_code == 429 else RuntimeError(f"{r.status_code} {r.text[:200]}")
                time.sleep(10 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last = e
            time.sleep(5 * (i + 1))
    if isinstance(last, RateLimited):
        raise last
    raise RuntimeError(f"LLM request failed: {last}")


def _chat(url, key, prompt, system, model, temperature):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    d = _post(url, {"Authorization": f"Bearer {key}"}, {"model": model, "messages": msgs, "temperature": temperature})
    return d["choices"][0]["message"]["content"]


def openrouter(prompt, system="", model=None, temperature=0.7):
    return _chat("https://openrouter.ai/api/v1/chat/completions", os.environ["OPENROUTER_API_KEY"], prompt, system,
                 model or config.OPENROUTER_MODEL, temperature)


def _with_fallback(fn):
    """On a 429 (after retries), retry once through OpenRouter if a key is set."""
    def wrapper(prompt, system="", **kw):
        try:
            return fn(prompt, system, **kw)
        except RateLimited:
            if os.getenv("OPENROUTER_API_KEY"):
                print(f"[llm] {fn.__name__} rate limited, falling back to OpenRouter")
                return openrouter(prompt, system)
            raise
    wrapper.__name__ = fn.__name__
    return wrapper


def _gemini(prompt, system="", model=None, temperature=0.8):
    """Google AI Studio API (Gemini and Gemma models)."""
    model = model or config.GEMINI_MODEL
    if model.startswith("gemma") and system:  # Gemma has no system-instruction support
        prompt, system = system + "\n\n" + prompt, ""
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    d = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
              {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, body)
    return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])


def _gemma(prompt, system="", temperature=0.7):
    return _gemini(prompt, system, model=config.GEMMA_MODEL, temperature=temperature)


def _groq(prompt, system="", model=None, temperature=0.6):
    return _chat("https://api.groq.com/openai/v1/chat/completions", os.environ["GROQ_API_KEY"], prompt, system,
                 model or config.GROQ_MODEL, temperature)


def _nvidia(prompt, system="", model=None, temperature=0.6):
    return _chat("https://integrate.api.nvidia.com/v1/chat/completions", os.environ["NVIDIA_API_KEY"], prompt, system,
                 model or config.NVIDIA_MODEL, temperature)


gemini, gemma, groq, nvidia = map(_with_fallback, (_gemini, _gemma, _groq, _nvidia))


def strategist_model(prompt, system="", **kw):
    """Nemotron for strategist/analyst. A ':free' model ID goes through OpenRouter; any other ID goes to NVIDIA.
    If that fails for any reason, GPT-OSS on Groq answers instead."""
    model = config.NVIDIA_MODEL
    try:
        if ":free" in model:
            return openrouter(prompt, system, model=model)
        if os.getenv("NVIDIA_API_KEY"):
            return nvidia(prompt, system, model=model, **kw)
    except Exception as e:
        print(f"[llm] strategist model failed ({str(e)[:120]}), using Groq")
    return groq(prompt, system, **kw)


def factcheck_model(prompt, system="", **kw):
    """Provider/model chosen by FACTCHECK_PROVIDER + FACTCHECK_MODEL (default: GPT-OSS on Groq)."""
    p, m = os.getenv("FACTCHECK_PROVIDER", "groq").lower(), os.getenv("FACTCHECK_MODEL") or None
    fn = {"groq": groq, "nvidia": nvidia, "gemini": gemini, "openrouter": openrouter}.get(p, groq)
    return fn(prompt, system, model=m, **kw) if m else fn(prompt, system, **kw)


def parse_json(text):
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", t, re.S)
        if not m:
            raise
        return json.loads(m.group(1))


def ask_json(fn, prompt, system="", **kw):
    """Call a model and parse JSON; retry once asking for strict JSON."""
    out = fn(prompt + "\n\nReturn ONLY valid JSON. No prose, no markdown fences.", system, **kw)
    try:
        return parse_json(out)
    except Exception:
        out = fn(prompt + "\n\nYour last reply was not valid JSON. Return ONLY the JSON object.", system, **kw)
        return parse_json(out)
