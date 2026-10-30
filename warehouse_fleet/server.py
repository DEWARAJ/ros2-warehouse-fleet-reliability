from __future__ import annotations

import argparse
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .manager import FleetManager
from .metrics import render_prometheus
from .models import FaultKind


class LiveFleet:
    """Thread-safe live simulation used by the operations API and Prometheus."""

    def __init__(self, robot_count: int = 5, store: object | None = None) -> None:
        self.manager = FleetManager(robot_count=robot_count, store=store)  # type: ignore[arg-type]
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.mission_counter = 0
        self.thread = threading.Thread(target=self._run, name="fleet-simulator", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                active = sum(m.status.value in {"queued", "retrying", "running"} for m in self.manager.missions.values())
                while active < 10:
                    self.mission_counter += 1
                    self.manager.submit_mission(f"live-{self.mission_counter:06d}", 2_000)
                    active += 1
                self.manager.tick(250)
            self.stop_event.wait(0.25)

    def snapshot(self, collection: str) -> object:
        with self.lock:
            if collection == "summary":
                return self.manager.summary()
            if collection == "robots":
                return [
                    {
                        "robot_id": r.robot_id,
                        "status": r.status.value,
                        "battery_pct": round(r.battery_pct, 2),
                        "mission_id": r.mission_id,
                        "completed_missions": r.completed_missions,
                        "failed_missions": r.failed_missions,
                        "fault": r.fault.value if r.fault else None,
                    }
                    for r in self.manager.robots.values()
                ]
            if collection == "missions":
                return [
                    {
                        "mission_id": m.mission_id,
                        "status": m.status.value,
                        "robot_id": m.robot_id,
                        "attempts": m.attempts,
                    }
                    for m in list(self.manager.missions.values())[-100:]
                ]
            if collection == "incidents":
                return [
                    {
                        "incident_id": i.incident_id,
                        "robot_id": i.robot_id,
                        "mission_id": i.mission_id,
                        "fault": i.fault.value,
                        "detected_ms": i.detected_ms,
                        "resolved_ms": i.resolved_ms,
                        "recovery_ms": i.recovery_ms,
                    }
                    for i in self.manager.incidents.values()
                ]
            if collection == "audit":
                return self.manager.audit_log[-100:]
            raise KeyError(collection)


def make_handler(fleet: LiveFleet) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "WarehouseFleet/1.0"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = json.dumps(payload, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _body(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/health":
                self._json({"status": "ok"})
                return
            if path == "/metrics":
                with fleet.lock:
                    payload = render_prometheus(fleet.manager).encode()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if path.startswith("/api/"):
                try:
                    self._json(fleet.snapshot(path.removeprefix("/api/")))
                except KeyError:
                    self._json({"error": "unknown resource"}, HTTPStatus.NOT_FOUND)
                return
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                body = self._body()
                actor = str(body.get("actor", "operator"))
                if path == "/api/faults":
                    with fleet.lock:
                        incident = fleet.manager.operator_inject_fault(
                            str(body["robot_id"]), FaultKind(str(body["fault"])), actor
                        )
                    self._json({"incident_id": incident.incident_id}, HTTPStatus.CREATED)
                    return
                if path.startswith("/api/robots/") and path.endswith("/recover"):
                    robot_id = path.split("/")[3]
                    with fleet.lock:
                        fleet.manager.force_recover(robot_id, actor)
                    self._json({"robot_id": robot_id, "status": "healthy"})
                    return
                if path == "/api/missions":
                    with fleet.lock:
                        fleet.mission_counter += 1
                        mission_id = str(body.get("mission_id", f"operator-{fleet.mission_counter:06d}"))
                        fleet.manager.submit_mission(mission_id, int(body.get("duration_ms", 2_000)))
                        fleet.manager._audit(actor, "submit_mission", mission_id, {})
                    self._json({"mission_id": mission_id}, HTTPStatus.CREATED)
                    return
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve a live warehouse fleet API and Prometheus metrics")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9108)
    parser.add_argument("--robots", type=int, default=5)
    parser.add_argument("--postgres-dsn", default="")
    args = parser.parse_args()
    store = None
    if args.postgres_dsn:
        from .postgres_store import PostgresEventStore

        store = PostgresEventStore(args.postgres_dsn)
    fleet = LiveFleet(args.robots, store)
    fleet.start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(fleet))
    print(f"fleet API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        fleet.stop()


if __name__ == "__main__":
    main()
