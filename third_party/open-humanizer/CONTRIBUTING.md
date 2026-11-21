# Contributing to Open-Humanizer

Thanks for helping keep AI writing tools open.

## Setup

```bash
git clone https://github.com/pandeyvishwas51-oss/open-humanizer.git
cd open-humanizer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -v
```

## Guidelines

- Prefer small, focused PRs.
- Every behavior change needs a unit test (mock OpenAI; no live keys in CI).
- Keep `config.DETECTOR_RULES` / `HUMANIZER_RULES` explicit — this project’s value is transparency.
- Do not commit API keys or real user documents.
- Document public API changes in the README.

## Useful directions

- Multilingual ban lists and contraction sets
- Stronger offline burstiness / POS proxies (optional deps OK if extras-gated)
- Eval scripts that log detector scores over time
- Provider examples (Ollama, OpenRouter, Azure)

## Code of conduct (short)

Be respectful. No harassment. Assume good faith in review.
