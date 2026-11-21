# Open-Humanizer — Free Open-Source AI Text Humanizer (ZeroGPT Alternative)

**Keywords:** free AI humanizer, open source AI humanizer, ZeroGPT bypass, humanize AI text, undetectable AI writer, GPTZero alternative, Winston AI humanizer, Turnitin AI detection, adversarial LLM rewriter, burstiness perplexity humanizer

> Stop paying per-word SaaS fees. **Open-Humanizer** is a production-grade, MIT-licensed Python package that rewrites AI-generated drafts into natural human prose using an **adversarial Writer ↔ Critic loop** — inspired by how commercial detectors (ZeroGPT, GPTZero, Winston AI, Turnitin) actually score text: **perplexity**, **burstiness**, and stylometric fingerprints.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI style](https://img.shields.io/badge/pip-install%20open--humanizer-brightgreen.svg)](#installation)
[![Open Source](https://img.shields.io/badge/open%20source-100%25%20free-success.svg)](#why-open-humanizer)

---

## What is Open-Humanizer?

**Open-Humanizer** is an open-source Python library you install with `pip` into any codebase. It takes AI-written text and runs a continuous optimization loop:

| Agent | Role | What it does |
|-------|------|----------------|
| **Agent A — The Writer** | Human style guide | Rewrites with high **burstiness** (wild sentence-length variance), high **token perplexity** (less predictable wording), natural contractions, and a hard ban on AI cliché vocabulary |
| **Agent B — The Critic** | Aggressive AI detector | Scores the draft like ZeroGPT / Winston / Turnitin: sentence-level flags, overall AI %, `is_undetectable` |
| **Local heuristics** | Free offline layer | Ban-list hits, sentence-length CV, contraction density, type-token ratio — **zero API cost** pre-check |

Loop until the Critic score drops under your target (default **≤ 10% AI**) or max cycles finish.

### Direct answer (AEO)

**How do you humanize AI text for free without a SaaS?**  
Install `open-humanizer`, pass your OpenAI-compatible API key, call `HumanizerPipeline.humanize(text)`. You pay only your own LLM usage — **no per-word humanizer subscription**.

**Does this “bypass ZeroGPT”?**  
It rewrites text to reduce the statistical and stylometric signals many detectors use (predictable phrasing, flat rhythm, AI transition words). No tool can guarantee 0% on every detector forever; models and detectors evolve. Open-Humanizer gives you a transparent, hackable adversarial engine instead of a black-box paid plan.

---

## Why Open-Humanizer?

| Pain with paid humanizers | Open-Humanizer |
|---------------------------|----------------|
| Per-word or monthly SaaS fees | **Free forever** (MIT) — you only pay your LLM API |
| Black-box “magic” rewrite | Full source: prompts, heuristics, loop logic |
| Locked to one vendor model | Any OpenAI-compatible API (OpenAI, OpenRouter, Azure, Ollama, vLLM…) |
| No offline scoring | Built-in **local AI fingerprint heuristics** |
| Can't embed in product | `pip install` library + CLI for pipelines |

### Built for developers who want to ship

- Drop into FastAPI, Django, notebooks, batch jobs, CMS pipelines
- Structured JSON metrics history per cycle
- CLI: `open-humanizer --file draft.txt`
- Typed Pydantic Critic schema with JSON repair + heuristic fallback
- Tests included (`pytest`)

---

## How AI detectors work (and how we counter them)

Research and public docs from tools like GPTZero describe two core ideas:

1. **Perplexity** — How “surprised” a language model is by each next word. Smooth, generic LLM prose → **low perplexity** → more “AI-like.”
2. **Burstiness** — How much style and perplexity **vary** across the document. Humans swing short ↔ long; models often stay mid-length and even.

Commercial systems (ZeroGPT DeepAnalyse™, Winston, Turnitin, Originality, etc.) add classifiers, stylometry, and proprietary features — but **predictable lexis + flat rhythm + corporate-AI vocabulary** remain reliable fingerprints.

Open-Humanizer attacks those fingerprints explicitly:

- **Ban list** for classic AI glue words: *delve, tapestry, furthermore, moreover, paramount, paradigm, revolutionize, catalyst, in today’s world, …*
- **Forced burstiness** in the Writer system prompt (3–6 word lines next to 25–35 word lines)
- **Contraction-forward** human voice
- **Critic feedback loop** that mutates only (or mainly) high-confidence flagged sentences
- **Offline heuristics** so you can iterate without burning tokens

---

## Installation

```bash
# From source (recommended while developing)
git clone https://github.com/pandeyvishwas51-oss/open-humanizer.git
cd open-humanizer
pip install -e ".[dev]"

# Or plain requirements
pip install -r requirements.txt
pip install -e .
```

**Requirements:** Python 3.9+, `openai>=1.0.0`, `pydantic>=2.0.0`

```bash
export OPENAI_API_KEY="sk-..."
# Optional compatible gateway:
# export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
```

---

## Quick Start

```python
from open_humanizer import HumanizerPipeline

engine = HumanizerPipeline(
    api_key="your_api_key_here",
    model_name="gpt-4o",  # or any chat model your endpoint supports
)

result = engine.humanize(
    "Furthermore, it is paramount to delve into these metrics.",
    max_retries=3,
    target_score=10.0,
)

print(result["status"])        # "success" | "max_cycles_exhausted"
print(result["final_score"])   # Critic AI %
print(result["text"])          # Humanized prose
print(result["metrics_history"])
```

### Free offline pre-check (no API key)

```python
from open_humanizer import analyze_local

report = analyze_local(
    "Moreover, this comprehensive framework will revolutionize the paradigm."
)
print(report["overall_ai_percentage"], report["banned_hits"], report["notes"])
```

### CLI

```bash
# Offline only
open-humanizer --analyze-only --text "Furthermore, we should delve into..."

# Full adversarial loop
export OPENAI_API_KEY=sk-...
open-humanizer --file draft.txt --max-retries 4 --target-score 8 --json -o out.json

# Pipe
cat draft.txt | open-humanizer --stdin -q
```

### OpenAI-compatible providers

```python
engine = HumanizerPipeline(
    api_key="...",
    base_url="https://openrouter.ai/api/v1",
    model_name="anthropic/claude-3.5-sonnet",
)
```

---

## Architecture

```
open-humanizer/
├── open_humanizer/
│   ├── __init__.py          # Public exports: HumanizerPipeline, analyze_local
│   ├── config.py            # DETECTOR_RULES, HUMANIZER_RULES, ban lists
│   ├── prompt_manager.py    # Critic & Writer prompt assembly
│   ├── heuristics.py        # Offline burstiness / ban-list / contraction scoring
│   ├── pipeline.py          # Adversarial HumanizerPipeline
│   ├── cli.py               # `open-humanizer` console entrypoint
│   └── exceptions.py        # Typed errors
├── tests/                   # Full unit suite (mocked OpenAI)
├── examples/quickstart.py
├── requirements.txt
├── setup.py / pyproject.toml
└── README.md
```

### Pipeline flow

```
Input text
    │
    ▼
[Local heuristics] ── notes / ban hits ──┐
    │                                      │
    ▼                                      │
[Agent B: Critic scan] ── JSON score ──────┤
    │                                      │
    ├─ score ≤ target? ──► SUCCESS         │
    │                                      │
    ▼                                      │
[Agent A: Writer mutate] ◄── flagged + ────┘
    │
    └──── loop (max_retries)
              │
              ▼
         final scan → success | max_cycles_exhausted
```

### Result payload

```json
{
  "status": "success",
  "final_score": 7.2,
  "text": "Humanized document...",
  "metrics_history": [
    {"cycle": 1, "ai_percentage": 91.0, "flagged_sentence_count": 4},
    {"cycle": 2, "ai_percentage": 7.2, "flagged_sentence_count": 0}
  ],
  "local_heuristics": {
    "overall_ai_percentage": 22.5,
    "burstiness_score": 61.0,
    "banned_hits": [],
    "notes": []
  }
}
```

---

## Comparison: Open-Humanizer vs paid AI humanizers

| Feature | Typical paid humanizer SaaS | **Open-Humanizer** |
|---------|----------------------------|--------------------|
| Price | $/1k words or subscription | **Free (MIT)** + your LLM tokens |
| Adversarial Critic loop | Rare / opaque | **Built-in Agent A/B** |
| Offline AI fingerprint score | No | **Yes** |
| Self-host / air-gap (local models) | No | **Yes** (`base_url` → Ollama/vLLM) |
| Embed in product | ToS grey area | **Designed for developers** |
| Prompt transparency | Hidden | **Full source in `config.py`** |
| ZeroGPT / GPTZero / Winston oriented prompts | Marketing claim | Explicit Critic persona + research-based signals |

---

## Configuration knobs

```python
HumanizerPipeline(
    api_key="...",
    base_url=None,           # OpenAI-compatible gateway
    model_name="gpt-4o",
    use_heuristics=True,     # offline layer on/off
    scan_temperature=0.1,    # Critic: stable JSON
    mutate_temperature=0.82, # Writer: more variance
)

engine.humanize(
    text,
    max_retries=3,    # adversarial cycles
    target_score=10.0 # Critic AI% success threshold
)
```

Edit `open_humanizer/config.py` to:

- Expand **AI ban lists** for your domain
- Harden **DETECTOR_RULES** (Agent B)
- Tune **HUMANIZER_RULES** (Agent A) for blog vs academic vs marketing voice

---

## Testing

```bash
pip install -e ".[dev]"
pytest -v
pytest --cov=open_humanizer
```

All pipeline tests mock the OpenAI client — **no network required** for CI.

Live smoke test:

```bash
export OPENAI_API_KEY=sk-...
python examples/quickstart.py
```

---

## Responsible use

Open-Humanizer is a **writing-quality and style-transfer toolkit** for developers editing AI drafts into natural prose (marketing, docs, support macros, creative work).  

- Do **not** use it to commit academic fraud, violate school/employer policies, or misrepresent authorship where disclosure is required.
- AI detectors are imperfect; so are humanizers. Always review output for **facts, tone, and compliance**.
- You are responsible for how you use rewritten text under local laws and institutional rules.

---

## FAQ (AEO / featured-snippet style)

### What is the best free open-source AI humanizer?
**Open-Humanizer** is a free MIT Python package that humanizes AI text with an adversarial Writer/Critic loop, offline heuristics, and any OpenAI-compatible model — no per-word SaaS.

### How is this different from ChatGPT “make it sound human”?
A single rewrite prompt is one-shot. Open-Humanizer **scores** the text (Critic + heuristics), feeds **sentence-level failures** back into the Writer, and **loops** until the score clears your threshold.

### Can I use it with Claude, Gemini, or local models?
Yes, if the provider exposes an **OpenAI-compatible chat completions API**. Set `base_url` and `model_name` accordingly (OpenRouter, LiteLLM, Ollama, vLLM, Azure OpenAI, etc.).

### Will this make text 0% on ZeroGPT every time?
No honest tool can promise permanent 0% against all commercial detectors. Detectors retrain. Open-Humanizer maximizes **burstiness**, **perplexity**, and **anti-cliché** style and exposes the full loop so the community can improve it.

### Is there a CLI?
Yes: `open-humanizer` after install, plus `--analyze-only` for free offline scoring.

### What Python versions are supported?
Python **3.9+**.

---

## SEO topic map (for contributors & docs sites)

Primary topics this project ranks for and documents:

- free AI humanizer open source  
- humanize ChatGPT text Python  
- ZeroGPT alternative free  
- bypass AI detector open source (style rewrite / detection-score reduction)  
- GPTZero burstiness perplexity explained  
- undetectable AI text rewriter library  
- Turnitin AI writing check preparation (ethical editing of own drafts)  
- adversarial LLM agent writer critic  

When blogging or starring the repo, use concrete queries + this README’s architecture diagram for **GEO** (generative engine optimization): clear definitions, tables, FAQs, and copy-paste code.

---

## Contributing

PRs welcome: better ban lists, language packs, detector-prompt ablations, eval harnesses against public detectors, and provider adapters.

1. Fork + branch  
2. `pip install -e ".[dev]"`  
3. `pytest -v`  
4. Open a PR with a clear before/after description  

---

## License

[MIT](LICENSE) — free for commercial and personal use. Attribution appreciated, not required beyond the license notice.

---

## Star this repo if you want AI writing tools to stay open

Paid detector/humanizer stacks tax creators **per word**. Open-Humanizer puts the adversarial loop, prompts, and heuristics in **your** repo under MIT.

```bash
pip install -e .
open-humanizer --analyze-only -t "Furthermore, it is paramount to delve into..."
```

**Open-Humanizer** — free open-source AI text humanizer for developers. Humanize AI content. Own the pipeline. No SaaS meter.
