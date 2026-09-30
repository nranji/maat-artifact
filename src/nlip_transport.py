"""NLIP over HTTP (ECMA-431).

POST a JSON NLIP message to /nlip. The endpoint replies with an NLIP message.
Gateways, the harmonizer, and the analyst-assistant each run as their own
process. ECMA-432 is the WebSocket binding; request/response covers the alert
and Q&A exchanges in this tree.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from nlip_soc import NLIPMessage

# localhost must bypass any SOCKS/HTTP proxy the environment sets
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

MAX_BODY_BYTES = 1_048_576  # 1 MiB cap on inbound NLIP messages (prototype safety)


def to_wire(msg) -> bytes:
    obj = asdict(msg) if isinstance(msg, NLIPMessage) else msg
    return json.dumps(obj, default=str).encode("utf-8")


def from_wire(b: bytes):
    d = json.loads(b.decode("utf-8"))
    if isinstance(d, dict) and "content" in d and "format" in d:
        try:
            return NLIPMessage(**d)
        except TypeError:
            return d
    return d


def make_server(port: int, handler, health=None):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def do_OPTIONS(self):  # CORS preflight
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self):  # health check (+ optional status payload)
            payload = health() if callable(health) else (health or {"ok": True})
            out = json.dumps(payload).encode()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            if n > MAX_BODY_BYTES:
                self.send_response(413)
                self._cors()
                self.end_headers()
                return
            body = self.rfile.read(n)
            try:
                resp = handler(from_wire(body))
                out, code = to_wire(resp), 200
            except Exception as e:  # noqa: BLE001
                out, code = json.dumps({"error": str(e)}).encode(), 500
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

    return ThreadingHTTPServer(("127.0.0.1", port), H)


def serve(port: int, handler, health=None):
    make_server(port, handler, health).serve_forever()


def send(url: str, msg, timeout: int = 60):
    req = urllib.request.Request(url, data=to_wire(msg),
                                 headers={"Content-Type": "application/json"})
    with _OPENER.open(req, timeout=timeout) as r:
        return from_wire(r.read())


def wait_ready(url: str, tries: int = 80) -> bool:
    import time
    base = url.rsplit("/", 1)[0] + "/health"
    for _ in range(tries):
        try:
            _OPENER.open(base, timeout=1)
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.1)
    return False
