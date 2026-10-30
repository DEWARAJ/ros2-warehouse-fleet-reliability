from __future__ import annotations

from collections import deque
from statistics import median

from .models import FaultKind, Incident, Mission, MissionStatus, Robot, RobotStatus
from .store import EventStore


FAULT_RECOVERY_MS: dict[FaultKind, int] = {
    FaultKind.NODE_CRASH: 4_000,
    FaultKind.STALE_HEARTBEAT: 3_000,
    FaultKind.STALE_ODOMETRY: 2_500,
    FaultKind.SENSOR_TIMEOUT: 2_000,
    FaultKind.LOCALIZATION_DROP: 3_500,
    FaultKind.NETWORK_DELAY: 1_500,
    FaultKind.LOW_BATTERY: 5_000,
    FaultKind.OBSTACLE_TIMEOUT: 2_500,
}


class FleetManager:
    """Deterministic controller for mission assignment, quarantine, and recovery."""

    def __init__(
        self,
        robot_count: int = 5,
        store: EventStore | None = None,
        automatic_recovery: bool = True,
    ) -> None:
        if robot_count < 1:
            raise ValueError("robot_count must be positive")
        self.now_ms = 0
        self.robots = {f"robot-{i + 1:02d}": Robot(f"robot-{i + 1:02d}") for i in range(robot_count)}
        self.missions: dict[str, Mission] = {}
        self.queue: deque[str] = deque()
        self.incidents: dict[str, Incident] = {}
        self.store = store or EventStore()
        self.automatic_recovery = automatic_recovery
        self._incident_counter = 0
        self._faults_injected = 0
        self._faults_recovered = 0
        self._availability_sum = 0.0
        self._availability_samples = 0
        self.audit_log: list[dict[str, object]] = []
        self.store.snapshot(self.now_ms, self.robots.values())

    def submit_mission(self, mission_id: str, duration_ms: int = 2_000) -> Mission:
        if mission_id in self.missions:
            raise ValueError(f"duplicate mission: {mission_id}")
        if duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        mission = Mission(mission_id=mission_id, created_ms=self.now_ms, duration_ms=duration_ms)
        self.missions[mission_id] = mission
        self.queue.append(mission_id)
        self.store.save_mission(mission)
        return mission

    def inject_fault(self, robot_id: str, fault: FaultKind) -> Incident:
        robot = self.robots[robot_id]
        if robot.status in {RobotStatus.QUARANTINED, RobotStatus.RECOVERING}:
            raise ValueError(f"{robot_id} already unavailable")
        self._faults_injected += 1
        self._incident_counter += 1
        mission_id = robot.mission_id
        incident = Incident(
            incident_id=f"incident-{self._incident_counter:04d}",
            robot_id=robot_id,
            fault=fault,
            detected_ms=self.now_ms,
            mission_id=mission_id,
            details={"battery_pct": round(robot.battery_pct, 2)},
        )
        self.incidents[incident.incident_id] = incident
        robot.status = RobotStatus.QUARANTINED
        robot.fault = fault
        robot.recover_at_ms = self.now_ms + FAULT_RECOVERY_MS[fault] if self.automatic_recovery else None
        if mission_id is not None:
            mission = self.missions[mission_id]
            robot.failed_missions += 1
            robot.mission_id = None
            mission.robot_id = None
            if mission.attempts < mission.max_attempts:
                mission.status = MissionStatus.RETRYING
                self.queue.appendleft(mission_id)
            else:
                mission.status = MissionStatus.FAILED
                mission.completed_ms = self.now_ms
            self.store.save_mission(mission)
        self.store.save_incident(incident)
        return incident

    def operator_inject_fault(self, robot_id: str, fault: FaultKind, actor: str = "operator") -> Incident:
        incident = self.inject_fault(robot_id, fault)
        self._audit(actor, "inject_fault", robot_id, {"fault": fault.value, "incident_id": incident.incident_id})
        return incident

    def force_recover(self, robot_id: str, actor: str = "operator") -> None:
        robot = self.robots[robot_id]
        if robot.status not in {RobotStatus.QUARANTINED, RobotStatus.RECOVERING}:
            raise ValueError(f"{robot_id} is not quarantined")
        robot.status = RobotStatus.RECOVERING
        robot.recover_at_ms = self.now_ms
        self._audit(actor, "force_recover", robot_id, {"fault": robot.fault.value if robot.fault else "unknown"})
        self._recover_robots(force=True)

    def _audit(self, actor: str, action: str, target: str, details: dict[str, object]) -> None:
        record = {"timestamp_ms": self.now_ms, "actor": actor, "action": action, "target": target, "details": details}
        self.audit_log.append(record)
        self.store.save_audit(self.now_ms, actor, action, target, details)

    def tick(self, step_ms: int = 250) -> None:
        if step_ms <= 0:
            raise ValueError("step_ms must be positive")
        self.now_ms += step_ms
        self._recover_robots()
        self._complete_missions()
        self._assign_missions()
        for robot in self.robots.values():
            if robot.status in {RobotStatus.HEALTHY, RobotStatus.BUSY}:
                robot.last_heartbeat_ms = self.now_ms
                robot.last_odometry_ms = self.now_ms
                robot.battery_pct = max(5.0, robot.battery_pct - (0.04 if robot.status == RobotStatus.BUSY else 0.005))
        available = sum(r.status in {RobotStatus.HEALTHY, RobotStatus.BUSY} for r in self.robots.values())
        self._availability_sum += available / len(self.robots)
        self._availability_samples += 1
        self.store.snapshot(self.now_ms, self.robots.values())

    def run_until_idle(self, max_ms: int = 120_000, step_ms: int = 250) -> None:
        deadline = self.now_ms + max_ms
        while self.now_ms < deadline:
            self.tick(step_ms)
            active = any(m.status in {MissionStatus.QUEUED, MissionStatus.RETRYING, MissionStatus.RUNNING} for m in self.missions.values())
            recovering = self.automatic_recovery and any(
                r.status in {RobotStatus.QUARANTINED, RobotStatus.RECOVERING} for r in self.robots.values()
            )
            if not active and not recovering:
                return
        raise TimeoutError("fleet did not become idle")

    def _assign_missions(self) -> None:
        available = sorted(
            (r for r in self.robots.values() if r.status == RobotStatus.HEALTHY and r.battery_pct > 15.0),
            key=lambda r: (r.completed_missions, -r.battery_pct, r.robot_id),
        )
        while self.queue and available:
            mission = self.missions[self.queue.popleft()]
            if mission.status == MissionStatus.FAILED:
                continue
            robot = available.pop(0)
            mission.status = MissionStatus.RUNNING
            mission.robot_id = robot.robot_id
            mission.started_ms = self.now_ms
            mission.attempts += 1
            robot.status = RobotStatus.BUSY
            robot.mission_id = mission.mission_id
            self.store.save_mission(mission)

    def _complete_missions(self) -> None:
        for mission in self.missions.values():
            if mission.status != MissionStatus.RUNNING or mission.started_ms is None:
                continue
            if self.now_ms - mission.started_ms < mission.duration_ms:
                continue
            robot = self.robots[mission.robot_id]  # type: ignore[index]
            mission.status = MissionStatus.COMPLETED
            mission.completed_ms = self.now_ms
            robot.completed_missions += 1
            robot.status = RobotStatus.HEALTHY
            robot.mission_id = None
            self.store.save_mission(mission)

    def _recover_robots(self, force: bool = False) -> None:
        if not self.automatic_recovery and not force:
            return
        for robot in self.robots.values():
            if robot.recover_at_ms is None or self.now_ms < robot.recover_at_ms:
                continue
            if robot.status == RobotStatus.QUARANTINED:
                robot.status = RobotStatus.RECOVERING
                robot.recover_at_ms = self.now_ms + 500
                continue
            robot.status = RobotStatus.HEALTHY
            robot.battery_pct = max(robot.battery_pct, 60.0) if robot.fault == FaultKind.LOW_BATTERY else robot.battery_pct
            robot.recover_at_ms = None
            matching = [i for i in self.incidents.values() if i.robot_id == robot.robot_id and i.resolved_ms is None]
            for incident in matching:
                incident.resolved_ms = self.now_ms
                incident.details["re_registered"] = 1
                self.store.save_incident(incident)
                self._faults_recovered += 1
            robot.fault = None

    def summary(self) -> dict[str, int | float]:
        completed = [m for m in self.missions.values() if m.status == MissionStatus.COMPLETED]
        failed = [m for m in self.missions.values() if m.status == MissionStatus.FAILED]
        latencies = [m.completed_ms - m.created_ms for m in completed if m.completed_ms is not None]
        recoveries = [i.recovery_ms for i in self.incidents.values() if i.recovery_ms is not None]
        total = len(self.missions)
        return {
            "robots": len(self.robots),
            "missions_total": total,
            "missions_completed": len(completed),
            "missions_failed": len(failed),
            "mission_completion_pct": round(100 * len(completed) / total, 2) if total else 0.0,
            "faults_injected": self._faults_injected,
            "faults_recovered": self._faults_recovered,
            "automatic_recovery_pct": round(100 * self._faults_recovered / self._faults_injected, 2) if self._faults_injected else 0.0,
            "median_mission_latency_ms": int(median(latencies)) if latencies else 0,
            "mean_time_to_recovery_ms": round(sum(recoveries) / len(recoveries), 2) if recoveries else 0.0,
            "fleet_availability_pct": round(100 * self._availability_sum / self._availability_samples, 2)
            if self._availability_samples
            else 100.0,
        }
