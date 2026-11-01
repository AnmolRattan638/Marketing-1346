"""Zero-dependency HTTP API + single-page UI (stdlib http.server).
POST /api/analyze {text, creator?, trend?, runs?, platform?, ...}   POST /api/ab {a, b, runs?}
GET /api/health   GET /  (web UI)"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .creator import Creator
from .trends import TrendSnapshot

WEB = os.path.join(os.path.dirname(__file__), "web", "index.html")
MAX_BODY = 1_000_000


def handle(method: str, path: str, body: dict | None) -> tuple[int, dict | str, str]:
    from .pipeline import analyze, default_pool
    if method == "GET" and path == "/api/health":
        return 200, {"status": "ok", "pool": len(default_pool())}, "application/json"
    if method == "POST" and path == "/api/analyze":
        b = body or {}
        if not isinstance(b.get("text"), str) or not b["text"].strip():
            return 400, {"error": "'text' is required"}, "application/json"
        r = analyze(b["text"], creator=Creator.from_dict(b["creator"]) if b.get("creator") else None,
                    trend=TrendSnapshot.from_dict(b["trend"]) if b.get("trend") else None,
                    platform=b.get("platform", "generic"), has_video=bool(b.get("has_video")), has_image=bool(b.get("has_image")),
                    is_thread=bool(b.get("is_thread")), thread_length=int(b.get("thread_length", 1)),
                    runs=max(100, min(int(b.get("runs", 1500)), 5000)), with_network=bool(b.get("network")))
        return 200, r, "application/json"
    if method == "POST" and path == "/api/ab":
        from .ab import ab_simulated
        from .dimensions import HeuristicScorer
        b = body or {}
        if not (isinstance(b.get("a"), str) and isinstance(b.get("b"), str)):
            return 400, {"error": "'a' and 'b' are required strings"}, "application/json"
        from .sim.wave import SimConfig
        s = HeuristicScorer()
        return 200, ab_simulated(default_pool(), s.score(b["a"]), s.score(b["b"]),
                                 Creator.from_dict(b["creator"]) if b.get("creator") else None, None,
                                 SimConfig(runs=max(100, min(int(b.get("runs", 800)), 3000)))), "application/json"
    if method == "GET" and path in ("/", "/index.html"):
        with open(WEB, encoding="utf-8") as f:
            return 200, f.read(), "text/html; charset=utf-8"
    return 404, {"error": "not found"}, "application/json"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, ctype):
        data = (payload if isinstance(payload, str) else json.dumps(payload, default=float)).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _run(self, method):
        body = None
        if method == "POST":
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._send(413, {"error": "body too large"}, "application/json")
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"error": "invalid JSON"}, "application/json")
        try:
            self._send(*handle(method, self.path.split("?")[0], body))
        except (ValueError, TypeError) as e:
            self._send(400, {"error": str(e)}, "application/json")

    do_GET = lambda self: self._run("GET")
    do_POST = lambda self: self._run("POST")

    def log_message(self, *a):
        pass


def make_server(host="127.0.0.1", port=8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def serve(host="127.0.0.1", port=8000):
    srv = make_server(host, port)
    print(f"ViralSim on http://{host}:{port}")
    srv.serve_forever()
