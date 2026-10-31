import unittest

import numpy as np

from tests.helpers import content, pool


class MLTests(unittest.TestCase):
    def test_early_predictor_beats_chance(self):
        try:
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("scikit-learn not installed")
        from viralsim.ml import build_dataset, train_early_predictor
        contents = [content(q) for q in (2, 3, 4, 5, 6, 7, 8, 9)]
        X, final = build_dataset(pool(), contents, n_per_content=6, n_users=400)
        self.assertEqual(X.shape[0], len(final))
        clf, rep = train_early_predictor(X, final)
        self.assertGreater(rep["test_auc"], 0.6)


if __name__ == "__main__":
    unittest.main()
