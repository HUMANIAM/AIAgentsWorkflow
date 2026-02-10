#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from backend.app import ingest_selection, retrieve_notes


class SmartBookmarkerHandler(BaseHTTPRequestHandler):
    server_version = "SmartBookmarkerHTTP/0.2"

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json({"ok": True, "service": "smartbookmarker"})
            return
        if parsed.path == "/api/notes":
            params = parse_qs(parsed.query)
            category = params.get("category", [None])[0]
            self._send_json({"notes": retrieve_notes(category=category)})
            return
        self._send_json({"error": "not_found"}, status=404)

    def do_POST(self):
        if self.path != "/api/save":
            self._send_json({"error": "not_found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "invalid_json"}, status=400)
            return

        text = str(payload.get("text", "")).strip()
        if not text:
            self._send_json({"error": "text_required"}, status=400)
            return

        category = payload.get("category")
        note = ingest_selection(text, category_override=category)
        self._send_json({"ok": True, "note": note})


def create_server(host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), SmartBookmarkerHandler)


def main() -> int:
    host = os.getenv("SMARTBOOKMARKER_HOST", "127.0.0.1")
    port = int(os.getenv("SMARTBOOKMARKER_PORT", "8787"))
    server = create_server(host=host, port=port)
    print(f"SmartBookmarker server listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
