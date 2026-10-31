"""Command line: viralsim analyze | ab | backtest | serve"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .creator import Creator
from .llm import get_client
from .trends import TrendSnapshot


def _load(args):
    creator = Creator.from_dict(json.load(open(args.creator))) if getattr(args, "creator", None) else Creator()
    trend = TrendSnapshot.load(args.trend) if getattr(args, "trend", None) else None
    llm = get_client(args.llm) if args.llm != "none" else None
    return creator, trend, llm


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="viralsim", description="Predict how content spreads before you publish.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("analyze", "ab"):
        p = sub.add_parser(name)
        p.add_argument("--creator"), p.add_argument("--trend")
        p.add_argument("--llm", default="none", choices=["none", "mock", "openai"], help="'openai' = any OpenAI-compatible endpoint (env VIRALSIM_LLM_*)")
        p.add_argument("--runs", type=int, default=2000)
        p.add_argument("--platform", default="generic")
        p.add_argument("--json", action="store_true")
        if name == "analyze":
            p.add_argument("text", help="post text, or @file.txt")
            p.add_argument("--network", action="store_true"), p.add_argument("--no-agents", action="store_true")
        else:
            p.add_argument("a"), p.add_argument("b")
    b = sub.add_parser("backtest")
    b.add_argument("--runs", type=int, default=800)
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1"), s.add_argument("--port", type=int, default=8000)
    a = ap.parse_args(argv)
    read = lambda t: open(t[1:], encoding="utf-8").read() if t.startswith("@") else t
    if a.cmd == "analyze":
        from .pipeline import analyze
        from .report import to_markdown
        creator, trend, llm = _load(a)
        r = analyze(read(a.text), creator=creator, trend=trend, llm=llm, platform=a.platform, runs=a.runs,
                    with_agents=not a.no_agents, with_network=a.network)
        print(json.dumps(r, indent=2, default=float) if a.json else to_markdown(r))
    elif a.cmd == "ab":
        from .ab import ab_simulated
        from .dimensions import HeuristicScorer, LLMScorer
        from .pipeline import default_pool
        from .sim.wave import SimConfig
        creator, trend, llm = _load(a)
        sc = LLMScorer(llm) if llm else HeuristicScorer()
        r = ab_simulated(default_pool(), sc.score(read(a.a)), sc.score(read(a.b)), creator, trend, SimConfig(runs=a.runs))
        print(json.dumps(r, indent=2) if a.json else
              f"Winner: {r['winner']}  P(B beats A)={r['p_b_beats_a']:.1%}  mean lift B-A={r['mean_lift_b_vs_a']:+,.0f} "
              f"(95% CI {r['lift_ci95'][0]:+,.0f}..{r['lift_ci95'][1]:+,.0f})  decisive={r['decisive']}\n"
              f"Viral probability A {r['viral_probability']['A']:.1%} / B {r['viral_probability']['B']:.1%}")
    elif a.cmd == "backtest":
        from .calibrate import backtest, baseline_always
        from .pipeline import analyze
        res = backtest(lambda c: analyze(c["content"], runs=a.runs, with_agents=False, with_levers=False)["viral_score"])
        base = backtest(baseline_always())
        keys = ("pearson", "mae", "directional_accuracy", "auc_success_vs_failure", "near_bucket")
        print("model   :", {k: round(res[k], 3) for k in keys}), print("const-50:", {k: round(base[k], 3) for k in keys})
    elif a.cmd == "serve":
        from .server import serve
        serve(a.host, a.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
