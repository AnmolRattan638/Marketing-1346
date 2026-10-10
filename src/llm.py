import json, os, re, time
import requests
from . import config


LOG = []   # which provider:model actually answered (or failed), shown in the Telegram draft


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
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code} from {url.split('?')[0]}: {r.text[:300]}")
            return r.json()
        except RuntimeError:
            raise
        except requests.RequestException as e:
            last = e
            time.sleep(5 * (i + 1))
    if isinstance(last, RateLimited):
        raise last
    raise RuntimeError(f"LLM request failed: {last}")


def _chat(url, key, prompt, system, model, temperature):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    d = _post(url, {"Authorization": f"Bearer {key}"}, {"model": model, "messages": msgs, "temperature": temperature})
    LOG.append(f"{url.split('/')[2].replace('api.', '')}:{model}")
    return d["choices"][0]["message"]["content"]


_FREE = None
_GMODELS = None


def _openrouter_free_models():
    """Currently-free OpenRouter models from its public list, best first (free slugs come and go)."""
    global _FREE
    if _FREE is None:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=60)
        r.raise_for_status()
        free = [m["id"] for m in r.json().get("data", [])
                if m["id"].endswith(":free") and str((m.get("pricing") or {}).get("prompt")) in ("0", "0.0")]
        ordered = []
        for pref in ("gpt-oss-120b", "llama-3.3-70b", "qwen3", "nemotron", "gemma", "deepseek"):
            ordered += [m for m in free if pref in m and m not in ordered]
        _FREE = ordered + [m for m in free if m not in ordered]
    return _FREE


def openrouter(prompt, system="", model=None, temperature=0.7):
    """Call OpenRouter. If the chosen model returns 404 (retired / no longer free), try other free models."""
    url, key = "https://openrouter.ai/api/v1/chat/completions", os.environ["OPENROUTER_API_KEY"]
    first = model or config.OPENROUTER_MODEL
    tried, last = [], None
    for attempt in range(5):
        if attempt == 0 and first:
            chosen = first
        else:
            cands = [m for m in _openrouter_free_models() if m not in tried]
            if not cands:
                break
            chosen = cands[0]
        tried.append(chosen)
        try:
            return _chat(url, key, prompt, system, chosen, temperature)
        except RuntimeError as e:
            last = e
            if "HTTP 404" not in str(e) or model:   # an explicitly requested model is not swapped
                raise
            print(f"[llm] OpenRouter {chosen} unavailable (404), trying another free model")
    raise last or RuntimeError("no free OpenRouter model available")


def _with_fallback(fn):
    """If a provider fails for any reason (rate limit, wrong model, outage), retry once through OpenRouter if a key is set."""
    def wrapper(prompt, system="", **kw):
        try:
            return fn(prompt, system, **kw)
        except Exception as e:
            if os.getenv("OPENROUTER_API_KEY"):
                print(f"[llm] {fn.__name__} failed ({str(e)[:150]}), falling back to OpenRouter")
                LOG.append(f"FAILED {fn.__name__}: {str(e)[:70]}")
                try:
                    return openrouter(prompt, system)
                except Exception as e2:
                    raise RuntimeError(f"{fn.__name__} failed: {str(e)[:300]} | OpenRouter fallback failed: {str(e2)[:300]}") from e2
            raise
    wrapper.__name__ = fn.__name__
    return wrapper


def _discover_gemini(kind):
    """Ask the Gemini API which models exist for this key and pick the newest suitable one.
    kind: 'text' (Gemini flash), 'gemma', 'image'."""
    global _GMODELS
    if _GMODELS is None:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"pageSize": 200},
                         headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} listing Gemini models: {r.text[:200]}")
        _GMODELS = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])]

    def ver(m):
        nums = re.findall(r"(\d+(?:\.\d+)?)", m)
        return (float(nums[0]) if nums else 0, float(nums[1]) if len(nums) > 1 and kind == "gemma" else 0)
    bad = ("tts", "live", "audio", "embedding", "robotics", "computer", "thinking", "learnlm", "aqa", "omni")
    if kind == "gemma":
        c = [m for m in _GMODELS if m.startswith("gemma-") and "3n" not in m and m.endswith("it")]
    elif kind == "image":
        c = [m for m in _GMODELS if m.startswith("gemini-") and "image" in m and not any(b in m for b in bad)]
        c = [m for m in c if "preview" not in m] or c
    else:
        c = [m for m in _GMODELS if m.startswith("gemini-") and "flash" in m and "image" not in m
             and "lite" not in m and not any(b in m for b in bad)]
        c = [m for m in c if "preview" not in m] or c
    return max(c, key=ver) if c else None


