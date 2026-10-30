from __future__ import annotations

import json
import random
from pathlib import Path

from .manager import FleetManager
from .models import FaultKind, RobotStatus


def run_trial(missions: int, recovery: bool, seed: int = 2026) -> dict[str, int | float]:
    manager = FleetManager(robot_count=5, automatic_recovery=recovery)
    rng = random.Random(seed)
    submitted = 0
    faults = [FaultKind.NODE_CRASH, FaultKind.LOCALIZATION_DROP]
    faults_injected = 0
    while submitted < missions:
        for _ in range(min(10, missions - submitted)):
            submitted += 1
            manager.submit_mission(f"mission-{submitted:04d}", rng.choice([1_250, 1_500, 1_750, 2_000]))
        for step in range(12):
            manager.tick(250)
            if faults_injected < len(faults) and submitted >= (faults_injected + 1) * 100 and step == 2:
                busy = [r for r in manager.robots.values() if r.status == RobotStatus.BUSY]
                if busy:
                    manager.inject_fault(busy[0].robot_id, faults[faults_injected])
                    faults_injected += 1
    manager.run_until_idle(max_ms=600_000)
    result = manager.summary()
    result["duration_ms"] = manager.now_ms
    result["throughput_missions_per_minute"] = round(60_000 * result["missions_completed"] / manager.now_ms, 2)
    result["recovery_enabled"] = int(recovery)
    return result


def run_comparison(output: str | Path = "results/recovery_comparison.json") -> dict[str, object]:
    baseline = run_trial(500, recovery=False)
    recovered = run_trial(500, recovery=True)
    comparison = {
        "workload": {"missions": 500, "robots": 5, "faults": 2, "seed": 2026},
        "recovery_disabled": baseline,
        "recovery_enabled": recovered,
        "change": {
            "availability_percentage_points": round(recovered["fleet_availability_pct"] - baseline["fleet_availability_pct"], 2),
            "throughput_pct": round(
                100
                * (recovered["throughput_missions_per_minute"] - baseline["throughput_missions_per_minute"])
                / baseline["throughput_missions_per_minute"],
                2,
            ),
            "duration_reduction_pct": round(100 * (baseline["duration_ms"] - recovered["duration_ms"]) / baseline["duration_ms"], 2),
        },
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    return comparison


if __name__ == "__main__":
    print(json.dumps(run_comparison(), indent=2))
