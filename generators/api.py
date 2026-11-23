"""HTTP wrapper for the questions service (standard library only).

    GENERATORS_SECRET=... GENERATORS_API_KEY=... python3 -m generators.api --port 8787

Endpoints (JSON; every request needs the header X-Generators-Key):
    GET  /health
    GET  /generators                 catalog: ids, formats, settings, presets
    POST /preview   {generator_id, difficulty, settings, format, seed}   sample WITH answer (instructors)
    POST /question  {generator_id, version, difficulty, settings, formats, format}   question + token (students)
    POST /check     {token, response | step_responses}                   mark, explain, diagnose

Only app servers should hold the key; browsers talk to their own app, never to this service.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from . import service

MAX_BODY = 64 * 1024
ROUTES = {
    ("GET", "/health"): lambda body: {"ok": True},
    ("GET", "/generators"): lambda body: service.catalog(),
    ("POST", "/preview"): lambda body: service.preview(**_pick(body, "generator_id", "difficulty", "settings", "format", "seed")),
    ("POST", "/question"): lambda body: service.new_question(
        **_pick(body, "generator_id", "version", "difficulty", "settings", "formats", "format")),
    ("POST", "/check"): lambda body: service.check(**_pick(body, "token", "response", "step_responses")),
}


def request_path(raw: str) -> str:
    """The route asked for. Behind Vercel's rewrite it arrives as ?route=/generators."""
    path, _, query = raw.partition("?")
    route = parse_qs(query).get("route", [None])[0]
    return (route or path).rstrip("/") or "/"


def _pick(body: dict, *keys: str) -> dict:
    return {k: body[k] for k in keys if k in body and body[k] is not None}


class Handler(BaseHTTPRequestHandler):
    server_version = "KGGenerators/1"

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle(self, method: str) -> None:
        key = os.environ.get("GENERATORS_API_KEY", "")
        if not key or not hmac.compare_digest(self.headers.get("X-Generators-Key", ""), key):
            return self._send(401, {"error": "Missing or wrong service key."})
        route = ROUTES.get((method, request_path(self.path)))
        if route is None:
            return self._send(404, {"error": "Not found."})
        body = {}
        if method == "POST":
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"error": "Request too large."})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"error": "Invalid JSON."})
            if not isinstance(body, dict):
                return self._send(400, {"error": "Expected a JSON object."})
        try:
            self._send(200, route(body))
        except service.ServiceError as e:
            self._send(e.status, {"error": str(e)})
        except TypeError:
            self._send(400, {"error": "Missing or unexpected fields."})
        except Exception:  # never leak internals
            self._send(500, {"error": "The question service failed. Try again."})

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def log_message(self, fmt, *args) -> None:  # quiet: no request bodies in logs
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
