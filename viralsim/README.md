# ViralSim

Forecast how a post will spread **before you publish it**, then find out what to change.

ViralSim merges seven open-source projects into one dependency-light Python package
(only `numpy` + `scipy`; everything else is optional). It runs fully offline, and gets better when
you plug in an LLM.

```bash
pip install .                      # add [ml] for the early-signal model
viralsim analyze "Unpopular opinion: remote work is overrated. What do you think?" \
    --creator examples/creator.json --trend examples/trend.json --network
viralsim ab "Version A text" "Version B text"
viralsim serve                     # http://127.0.0.1:8000  (API + small web UI)
viralsim backtest                  # measure the model against 50 known campaigns
```

## What you get

| Capability | Module | Origin |
|---|---|---|
| Monte-Carlo feed-wave simulation over a 50,000-persona audience: reach p10/p50/p90, breakout probability, per-wave bands | `sim/wave.py` | Content-diffusion |
| Follower-graph cascade: fatigue, saturation, backlash, social proof, moderation, opinion dynamics, polarisation | `sim/network.py` | SocialNetSim |
| Hawkes self-exciting fit + "how big will it get" forecast from early events | `sim/hawkes.py` | SocialNetSim |
| Hybrid agents: LLM-driven core agents with memory + many persona-grounded ordinary agents, role incentives, crowd pulse, interviews | `agents.py` | HiSim, PhantomCrowd, Viralix |
| Platform-signal heuristics (reply/link/hook/negative-signal risk) | `signals.py` | x-virality-predictor |
| 8-dimension content scoring: offline heuristic or LLM rubric | `dimensions.py` | Content-diffusion |
| Backlash/controversy detection (rules, optionally LLM), discourse tension | `risk.py` | PhantomCrowd, Viralix |
| A/B: paired Monte Carlo, proper z-test, LLM-persona voting | `ab.py` | viral-predictor |
| Counterfactual optimiser: ranked levers by paired re-simulation, text edits, LLM rewrite | `optimize.py` | Content-diffusion |
| Backtest + calibration metrics (Pearson, MAE, AUC, Brier, ECE) | `calibrate.py` | PhantomCrowd |
| Early-signal virality classifier trained on simulated cascades | `ml.py` | SocialNetSim |
| Trend alignment (topic/entity/tag, fuzzy Jaccard) | `trends.py` | Content-diffusion |
| Creator scores (trust, momentum, niche authority, audience quality, volatility) | `creator.py` | Content-diffusion |

Python API:

```python
from viralsim.pipeline import analyze
from viralsim.llm import OpenAICompatClient      # OpenAI, OpenRouter, Ollama /v1, vLLM...
r = analyze("your post", llm=OpenAICompatClient(model="gpt-4o-mini"), with_network=True)
print(r["viral_score"], r["forecast"]["reach_p50"], r["suggestions"]["counterfactual"])
```

## Read this before trusting a number

* **Offline mode scores content with a lexical heuristic.** It is coarse. On the bundled 50-campaign
  backtest the offline pipeline did **not** beat a constant guess (Pearson -0.17, AUC 0.53, MAE worse
  than predicting 50). That set is brand-campaign *quality*, a different target than reach, so this is
  not proof the simulator is wrong, but it is no evidence it is right either. PhantomCrowd reported
  r = 0.47 for its LLM pipeline on the same set; ViralSim's LLM mode has **not** been benchmarked yet.
  Run `viralsim backtest` with your own model and treat the result as the real accuracy figure.
* The simulators are internally consistent models (verified: Python port matches the original C++
  simulator within Monte-Carlo noise; Hawkes fitting recovers known parameters), but their constants are
  hand-set, not fitted to real platform data. `confidence` is a reliability heuristic, not a calibrated probability.
* The platform-signal weights are estimates, not X's production weights.
* The web UI and the LLM prompts (`openai` client against a real provider) were not exercised against
  live services in the build environment; the HTTP client is tested against a local fake server.

## Layout

```
src/viralsim/   pipeline.py (entry)  sim/ (wave, network, hawkes)  agents.py  signals.py  dimensions.py
                risk.py  ab.py  optimize.py  calibrate.py  ml.py  trends.py  creator.py  audience.py
                engagement.py  llm.py  server.py  cli.py  web/  data/
tests/          35 unit/integration tests (python -m unittest)
docs/ARCHITECTURE.md   design, provenance, what was deliberately left out
```

Run tests: `PYTHONPATH=src python -m unittest discover -s tests -t .`

Licences and attributions: see `NOTICE.md` (one source repo has no licence file; action item there).
