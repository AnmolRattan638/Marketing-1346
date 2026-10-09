import json, os, re, time
import requests
from . import config


def _post(url, headers, body, tries=3, timeout=120):
    last = None
    for i in range(tries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                last = RuntimeError(f"{r.status_code} {r.text[:200]}")
                time.sleep(10 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"LLM request failed: {last}")


def gemini(prompt, system="", model=None, temperature=0.8):
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


def gemma(prompt, system="", temperature=0.7):
    return gemini(prompt, system, model=config.GEMMA_MODEL, temperature=temperature)


def groq(prompt, system="", model=None, temperature=0.6):
    """Groq's OpenAI-compatible API (GPT-OSS 120B)."""
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    d = _post("https://api.groq.com/openai/v1/chat/completions",
              {"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
              {"model": model or config.GROQ_MODEL, "messages": msgs, "temperature": temperature})
    return d["choices"][0]["message"]["content"]


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
