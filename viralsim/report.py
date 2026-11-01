"""Markdown report builder (deterministic; no LLM needed)."""
from __future__ import annotations


def _n(x: float) -> str:
    return f"{x:,.0f}"


def to_markdown(r: dict) -> str:
    f, rk = r["forecast"], r["risk"]
    L = [f"# Viral forecast: {r['viral_score']}/100", "",
         f"**Reach** p10 {_n(f['reach_p10'])} · p50 {_n(f['reach_p50'])} · p90 {_n(f['reach_p90'])} "
         f"(expected {_n(f['expected_reach'])} of a {_n(f['audience_pool'])}-viewer pool)  ",
         f"**Breakout probability** {f['viral_probability']:.1%} · **reliability heuristic** {f['confidence']:.0%} · "
         f"**trend alignment** {f['trend_alignment']:.2f}", "",
         "**Expected actions per run:** " + ", ".join(f"{k} {_n(v)}" for k, v in f["engagement"].items()), ""]
    c = r["content"]["dims"]
    L += ["## Content profile", ", ".join(f"{k} {v}" for k, v in c.items()) + f" (scored by {r['scorer']})", ""]
    L += [f"## Backlash risk: {rk['level']}"] + ([f"- {i['category']} ({i['severity']}): {i['description']}" for i in rk["issues"]] or ["- none detected"]) + [""]
    if "agents" in r:
        a = r["agents"]
        L += ["## Simulated crowd", f"Actions {a['totals']} · sentiment {a['sentiment']} · cascade size {a['cascade']['size']}, "
              f"depth {a['cascade']['max_depth']}, structural virality {a['cascade']['structural_virality']}"]
        L += ["- " + f"{role}: n={v['n']}, sentiment {v['avg_sentiment']:+.2f}, share rate {v['share_rate']:.0%}" for role, v in a["by_role"].items()] + [""]
    s = r.get("suggestions")
    if s:
        L += ["## What to change"]
        L += [f"- **{x['title']}** (+{x['lift_pct']}% expected reach): {x['hint']}" for x in s["counterfactual"]]
        L += [f"- {x['title']}: {x['description']}" for x in s["text_edits"][:4]] + [""]
    L += ["## Caveats"] + [f"- {c}" for c in r["caveats"]]
    return "\n".join(L)
