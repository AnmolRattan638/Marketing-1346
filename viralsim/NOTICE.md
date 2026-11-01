# Provenance and licences

ViralSim merges ideas, equations, data and (where noted) re-implemented logic from seven projects.
Please keep this file when redistributing.

| Source repo | Licence | What ViralSim took |
|---|---|---|
| Content-diffusion (Kishan Arya) | MIT | Wave/Monte-Carlo model equations, engagement gate, trend alignment, creator scores, counterfactual levers, **bundled 50k persona pool** (`data/personas_50k.jsonl.gz`). Python port of the C++ logic. |
| PhantomCrowd | MIT | Agent memory + relationships, crowd-pulse feedback, tiered LLM/rule agents, controversy categories, interview feature, **50-campaign backtest set** (`data/backtest_campaigns.json`). |
| SocialNetSim (M. Lakhili) | MIT | Interest/ideology-weighted attachment, SIR-style diffusion with fatigue/saturation/backlash, Hawkes process, bounded-confidence opinion dynamics, moderation, early-signal ML idea. Re-implemented. |
| social_simulation / HiSim (X. Mou et al.) | MIT | Core-LLM + ordinary-ABM hybrid agent design (paper: arXiv:2402.16333). Concept only; the repo ships a project web page, not the simulator. |
| Viralix | Apache-2.0 | Role-based agents (public/influencer/brand/academic/competitor), declared-vs-text sentiment "discourse tension", cascade metrics idea, grounded-report idea. Re-implemented; no code copied. |
| viral-predictor | README says MIT, **no LICENSE file** | A/B-test-by-simulated-users concept and statistical-confidence display. Re-implemented (and statistically corrected). |
| x-virality-predictor | **No licence file** | Signal-weight heuristics (`signals.py`: weights, hook/CTA patterns). Constants and patterns were adapted. **Action needed:** confirm permission with the author or replace `signals.py` before commercial redistribution. |

Data: the persona pool derives from NVIDIA Nemotron-Personas-USA (CC BY 4.0), mapped to the persona schema by the Content-diffusion authors; attribution required.
Taxonomy note: the 24-topic list comes from Content-diffusion. Its IAB-taxonomy-based trend-graph tagging was not ported.
