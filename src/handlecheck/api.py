"""Tiny dependency-free HTTP API:  GET /check?username=foo&platform=github&platform=x

Run with:  handlecheck-api --port 8000   (binds to localhost by default)
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .checkers import PLATFORMS, check_all


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        qs = parse_qs(url.query)
        if url.path == "/platforms":
            return self._send(200, sorted(PLATFORMS))
        if url.path != "/check":
            return self._send(404, {"error": "use /check?username=NAME or /platforms"})
        names = qs.get("username", [])
        platforms = qs.get("platform") or None
        bad = [p for p in platforms or [] if p not in PLATFORMS]
        if not names or len(names) > 20 or bad:
            return self._send(400, {"error": f"need 1-20 username params; unknown platforms: {bad}"})
        rows = []
        for n in names:
            rows += [{**asdict(r), "status": r.status.value} for r in check_all(n, platforms)]
        self._send(200, rows)

    def log_message(self, *args) -> None:  # keep stdout quiet
        pass


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="handlecheck-api")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)
    print(f"listening on http://{args.host}:{args.port}  (try /check?username=google)")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
