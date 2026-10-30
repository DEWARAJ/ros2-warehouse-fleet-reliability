from __future__ import annotations

from dataclasses import dataclass, field
try:
    from enum import StrEnum
except ImportError:  # Python 3.10, used by ROS 2 Humble on Ubuntu 22.04
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value


class RobotStatus(StrEnum):
    HEALTHY = "healthy"
    BUSY = "busy"
    DEGRADED = "degraded"
    QUARANTINED = "quarantined"
    RECOVERING = "recovering"


class MissionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    RETRYING = "retrying"
    FAILED = "failed"


class FaultKind(StrEnum):
    NODE_CRASH = "node_crash"
    STALE_HEARTBEAT = "stale_heartbeat"
    STALE_ODOMETRY = "stale_odometry"
    SENSOR_TIMEOUT = "sensor_timeout"
    LOCALIZATION_DROP = "localization_drop"
    NETWORK_DELAY = "network_delay"
    LOW_BATTERY = "low_battery"
    OBSTACLE_TIMEOUT = "obstacle_timeout"


@dataclass(slots=True)
class Robot:
    robot_id: str
    status: RobotStatus = RobotStatus.HEALTHY
    battery_pct: float = 100.0
    last_heartbeat_ms: int = 0
    last_odometry_ms: int = 0
    mission_id: str | None = None
    completed_missions: int = 0
    failed_missions: int = 0
    recover_at_ms: int | None = None
    fault: FaultKind | None = None


@dataclass(slots=True)
class Mission:
    mission_id: str
    created_ms: int
    duration_ms: int
    status: MissionStatus = MissionStatus.QUEUED
    robot_id: str | None = None
    started_ms: int | None = None
    completed_ms: int | None = None
    attempts: int = 0
    max_attempts: int = 3


@dataclass(slots=True)
class Incident:
    incident_id: str
    robot_id: str
    fault: FaultKind
    detected_ms: int
    resolved_ms: int | None = None
    mission_id: str | None = None
    action: str = "quarantine_and_reassign"
    details: dict[str, str | int | float] = field(default_factory=dict)

    @property
    def recovery_ms(self) -> int | None:
        if self.resolved_ms is None:
            return None
        return self.resolved_ms - self.detected_ms
