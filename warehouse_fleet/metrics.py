from __future__ import annotations

from .manager import FleetManager
from .models import RobotStatus


def render_prometheus(manager: FleetManager) -> str:
    summary = manager.summary()
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
