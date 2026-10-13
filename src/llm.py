import json, os, random, re, time
import requests
from . import config


LOG = []        # short lines shown in the Telegram draft: which provider:model answered or failed
FAILURES = []   # full detail of every failure in this run; saved with the draft so a problem can be diagnosed afterwards
_DOWN = {}      # "provider:model" -> time until which it is skipped (circuit breaker)
COOLDOWN = 600  # seconds a model that returned a server error is skipped: one outage costs one wait, not one per call


class RateLimited(RuntimeError):
    pass


class ProviderDown(RuntimeError):
    """Server error (500/502/503/504) or unreachable. Waiting on the same model rarely helps; switching model usually does."""


def _scrub(text):
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "TELEGRAM_BOT_TOKEN"):
        v = os.environ.get(k)
        if v and len(v) > 6:
            text = text.replace(v, "***")
    return text


def _retry_after(r):
    """Seconds the provider asks us to wait: Retry-After header, or Gemini's retryDelay / 'retry in 12s' in the body."""
    try:
        h = r.headers.get("Retry-After")
        if h and h.replace(".", "", 1).isdigit():
            return float(h)
    except Exception:
        pass
    m = re.search(r'retry(?:Delay)?"?\s*(?:in|:)?\s*"?(\d+(?:\.\d+)?)s', r.text or "", re.I)
    return float(m.group(1)) if m else None


def _post(url, headers, body, tries=3, timeout=120):
    """429: wait as asked (capped) and retry. 5xx / unreachable: one quick retry, then raise ProviderDown so the caller can switch model.
    Other 4xx (bad key, bad request, unknown model): raise at once, retrying cannot help."""
    host = url.split("/")[2]
    last, net_fail, server_fail = None, 0, 0
    for i in range(tries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as e:
            net_fail += 1
            last = ProviderDown(f"{host} unreachable: {type(e).__name__}")
            if net_fail >= 2:
                raise last
            time.sleep(3 + random.random() * 2)
            continue
        if r.status_code == 429:
            last = RateLimited(f"HTTP 429 from {host}: {_scrub(r.text[:200])}")
            if i < tries - 1:
                time.sleep(min(max(_retry_after(r) or 0, 5 * (i + 1)), 45))
            continue
        if r.status_code in (500, 502, 503, 504):
            server_fail += 1
            last = ProviderDown(f"HTTP {r.status_code} from {host}: {_scrub(r.text[:300])}")
            if server_fail >= 2:
                raise last
            time.sleep(3 + random.random() * 2)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} from {host}: {_scrub(r.text[:300])}")
        try:
            return r.json()
        except ValueError:
            raise ProviderDown(f"{host} returned a non-JSON reply (HTTP {r.status_code})")
    raise last or RuntimeError("LLM request failed")


def _down(key):
    return _DOWN.get(key, 0) > time.time()


def _fail(provider, model, err, t0):
    """Record a failure in full (FAILURES) and briefly (LOG); a server error or rate limit also benches the model for COOLDOWN seconds."""
    key = f"{provider}:{model}"
    m = re.search(r"\bHTTP (\d{3})\b", str(err))
    FAILURES.append({"model": key, "status": m.group(1) if m else type(err).__name__, "seconds": round(time.time() - t0, 1),
                     "error": _scrub(str(err))[:300]})
    LOG.append(f"FAILED {key} ({'HTTP ' + m.group(1) if m else type(err).__name__})")
    if isinstance(err, (ProviderDown, RateLimited)):
        _DOWN[key] = time.time() + COOLDOWN


def _chat(url, key, prompt, system, model, temperature):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    provider, t0 = url.split("/")[2].replace("api.", ""), time.time()
    try:
        d = _post(url, {"Authorization": f"Bearer {key}"}, {"model": model, "messages": msgs, "temperature": temperature})
    except Exception as e:
        _fail(provider, model, e, t0)
        raise
    LOG.append(f"{provider}:{model}")
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
    """Call OpenRouter. If the chosen model is gone (404), erroring (5xx) or rate limited, try other free models.
    An explicitly requested model is never swapped: the caller decides what happens next."""
    url, key = "https://openrouter.ai/api/v1/chat/completions", os.environ["OPENROUTER_API_KEY"]
    first = model or config.OPENROUTER_MODEL
    tried, last = [], None
    for attempt in range(5):
        if attempt == 0 and first:
            chosen = first
        else:
            cands = [m for m in _openrouter_free_models() if m not in tried and not _down(f"openrouter.ai:{m}")]
            if not cands:
                break
            chosen = cands[0]
        tried.append(chosen)
        if _down(f"openrouter.ai:{chosen}"):
            if model:
                raise ProviderDown(f"{chosen} skipped: it returned server errors earlier in this run")
            continue
        try:
            return _chat(url, key, prompt, system, chosen, temperature)
        except RuntimeError as e:
            last = e
            if model or not ("HTTP 404" in str(e) or isinstance(e, (ProviderDown, RateLimited))):
                raise
            print(f"[llm] OpenRouter {chosen} unavailable ({str(e)[:90]}), trying another free model")
    raise last or RuntimeError("no free OpenRouter model available")


