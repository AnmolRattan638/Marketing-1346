"""Counterfactual optimiser (Content-diffusion's Analyse Engine): change ONE thing about the post,
re-simulate with the SAME seed (paired comparison), and rank the changes by lift. Also turns text
signals into concrete edits and, with an LLM, drafts a rewrite that applies the top levers."""
from __future__ import annotations

import re

from .audience import AudiencePool
from .creator import Creator
from .llm import LLMClient
from .schema import DIM_IDX, TOPIC_IDX, Content, clamp
from .signals import analyze_text, predict_signals
from .trends import TrendSnapshot, tokenize
from .sim.wave import SimConfig, run_monte_carlo

DELTA, MIN_LIFT_PCT, MAX_SUGGESTIONS, BOOST_GATE, CONTROVERSY_DOWN_GATE = 2.0, 1.5, 4, 3.5, 5.0
GENERAL_DIMS = ["curiosity", "novelty", "relatability", "emotional_intensity"]
GATED_DIMS = ["humor", "educational", "practical_value"]
HINTS = {
    "dim:humor": ("Sharpen the humor", "land a harder punchline or funnier framing"),
    "dim:curiosity": ("Open a stronger curiosity gap", "tease the payoff up front without giving it away"),
    "dim:educational": ("Teach one concrete thing", "make the takeaway sharper and more useful"),
    "dim:novelty": ("Make it feel fresher", "a format, angle or detail viewers haven't seen"),
    "dim:controversy_up": ("Take a clearer stance", "a claim people can push back on drives comments"),
    "dim:controversy_down": ("Soften the divisive edge", "the friction is costing you reach"),
    "dim:emotional_intensity": ("Raise the emotional stakes", "a stronger high-arousal beat: awe, joy, tension"),
    "dim:relatability": ("Make it more 'that's so me'", "a detail a wide audience instantly recognises"),
    "dim:practical_value": ("Add something actionable", "a tip or takeaway worth acting on"),
    "composite:shareability": ("Give them a reason to share", "a hook or moment viewers want to send to a friend"),
    "composite:saveability": ("Add a save-worthy takeaway", "a tip, list or reference worth bookmarking"),
    "trend": ("Ride a trend that's peaking", "align with a topic the algorithm is boosting right now"),
}


def apply_op(c: Content, op: dict) -> None:
    if "dim" in op and op["dim"] in DIM_IDX:
        c.dims[op["dim"]] = clamp(c.dims.get(op["dim"], 0.0) + op.get("delta", 0.0), 0, 10)
    elif "composite" in op:
        c.ensure_composites()
        cur = getattr(c, op["composite"])
        setattr(c, op["composite"], clamp(cur + op.get("delta", 0.0), 0, 10))
    elif "topic" in op and op["topic"] in TOPIC_IDX:
        c.topics[op["topic"]] = op.get("set", 1.0)
    elif "add_entity" in op and op["add_entity"] not in c.entities:
        c.entities.append(op["add_entity"])
    elif "add_tag" in op and op["add_tag"] not in c.tags:
        c.tags.append(op["add_tag"])


def _trend_lever(c: Content, trend: TrendSnapshot) -> dict | None:
    theme = set()
    for t, v in c.topics.items():
        theme |= set(tokenize(t)) if v > 0 else set()
    for s in c.entities + c.tags:
        theme |= set(tokenize(s))
    have = {e.lower() for e in c.entities}
    best = None
    for e in trend.trending_entities:
        lab = e.get("label")
        if not lab or lab.lower() in have or not (theme & (set(tokenize(lab)) | set(tokenize(" ".join(e.get("tags", [])))))):
            continue
        if best is None or e.get("weight", 0) > best[1]:
            best = (lab, e.get("weight", 0))
    return {"label": "trend", "ops": [{"add_entity": best[0]}], "meta": {"entity": best[0]}} if best else None


def build_scenarios(c: Content, trend: TrendSnapshot) -> list[dict]:
    c.ensure_composites()
    sc = [{"label": f"dim:{d}", "ops": [{"dim": d, "delta": DELTA}]} for d in GENERAL_DIMS]
    sc.append({"label": "composite:shareability", "ops": [{"composite": "shareability", "delta": DELTA}]})
    for d in GATED_DIMS:
        if c.dims.get(d, 0) >= BOOST_GATE:
            sc.append({"label": f"dim:{d}", "ops": [{"dim": d, "delta": DELTA}]})
    ctr = c.dims.get("controversy", 0)
    if ctr >= BOOST_GATE:
        sc.append({"label": "dim:controversy_up", "ops": [{"dim": "controversy", "delta": DELTA}]})
    if ctr >= CONTROVERSY_DOWN_GATE:
        sc.append({"label": "dim:controversy_down", "ops": [{"dim": "controversy", "delta": -DELTA}]})
    if c.saveability >= BOOST_GATE:
        sc.append({"label": "composite:saveability", "ops": [{"composite": "saveability", "delta": DELTA}]})
    t = _trend_lever(c, trend)
    if t:
        sc.append(t)
    return sc


def analyse(pool: AudiencePool, content: Content, creator: Creator | None = None, trend: TrendSnapshot | None = None,
            runs: int = 1000, seed: int = 42) -> dict:
    trend, creator = trend or TrendSnapshot.neutral(), creator or Creator()
    cfg = SimConfig(runs=runs, base_seed=seed)
    ctl = run_monte_carlo(pool, content, creator, trend, cfg)
    out = []
    for sc in build_scenarios(content, trend):
        v = content.copy()
        for op in sc["ops"]:
            apply_op(v, op)
        r = run_monte_carlo(pool, v, creator, trend, cfg)
        lift = (r["expected_reach"] - ctl["expected_reach"]) / max(ctl["expected_reach"], 1.0) * 100
        title, why = HINTS.get(sc["label"], (sc["label"], ""))
        if sc["label"] == "trend":
            title = f"Ride a trend: {sc['meta']['entity']}"
        out.append({"lever": sc["label"], "title": title, "hint": why, "lift_pct": round(lift, 1),
                    "viral_probability_delta": round(r["viral_probability"] - ctl["viral_probability"], 4),
                    "expected_reach": r["expected_reach"]})
    ranked = sorted((o for o in out if o["lift_pct"] >= MIN_LIFT_PCT), key=lambda o: -o["lift_pct"])[:MAX_SUGGESTIONS]
    return {"baseline": {k: ctl[k] for k in ("expected_reach", "reach_p10", "reach_p50", "reach_p90", "viral_probability", "confidence")},
            "suggestions": ranked, "all_levers": out}


def text_edits(text: str, creator: Creator | None = None, **media) -> list[dict]:
    """Platform-signal edits from the text itself (link tax, hooks, questions, hashtags...)."""
    f = analyze_text(text, **media)
    return [i for i in predict_signals(f, creator).insights if i["type"] in ("negative", "warning", "neutral")]


def rewrite(llm: LLMClient, text: str, suggestions: list[dict], platform: str = "X", n: int = 3) -> list[str]:
    levers = "\n".join(f"- {s['title']}: {s['hint']}" for s in suggestions) or "- make it punchier"
    prompt = (f"Rewrite this {platform} post in {n} distinct variants that apply these levers while keeping the facts and the "
              f"author's voice. Do not add unverifiable claims.\nLevers:\n{levers}\nPost: '''{text}'''\nReturn one variant per line, no numbering.")
    raw = llm.complete("You are a sharp social-media copywriter.", prompt, temperature=0.9, max_tokens=500)
    return [re.sub(r"^[\-\d.\s]+", "", ln).strip() for ln in raw.splitlines() if ln.strip()][:n]
