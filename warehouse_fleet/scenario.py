from __future__ import annotations

import json
import random
from pathlib import Path

from .manager import FleetManager
from .metrics import render_prometheus
from .models import FaultKind, RobotStatus
from .store import EventStore


def run_benchmark(
    mission_count: int = 250,
    robot_count: int = 5,
    seed: int = 2026,
    output_dir: str | Path = "results",
) -> dict[str, int | float]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    db_path = output / "fleet_evidence.db"
    if db_path.exists():
        db_path.unlink()
    store = EventStore(db_path)
    manager = FleetManager(robot_count=robot_count, store=store)
    rng = random.Random(seed)
    faults = list(FaultKind)
    submitted = 0
    while submitted < mission_count:
        batch = min(robot_count * 2, mission_count - submitted)
        for _ in range(batch):
            submitted += 1
            manager.submit_mission(f"mission-{submitted:04d}", duration_ms=rng.choice([1_250, 1_500, 1_750, 2_000]))
        for step in range(12):
            manager.tick(250)
            busy = [r for r in manager.robots.values() if r.status == RobotStatus.BUSY]
            if busy and step == 2 and submitted % 20 == 0:
                manager.inject_fault(rng.choice(busy).robot_id, rng.choice(faults))
    manager.run_until_idle(max_ms=180_000)
    summary = manager.summary()
    summary.update({"seed": seed, "duration_ms": manager.now_ms})
    (output / "benchmark_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output / "fleet_metrics.prom").write_text(render_prometheus(manager), encoding="utf-8")
    store.close()
    return summary