_ALIAS = {}


def _gemini(prompt, system="", model=None, temperature=0.8, _kind="text"):
    """Google AI Studio API (Gemini and Gemma models). If the model has been retired (404), pick a current one."""
    orig = model = model or config.GEMINI_MODEL
    model = _ALIAS.get(model, model)
    for attempt in (1, 2):
        sys_, pr = system, prompt
        if model.startswith("gemma") and sys_:     # Gemma has no system-instruction support
            pr, sys_ = sys_ + "\n\n" + pr, ""
        body = {"contents": [{"role": "user", "parts": [{"text": pr}]}],
                "generationConfig": {"temperature": temperature}}
        if sys_:
            body["systemInstruction"] = {"parts": [{"text": sys_}]}
        try:
            d = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                      {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, body)
            LOG.append(f"google:{model}")
            return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
        except RuntimeError as e:
            if attempt == 1 and "HTTP 404" in str(e):
                alt = _discover_gemini("gemma" if model.startswith("gemma") else _kind)
                if alt and alt != model:
                    print(f"[llm] {model} unavailable (404); using {alt}")
                    model = _ALIAS[orig] = alt
                    continue
            raise


def _gemma(prompt, system="", temperature=0.7):
    m = config.GEMMA_MODEL
    if "/" in m or m.endswith(":free"):          # OpenRouter-style ID, e.g. google/gemma-4-31b-it:free
        try:
            return openrouter(prompt, system, model=m, temperature=temperature)
        except Exception as e:
            print(f"[llm] {m} via OpenRouter failed ({str(e)[:120]}); trying Gemma on Google AI Studio")
            LOG.append(f"FAILED {m}: {str(e)[:60]}")
        try:
            m = _discover_gemini("gemma") or "gemma-3-27b-it"
        except Exception:
            m = "gemma-3-27b-it"
    return _gemini(prompt, system, model=m, temperature=temperature, _kind="gemma")


def _groq(prompt, system="", model=None, temperature=0.6):
    return _chat("https://api.groq.com/openai/v1/chat/completions", os.environ["GROQ_API_KEY"], prompt, system,
                 model or config.GROQ_MODEL, temperature)


def _nvidia(prompt, system="", model=None, temperature=0.6):
    return _chat("https://integrate.api.nvidia.com/v1/chat/completions", os.environ["NVIDIA_API_KEY"], prompt, system,
                 model or config.NVIDIA_MODEL, temperature)


gemini, gemma, groq, nvidia = map(_with_fallback, (_gemini, _gemma, _groq, _nvidia))


def strategist_model(prompt, system="", **kw):
    """Nemotron for the strategist. A ':free' model ID goes through OpenRouter; any other ID goes to NVIDIA.
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
    p, m = (os.getenv("FACTCHECK_PROVIDER") or "groq").lower(), os.getenv("FACTCHECK_MODEL") or None
    fn = {"groq": groq, "nvidia": nvidia, "gemini": gemini, "openrouter": openrouter}.get(p, groq)
    return fn(prompt, system, model=m, **kw) if m else fn(prompt, system, **kw)


def parse_json(text):
    """Find the JSON in a model reply, even if the model also wrote reasoning (with stray braces) around it."""
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    dec, best = json.JSONDecoder(), None
    for m in re.finditer(r"[\{\[]", t):
        try:
            obj, end = dec.raw_decode(t[m.start():])
        except Exception:
            continue
        if isinstance(obj, (dict, list)) and (best is None or end > best[1]):
            best = (obj, end)
    if best is None:
        raise ValueError("no JSON found in model reply")
    return best[0]


def ask_json(fn, prompt, system="", **kw):
    """Call a model and parse JSON; retry once asking for strict JSON."""
    out = fn(prompt + "\n\nReturn ONLY valid JSON. No prose, no markdown fences.", system, **kw)
    try:
        return parse_json(out)
    except Exception:
        out = fn(prompt + "\n\nYour last reply was not valid JSON. Return ONLY the JSON object.", system, **kw)
        return parse_json(out)
