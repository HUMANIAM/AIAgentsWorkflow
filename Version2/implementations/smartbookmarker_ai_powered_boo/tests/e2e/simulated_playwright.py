#!/usr/bin/env python3
import sys
import threading
from urllib import request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.server import create_server  # noqa: E402


def main() -> int:
    server = create_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        payload = b'{"text":"Playwright simulation note for SmartBookmarker","category":"research"}'
        req = request.Request(
            f"http://{host}:{port}/api/save",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
        if '"ok": true' not in body:
            return 1

        with request.urlopen(f"http://{host}:{port}/api/notes?category=research", timeout=10) as response:
            notes_body = response.read().decode("utf-8")
        if "Playwright simulation note for SmartBookmarker" not in notes_body:
            return 1

        tab_file = ROOT / "backend" / "data" / "mock_sheet" / "research.md"
        if not tab_file.exists():
            return 1
        content = tab_file.read_text(encoding="utf-8")
        if "-----" not in content or "# " not in content:
            return 1
        return 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
