import json
import threading
import unittest
import urllib.error
import urllib.request

from viralsim.cli import main
from viralsim.pipeline import analyze, viral_score
from viralsim.report import to_markdown
from viralsim.server import handle, make_server
from tests.helpers import pool


class PipelineTests(unittest.TestCase):
    def test_analyze_end_to_end(self):
        r = analyze("5 ways to learn Python fast. What do you think? #coding", pool=pool(), runs=200, with_network=True)
        self.assertTrue(0 <= r["viral_score"] <= 100)
        for k in ("forecast", "signals", "risk", "agents", "network", "suggestions", "caveats"):
            self.assertIn(k, r)
        self.assertIn("# Viral forecast", to_markdown(r))
        json.dumps(r, default=float)

    def test_penalty_lowers_score(self):
        self.assertGreater(viral_score(0.3, 0.1, 50, 0), viral_score(0.3, 0.1, 50, 30))

    def test_score_monotonic_in_breakout(self):
        self.assertGreater(viral_score(0.5, 0.1, None, 0), viral_score(0.05, 0.1, None, 0))


class ServerTests(unittest.TestCase):
    def test_handle_validation(self):
        self.assertEqual(handle("POST", "/api/analyze", {})[0], 400)
        self.assertEqual(handle("POST", "/api/ab", {"a": "x"})[0], 400)
        self.assertEqual(handle("GET", "/nope", None)[0], 404)

    def test_http_round_trip(self):
        srv = make_server("127.0.0.1", 0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_port}"
        try:
            with urllib.request.urlopen(base + "/api/health") as r:
                self.assertEqual(json.load(r)["status"], "ok")
            req = urllib.request.Request(base + "/api/analyze", json.dumps({"text": "hello there friends", "runs": 100}).encode(),
                                         {"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as r:
                self.assertIn("viral_score", json.load(r))
            bad = urllib.request.Request(base + "/api/analyze", b"{not json", {"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(bad)
            cm.exception.close()
            self.assertEqual(cm.exception.code, 400)
            with urllib.request.urlopen(base + "/") as r:
                self.assertIn(b"ViralSim", r.read())
        finally:
            srv.shutdown()


class CLITests(unittest.TestCase):
    def test_version(self):
        with self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
