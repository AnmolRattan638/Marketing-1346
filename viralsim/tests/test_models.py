import json
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np

from viralsim import ab, calibrate, metrics, optimize, risk
from viralsim.agents import run_hybrid
from viralsim.llm import MockLLM, OpenAICompatClient, extract_json
from viralsim.sim.hawkes import HawkesParams, fit_hawkes, forecast_remaining, simulate_hawkes
from viralsim.sim.network import ModerationConfig, NetworkConfig, simulate_cascade
from viralsim.signals import analyze_text, predict_signals
from tests.helpers import content, pool


class MetricsTests(unittest.TestCase):
    def test_structural_virality_known_trees(self):
        path = metrics.cascade_metrics({0: None, 1: 0, 2: 1}, {0: 0, 1: 1, 2: 2})
        self.assertAlmostEqual(path["structural_virality"], 4 / 3, places=4)
        star = metrics.cascade_metrics({0: None, 1: 0, 2: 0, 3: 0}, {0: 0, 1: 1, 2: 1, 3: 1})
        self.assertAlmostEqual(star["structural_virality"], 1.5, places=4)
        self.assertEqual(path["max_depth"], 2)
        self.assertGreater(path["structural_virality"], 0)

    def test_bimodality_and_polarization(self):
        bi = np.array([-1.0] * 50 + [1.0] * 50)
        uni = np.random.default_rng(0).normal(0, 0.1, 100)
        self.assertGreater(metrics.bimodality(bi), 0.555)
        self.assertLess(metrics.bimodality(uni), 0.555)
        self.assertGreater(metrics.polarization(bi), metrics.polarization(uni))


class HawkesTests(unittest.TestCase):
    def test_recovers_branching_ratio(self):
        p = HawkesParams(0.5, 0.6, 1.0)
        t = simulate_hawkes(p, 400, np.random.default_rng(3))
        f = fit_hawkes(t, 400)
        self.assertAlmostEqual(f.branching_ratio, 0.6, delta=0.15)
        self.assertGreater(forecast_remaining(t, 400, f), 0)

    def test_needs_events(self):
        with self.assertRaises(ValueError):
            fit_hawkes([1.0, 2.0], 10)


class NetworkTests(unittest.TestCase):
    def test_quality_drives_cascade_and_moderation_suppresses(self):
        mean = lambda q, **kw: np.mean([simulate_cascade(pool(), content(q), cfg=NetworkConfig(n_users=500, seed=s), **kw).metrics["size"] for s in range(5)])
        self.assertGreater(mean(9), mean(3))
        base = mean(8, is_misinfo=True)
        mod = mean(8, is_misinfo=True, moderation=ModerationConfig(detect_accuracy=1.0, suppression=0.9))
        self.assertLess(mod, base)

    def test_opinion_moves_towards_stance(self):
        r = simulate_cascade(pool(), content(9), cfg=NetworkConfig(n_users=500, seed=1), stance=0.8)
        self.assertGreater(r.opinions_after.mean(), r.opinions_before.mean())


class ABTests(unittest.TestCase):
    def test_z_test(self):
        r = ab.two_proportion_z(60, 100, 40, 100)
        self.assertAlmostEqual(r["z"], 2.8284, places=3)
        self.assertGreater(r["confidence"], 0.99)
        self.assertEqual(ab.two_proportion_z(0, 100, 0, 100)["confidence"], 0.5)
        self.assertEqual(ab.two_proportion_z(5, 0, 5, 10)["confidence"], 0.0)

    def test_compare_votes_tie(self):
        self.assertEqual(ab.compare_votes({"like": 5}, {"like": 5}, 10)["like"]["winner"], "tie")

    def test_simulated_ab_picks_stronger(self):
        r = ab.ab_simulated(pool(), content(3), content(8), cfg=__import__("viralsim.sim.wave", fromlist=["x"]).SimConfig(runs=200))
        self.assertEqual(r["winner"], "B")
        self.assertTrue(r["decisive"])


