import math
import unittest

import numpy as np

from viralsim.creator import Creator, compute_scores, consistency
from viralsim.schema import Content
from viralsim.sim.wave import SimConfig, _lognormal_mult, run_monte_carlo
from viralsim.trends import TrendSnapshot, jaccard, best_match_weight
from tests.helpers import content, pool


class TrendTests(unittest.TestCase):
    def test_jaccard(self):
        self.assertAlmostEqual(jaccard(["a", "b"], ["b", "c"]), 1 / 3)
        self.assertEqual(jaccard([], ["a"]), 0.0)

    def test_fuzzy_entity_match(self):
        self.assertEqual(best_match_weight("World Cup final", [("FIFA World Cup final", 0.9)]), 0.9)  # containment
        self.assertEqual(best_match_weight("cooking", [("World Cup", 0.9)]), 0.0)

    def test_alignment_bounds_and_weights(self):
        t = TrendSnapshot(topic_trends={"comedy": 1.0}, trending_entities=[{"label": "Big Event", "weight": 1.0}],
                          tag_trends={"bigevent": 1.0})
        c = Content(topics={"comedy": 1.0}, entities=["Big Event"], tags=["bigevent"])
        self.assertAlmostEqual(t.alignment(c), 1.0)
        self.assertAlmostEqual(t.alignment(Content(topics={"comedy": 1.0})), 0.6)
        self.assertEqual(TrendSnapshot.neutral().alignment(c), 0.0)


class CreatorTests(unittest.TestCase):
    def test_consistency(self):
        self.assertEqual(consistency([10, 10, 10]), 1.0)
        self.assertLess(consistency([1, 100, 1]), 0.1)

    def test_scores_in_range(self):
        s = compute_scores(instagram={"followers": 10000, "following": 500, "monthly_reach": 40000,
                                      "recent_posts": [{"like_count": 300, "comments_count": 20, "timestamp": "2026-01-01T00:00:00Z"},
                                                       {"like_count": 250, "comments_count": 10, "timestamp": "2026-01-15T00:00:00Z"}]})
        for v in s.values():
            self.assertTrue(0 <= v <= 100)
        self.assertGreater(s["audience_quality_score"], 0)

    def test_seed_is_soft_capped(self):
        mega = Creator(followers=1e9, monthly_reach=1e10, momentum=100, audience_quality=100)
        self.assertLessEqual(mega.mechanics(50000)["seed_size"], 0.10 * 50000)
        small = Creator(followers=100, monthly_reach=300).mechanics(50000)["seed_size"]
        self.assertLess(small, mega.mechanics(50000)["seed_size"])


class WaveTests(unittest.TestCase):
    def test_lognormal_has_mean_one(self):
        rng = np.random.default_rng(0)
        for sigma in (0.2, 0.6):
            self.assertAlmostEqual(np.mean([_lognormal_mult(rng, sigma) for _ in range(40000)]), 1.0, delta=0.03)

    def test_deterministic_for_fixed_seed(self):
        cfg = SimConfig(runs=200)
        a = run_monte_carlo(pool(), content(6), Creator(), cfg=cfg)
        b = run_monte_carlo(pool(), content(6), Creator(), cfg=cfg)
        self.assertEqual(a, b)

    def test_quality_and_creator_monotonic(self):
        cfg = SimConfig(runs=300)
        lo, hi = (run_monte_carlo(pool(), content(q), Creator(), cfg=cfg)["expected_reach"] for q in (3, 8))
        self.assertGreater(hi, lo)
        small = run_monte_carlo(pool(), content(6), Creator(followers=300, monthly_reach=900), cfg=cfg)["expected_reach"]
        big = run_monte_carlo(pool(), content(6), Creator(followers=300000, monthly_reach=2e6, trust=70), cfg=cfg)["expected_reach"]
        self.assertGreater(big, small)

    def test_output_invariants(self):
        r = run_monte_carlo(pool(), content(7), Creator(), cfg=SimConfig(runs=300))
        self.assertLessEqual(r["reach_p10"], r["reach_p50"])
        self.assertLessEqual(r["reach_p50"], r["reach_p90"])
        self.assertLessEqual(r["reach_p90"], r["audience_pool"])
        self.assertTrue(0 <= r["viral_probability"] <= 1 and 0 <= r["confidence"] <= 1)

    def test_trend_alignment_helps(self):
        cfg = SimConfig(runs=300)
        t = TrendSnapshot(topic_trends={"comedy": 1.0})
        a = run_monte_carlo(pool(), content(6), Creator(), TrendSnapshot.neutral(), cfg)["expected_reach"]
        b = run_monte_carlo(pool(), content(6), Creator(), t, cfg)["expected_reach"]
        self.assertGreater(b, a)


if __name__ == "__main__":
    unittest.main()
