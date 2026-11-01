from __future__ import annotations

from .manager import FleetManager
from .models import RobotStatus


def render_prometheus(manager: FleetManager) -> str:
    summary = manager.summary()
    active_missions = sum(
        mission.status.value in {"queued", "retrying", "running"}
        for mission in manager.missions.values()
    )
    unresolved_incidents = sum(incident.resolved_ms is None for incident in manager.incidents.values())
    lines = [
        "# HELP warehouse_fleet_missions_total Total submitted missions.",
        "# TYPE warehouse_fleet_missions_total gauge",
        f"warehouse_fleet_missions_total {summary['missions_total']}",
        "# HELP warehouse_fleet_missions_completed_total Completed missions.",
        "# TYPE warehouse_fleet_missions_completed_total gauge",
        f"warehouse_fleet_missions_completed_total {summary['missions_completed']}",
        "# HELP warehouse_fleet_incidents_total Injected and detected incidents.",
        "# TYPE warehouse_fleet_incidents_total gauge",
        f"warehouse_fleet_incidents_total {summary['faults_injected']}",
        "# HELP warehouse_fleet_recovery_milliseconds Mean incident recovery time.",
        "# TYPE warehouse_fleet_recovery_milliseconds gauge",
        f"warehouse_fleet_recovery_milliseconds {summary['mean_time_to_recovery_ms']}",
        "# HELP warehouse_fleet_availability_percent Mean available fleet capacity.",
        "# TYPE warehouse_fleet_availability_percent gauge",
        f"warehouse_fleet_availability_percent {summary['fleet_availability_pct']}",
        "# HELP warehouse_fleet_active_missions Current queued, retrying, and running missions.",
        "# TYPE warehouse_fleet_active_missions gauge",
        f"warehouse_fleet_active_missions {active_missions}",
        "# HELP warehouse_fleet_unresolved_incidents Current incidents without a resolution timestamp.",
        "# TYPE warehouse_fleet_unresolved_incidents gauge",
        f"warehouse_fleet_unresolved_incidents {unresolved_incidents}",
    ]
    for robot in manager.robots.values():
        available = int(robot.status in {RobotStatus.HEALTHY, RobotStatus.BUSY})
        lines.extend(
            [
                f'warehouse_robot_available{{robot_id="{robot.robot_id}"}} {available}',
                f'warehouse_robot_battery_percent{{robot_id="{robot.robot_id}"}} {robot.battery_pct:.3f}',
                f'warehouse_robot_completed_missions{{robot_id="{robot.robot_id}"}} {robot.completed_missions}',
                f'warehouse_robot_failed_missions{{robot_id="{robot.robot_id}"}} {robot.failed_missions}',
            ]
        )
    return "\n".join(lines) + "\n"
