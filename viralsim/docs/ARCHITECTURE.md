# Architecture

```
text/media ─► content vector (8 dims, topics, entities) ─┐   creator scores ─┐   trend snapshot ─┐
                                                         ▼                   ▼                   ▼
                                              engagement.py  (persona × content → watch/like/comment/share/save/follow)
                                                         │
        ┌────────────────────────┬───────────────────────┼──────────────────────┐
        ▼                        ▼                       ▼                      ▼
  sim/wave.py              agents.py               sim/network.py          signals.py + risk.py
  feed waves, MC           core(LLM)+ordinary      graph cascade,          platform heuristics,
  reach distribution       agents, memory, roles   opinions, moderation    backlash penalty
        └────────────────────────┴───────────┬───────────┴──────────────────────┘
                                             ▼
                          pipeline.viral_score  →  report.py / server.py / cli.py
                                             ▼
                      optimize.py (counterfactual levers)   ab.py   calibrate.py
```

## Design decisions

* **One content vector, many simulators.** Content-diffusion's 8-dimension vector is the shared contract.
  Feed-driven platforms (TikTok/Reels/Shorts) use `sim/wave.py`; follower-graph platforms use `sim/network.py`;
  qualitative reactions come from `agents.py`.
* **Persona reactions are deterministic given the content**, so `engage_all` precomputes them once for the
  whole pool and each Monte-Carlo run only samples viewers. 5,000 runs over 50k personas take ~2 s in numpy
  (the original needed a C++ build). Fixed seeds make counterfactual comparisons paired.
* **LLM optional everywhere.** Every LLM call has a deterministic fallback, so the pipeline never fails because
  a model returned bad JSON. `llm.py` speaks the OpenAI-compatible protocol over stdlib `urllib`.
* **Ordinary agents are persona-grounded, not random.** PhantomCrowd's rule agents picked actions from a fixed
  list; here they reuse the persona engagement model, so the cheap crowd and the Monte-Carlo model agree.
* **Zero-dependency serving.** `server.py` uses `http.server`; swap in FastAPI/React later without touching the core.

## Fixes made while merging

| Issue in a source repo | Resolution |
|---|---|
| viral-predictor ran a z-test with the wrong sample sizes and treated all actions as one total | Per-metric one-sided two-proportion z-test with degenerate-case handling; paired simulation alternative |
| viral-predictor sent the same prompt to every "user" | Each simulated user is a sampled persona |
| x-virality: comments said "-400% link tax" but code applied x0.25; exactly 3 hashtags were never penalised | Consistent 0.25 multiplier in text; 3+ hashtags penalised |
| Viralix "structural virality" was out-degree variance | True definition: mean pairwise distance (Wiener index), unit-tested on known trees |
| Content-diffusion Jaccard counted duplicate tokens | Set-based Jaccard |
| PhantomCrowd rule agents ignored persona and content | Persona-driven behaviour model |

## Deliberately not ported (and why)

* Trend collectors (Reddit/YouTube/Google Trends), the semantic trend graph, and creator OAuth fetchers: they
  need API keys and network. `TrendSnapshot` is the integration point; produce one JSON from any source.
* Image/video understanding (Ollama VLM, Whisper): heavy dependencies. Use `LLMScorer` or pass a `Content` vector.
* Viralix's Supabase/pgvector GraphRAG, Zep memory, scrapers, MCP server, PDF export, and PhantomCrowd's
  LightRAG knowledge graph and Vue frontend. Each is infrastructure-heavy; the in-process `AgentMemory` covers
  the simulation need. These are the natural next modules.
* The original C++ simulator: superseded by the numpy port (parity-checked), keeping a single-language stack.

## Extending

* New platform: add a `PLATFORMS` preset of seed/engagement constants and choose wave vs network simulator.
* Calibrate: fit constants (`R_GAIN`, share scale, gate weights) against real outcome data with `calibrate.backtest`.
