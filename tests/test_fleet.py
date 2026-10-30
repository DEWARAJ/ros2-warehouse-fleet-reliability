import unittest
from pathlib import Path
from uuid import uuid4

from warehouse_fleet.manager import FAULT_RECOVERY_MS, FleetManager
from warehouse_fleet.metrics import render_prometheus
from warehouse_fleet.models import FaultKind, MissionStatus, RobotStatus
from warehouse_fleet.scenario import run_benchmark
from warehouse_fleet.store import EventStore


class FleetManagerTests(unittest.TestCase):
    def test_assigns_and_completes_mission(self) -> None:
        manager = FleetManager(robot_count=2)
        manager.submit_mission("mission-1", 500)
        manager.run_until_idle()
        self.assertEqual(MissionStatus.COMPLETED, manager.missions["mission-1"].status)
        self.assertEqual(1, manager.summary()["missions_completed"])

    def test_rejects_duplicate_mission_id(self) -> None:
        manager = FleetManager()
        manager.submit_mission("duplicate")
        with self.assertRaises(ValueError):
            manager.submit_mission("duplicate")

    def test_fault_quarantines_robot_and_reassigns_mission(self) -> None:
        manager = FleetManager(robot_count=2)
        manager.submit_mission("mission-1", 2_000)
        manager.tick()
        first_robot = manager.missions["mission-1"].robot_id
        self.assertIsNotNone(first_robot)
        manager.inject_fault(first_robot, FaultKind.NODE_CRASH)  # type: ignore[arg-type]
        self.assertEqual(RobotStatus.QUARANTINED, manager.robots[first_robot].status)  # type: ignore[index]
        manager.tick()
        self.assertNotEqual(first_robot, manager.missions["mission-1"].robot_id)
        manager.run_until_idle()
        self.assertEqual(MissionStatus.COMPLETED, manager.missions["mission-1"].status)

    def test_incident_records_recovery_time(self) -> None:
        manager = FleetManager(robot_count=1)
        incident = manager.inject_fault("robot-01", FaultKind.SENSOR_TIMEOUT)
        expected = FAULT_RECOVERY_MS[FaultKind.SENSOR_TIMEOUT] + 500
        for _ in range(expected // 250):
            manager.tick(250)
        self.assertEqual(expected, incident.recovery_ms)
        self.assertEqual(RobotStatus.HEALTHY, manager.robots["robot-01"].status)

    def test_low_battery_recovery_recharges_robot(self) -> None:
        manager = FleetManager(robot_count=1)
        manager.robots["robot-01"].battery_pct = 8.0
        manager.inject_fault("robot-01", FaultKind.LOW_BATTERY)
        manager.run_until_idle()
        self.assertGreaterEqual(manager.robots["robot-01"].battery_pct, 59.9)

    def test_prometheus_output_has_per_robot_metrics(self) -> None:
        manager = FleetManager(robot_count=2)
        metrics = render_prometheus(manager)
        self.assertIn('warehouse_robot_available{robot_id="robot-01"}', metrics)
        self.assertIn("warehouse_fleet_missions_total", metrics)

    def test_store_supports_operational_query(self) -> None:
        store = EventStore()
        manager = FleetManager(robot_count=1, store=store)
        manager.submit_mission("mission-1", 500)
        manager.run_until_idle()
        rows = store.query("SELECT COUNT(*) AS completed FROM missions WHERE status = 'completed'")
        self.assertEqual(1, rows[0]["completed"])

    def test_deterministic_benchmark_writes_evidence(self) -> None:
        directory = Path("results") / f"test-{uuid4().hex}"
        try:
            first = run_benchmark(40, 3, 7, directory)
            self.assertEqual(40, first["missions_completed"])
            self.assertTrue((directory / "benchmark_summary.json").exists())
            self.assertTrue((directory / "fleet_evidence.db").exists())
            second = run_benchmark(40, 3, 7, directory)
            self.assertEqual(first, second)
        finally:
            for child in directory.glob("*"):
                child.unlink(missing_ok=True)
            directory.rmdir()


if __name__ == "__main__":
    unittest.main()