class SignalAndRiskTests(unittest.TestCase):
    def test_link_penalty_and_question_bonus(self):
        base = predict_signals(analyze_text("Here's what I learned shipping a product. What would you add?"))
        link = predict_signals(analyze_text("Here's what I learned shipping a product. What would you add? https://x.co/a"))
        self.assertGreater(base.score, link.score)
        noq = predict_signals(analyze_text("Here's what I learned shipping a product."))
        self.assertGreater(base.probs["reply"], noq.probs["reply"])

    def test_controversy_rules(self):
        r = risk.detect_controversy("Real men don't cry. No excuses!")
        self.assertTrue(r.has_controversy)
        self.assertLessEqual(r.score_penalty, 40)
        self.assertFalse(risk.detect_controversy("We launched a new feature today.").has_controversy)

    def test_llm_failure_falls_back_to_rules(self):
        bad = MockLLM(lambda s, u: "not json at all")
        self.assertEqual(risk.detect_controversy("hello", bad).source, "rules")


class LLMTests(unittest.TestCase):
    def test_extract_json(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('Sure! {"a": [1,2]} hope that helps'), {"a": [1, 2]})
        self.assertEqual(extract_json("<think>hmm</think>{\"k\": true}"), {"k": True})
        with self.assertRaises(ValueError):
            extract_json("nothing here")

    def test_openai_compat_client_against_local_server(self):
        seen = {}

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                seen["path"], seen["auth"] = self.path, self.headers.get("Authorization")
                seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                out = json.dumps({"choices": [{"message": {"content": '{"ok": true}'}}]}).encode()
                self.send_response(200), self.send_header("Content-Length", str(len(out))), self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            c = OpenAICompatClient(f"http://127.0.0.1:{srv.server_port}/v1", "k", "m")
            self.assertEqual(extract_json(c.complete("s", "u", json_mode=True)), {"ok": True})
        finally:
            srv.shutdown()
        self.assertEqual(seen["path"], "/v1/chat/completions")
        self.assertEqual(seen["auth"], "Bearer k")
        self.assertEqual(seen["body"]["response_format"], {"type": "json_object"})


class AgentTests(unittest.TestCase):
    def test_deterministic_and_quality_sensitive(self):
        a = run_hybrid(content(8), pool(), n_core=4, n_ordinary=300, rounds=4, seed=3)
        b = run_hybrid(content(8), pool(), n_core=4, n_ordinary=300, rounds=4, seed=3)
        self.assertEqual(a.totals, b.totals)
        weak = run_hybrid(content(1), pool(), n_core=4, n_ordinary=300, rounds=4, seed=3)
        self.assertGreater(a.engagement_rate, weak.engagement_rate)

    def test_llm_errors_do_not_crash(self):
        r = run_hybrid(content(8), pool(), llm=MockLLM(lambda s, u: "garbage"), n_core=4, n_ordinary=100, rounds=3, seed=1)
        self.assertGreaterEqual(len(r.actions), 1)


class OptimizeCalibrateTests(unittest.TestCase):
    def test_levers_are_ranked_and_paired(self):
        r = optimize.analyse(pool(), content(5), runs=200)
        lifts = [s["lift_pct"] for s in r["suggestions"]]
        self.assertEqual(lifts, sorted(lifts, reverse=True))
        self.assertTrue(all(l >= optimize.MIN_LIFT_PCT for l in lifts))
        self.assertLessEqual(len(lifts), optimize.MAX_SUGGESTIONS)

    def test_metrics(self):
        self.assertEqual(calibrate.auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]), 1.0)
        self.assertEqual(calibrate.auc([0.5, 0.5], [0, 1]), 0.5)
        self.assertAlmostEqual(calibrate.ece([0.9] * 10, [1] * 9 + [0]), 0.0, places=6)
        self.assertGreater(calibrate.brier([1.0], [0.0]), 0.99)
        self.assertEqual(len(calibrate.load_campaigns()), 50)


if __name__ == "__main__":
    unittest.main()