def _with_fallback(fn):
    """If every model of a provider fails, retry through OpenRouter and then Groq, so a request never dies because one vendor is down."""
    def wrapper(prompt, system="", **kw):
        try:
            return fn(prompt, system, **kw)
        except Exception as e:
            chain = []
            if os.getenv("OPENROUTER_API_KEY"):
                chain.append(("OpenRouter", lambda: openrouter(prompt, system)))
            if os.getenv("GROQ_API_KEY") and fn.__name__ != "_groq":
                chain.append(("Groq", lambda: _groq(prompt, system)))
            if not chain:
                raise
            first = _scrub(str(e))[:300]
            print(f"[llm] {fn.__name__} failed ({first[:150]}), falling back")
            LOG.append(f"FAILED {fn.__name__.lstrip('_')}: all its models")
            errs = [f"{fn.__name__}: {first}"]
            for name, call in chain:
                try:
                    return call()
                except Exception as e2:
                    errs.append(f"{name}: {_scrub(str(e2))[:200]}")
            raise RuntimeError(" | ".join(errs)) from e
    wrapper.__name__ = fn.__name__
    return wrapper


def _gemini_models():
    global _GMODELS
    if _GMODELS is None:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"pageSize": 200},
                         headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} listing Gemini models: {r.text[:200]}")
        _GMODELS = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])]
    return _GMODELS


def _rank_gemini(kind):
    """Suitable models for this key, newest first. kind: 'text' (Gemini flash), 'gemma', 'image'."""
    models = _gemini_models()

    def ver(m):
        nums = re.findall(r"(\d+(?:\.\d+)?)", m)
        return (float(nums[0]) if nums else 0, float(nums[1]) if len(nums) > 1 and kind == "gemma" else 0)
    bad = ("tts", "live", "audio", "embedding", "robotics", "computer", "thinking", "learnlm", "aqa", "omni")
    if kind == "gemma":
        c = [m for m in models if m.startswith("gemma-") and "3n" not in m and m.endswith("it")]
    elif kind == "image":
        c = [m for m in models if m.startswith("gemini-") and "image" in m and not any(b in m for b in bad)]
        c = [m for m in c if "preview" not in m] or c
    else:
        c = [m for m in models if m.startswith("gemini-") and "flash" in m and "image" not in m
             and "lite" not in m and not any(b in m for b in bad)]
        c = [m for m in c if "preview" not in m] or c
    return sorted(c, key=ver, reverse=True)


def _discover_gemini(kind):
    ranked = _rank_gemini(kind)
    return ranked[0] if ranked else None


_ALIAS = {}
_STATIC = {"text": ["gemini-flash-latest", "gemini-flash-lite-latest"], "gemma": ["gemma-3-27b-it"]}


def _gemini_ladder(model, kind):
    """The model asked for, then the next-best Google models: Google's own advice for a 500 or 503 is to switch model."""
    ladder = [model]
    try:
        ladder += _rank_gemini(kind)[:2]
    except Exception:
        ladder += _STATIC.get(kind, [])
    if kind == "gemma":                                  # no Gemma answering: a Gemini Flash can still do the job
        try:
            ladder += _rank_gemini("text")[:1]
        except Exception:
            ladder += _STATIC["text"][:1]
    return list(dict.fromkeys(ladder))[:5]


def _gemini(prompt, system="", model=None, temperature=0.8, _kind="text"):
    """Google AI Studio API (Gemini and Gemma). A model that is retired (404), erroring (5xx), overloaded or rate limited
    is skipped for the next-best Google model; only when all of them fail does the caller fall back to another provider."""
    orig = model or config.GEMINI_MODEL
    start = _ALIAS.get(orig, orig)
    ladder = _gemini_ladder(start, _kind)
    live = [m for m in ladder if not _down(f"google:{m}")] or ladder[:1]
    errors, retired = [], False
    for m in live:
        sys_, pr = system, prompt
        if m.startswith("gemma") and sys_:             # Gemma has no system-instruction support
            pr, sys_ = sys_ + "\n\n" + pr, ""
        body = {"contents": [{"role": "user", "parts": [{"text": pr}]}],
                "generationConfig": {"temperature": temperature}}
        if sys_:
            body["systemInstruction"] = {"parts": [{"text": sys_}]}
        t0 = time.time()
        try:
            d = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                      {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, body)
        except RuntimeError as e:
            _fail("google", m, e, t0)
            gone = "HTTP 404" in str(e)
            if isinstance(e, (ProviderDown, RateLimited)) or gone:
                errors.append(f"{m}: {_scrub(str(e))[:120]}")
                retired = retired or (gone and m == start)
                continue
            raise                                       # bad key / bad request: another model will not fix it
        LOG.append(f"google:{m}")
        if retired and m != start:
            _ALIAS[orig] = m                            # the configured model was retired: use the replacement from now on
        return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
    raise ProviderDown("all Google models failed: " + " | ".join(errors))


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
