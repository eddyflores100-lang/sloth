"""sloth.web — zero-dependency dashboard: show the latest signed receipt.

Endpoints:
  GET /                    latest receipt as a standalone HTML page
  GET /receipt/latest.json raw receipt (for `curl` + offline checking)
  GET /verify              re-walks the chain and checks the Ed25519 signature
  GET /healthz             k8s-flavoured liveness

Run: python web/app.py  (env PORT respected; defaults to 8080)
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sloth.report import latest_receipt, render_html  # noqa: E402
from sloth.receipts import verify  # noqa: E402

RECEIPTS_DIR = os.environ.get(
    "SLOTH_RECEIPTS", os.path.join(os.path.dirname(__file__), "..", "receipts"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/healthz":
            return self._send(200, "ok", "text/plain")
        if path == "/receipt/latest.json":
            rpath = latest_receipt(RECEIPTS_DIR)
            if not rpath:
                return self._send(404, '{"error": "no receipts yet"}', "application/json")
            return self._send(200, open(rpath, encoding="utf-8").read(), "application/json")
        if path == "/verify":
            rpath = latest_receipt(RECEIPTS_DIR)
            if not rpath:
                return self._send(404, '{"verified": false, "reason": "no receipts"}',
                                  "application/json")
            ok, problems = verify(rpath)
            return self._send(200, json.dumps({
                "verified": ok, "receipt": os.path.basename(rpath),
                "problems": problems}, indent=1), "application/json")

        rpath = latest_receipt(RECEIPTS_DIR)
        if not rpath:
            return self._send(200, """<!doctype html><meta charset=utf-8>
<title>SLOTH</title><body style='background:#0d1117;color:#e6edf3;font-family:monospace;
max-width:700px;margin:80px auto'><h1>&#129425; SLOTH is asleep.</h1>
<p>No receipts yet. The sloth works at night; check back after breakfast.</p></body>""")
        return self._send(200, render_html(rpath))

    def log_message(self, *a):  # quiet
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"sloth dashboard on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
