from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def make_handler(output: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            record = {
                "received_at": datetime.now(timezone.utc).isoformat(),
                "path": self.path,
                "payload": payload,
            }
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            body = json.dumps({"status": "ok", "output": str(output)}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Receive Alertmanager webhooks as JSONL evidence")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9119)
    parser.add_argument("--output", type=Path, default=Path("results/mock_pager_alerts.jsonl"))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.output))
    print(f"mock pager listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
