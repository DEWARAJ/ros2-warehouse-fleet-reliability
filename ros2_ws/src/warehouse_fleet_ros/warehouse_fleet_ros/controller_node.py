from __future__ import annotations

import json
import time
from functools import partial

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
from warehouse_fleet_interfaces.action import ExecuteMission
from warehouse_fleet_interfaces.msg import FleetIncident, RobotHealth


class FleetController(Node):
    def __init__(self) -> None:
        super().__init__("fleet_controller")
        self.declare_parameter("heartbeat_timeout_seconds", 2.0)
        self.timeout = float(self.get_parameter("heartbeat_timeout_seconds").value)
        self.last_health: dict[str, float] = {}
        self.health_status: dict[str, str] = {}
        self.quarantined: set[str] = set()
        self.active_missions: dict[str, tuple[str, object]] = {}
        self.retry_queue: list[str] = []
        self.mission_counter = 0
        robot_ids = [f"robot-{index:02d}" for index in range(1, 6)]
        self.action_clients = {
            robot_id: ActionClient(self, ExecuteMission, f"/{robot_id}/execute_mission") for robot_id in robot_ids
        }
        self.create_subscription(RobotHealth, "/fleet/health", self._health, 50)
        self.incident_publisher = self.create_publisher(FleetIncident, "/fleet/incidents", 20)
        self.event_publisher = self.create_publisher(String, "/fleet/events", 20)
        self.create_timer(0.25, self._watchdog)
        self.create_timer(1.0, self._dispatch)

    def _health(self, message: RobotHealth) -> None:
        self.last_health[message.robot_id] = time.monotonic()
        self.health_status[message.robot_id] = message.status
        if message.robot_id in self.quarantined and message.status == "healthy":
            self.quarantined.remove(message.robot_id)
            self._event("robot_re_registered", message.robot_id, message.mission_id)
        if message.fault_code and message.robot_id not in self.quarantined:
            self._incident(message.robot_id, message.mission_id, message.fault_code)

    def _dispatch(self) -> None:
        for robot_id, client in self.action_clients.items():
            if robot_id in self.active_missions or robot_id in self.quarantined:
                continue
            if self.health_status.get(robot_id) != "healthy" or not client.wait_for_server(timeout_sec=0.0):
                continue
            if self.retry_queue:
                mission_id = self.retry_queue.pop(0)
            else:
                self.mission_counter += 1
                mission_id = f"ros-mission-{self.mission_counter:06d}"
            goal = ExecuteMission.Goal()
            goal.mission_id = mission_id
            goal.pickup_zone = "inbound"
            goal.dropoff_zone = "outbound"
            goal.expected_duration_ms = 2_000
            future = client.send_goal_async(goal)
            future.add_done_callback(partial(self._goal_response, robot_id, mission_id))

    def _goal_response(self, robot_id: str, mission_id: str, future: object) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.retry_queue.append(mission_id)
            return
        self.active_missions[robot_id] = (mission_id, goal_handle)
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(partial(self._mission_result, robot_id, mission_id))
        self._event("mission_assigned", robot_id, mission_id)

    def _mission_result(self, robot_id: str, mission_id: str, future: object) -> None:
        self.active_missions.pop(robot_id, None)
        result = future.result().result
        if not result.completed:
            if mission_id not in self.retry_queue:
                self.retry_queue.append(mission_id)
            self._event("mission_requeued", robot_id, mission_id)
        else:
            self._event("mission_completed", robot_id, mission_id)

    def _watchdog(self) -> None:
        now = time.monotonic()
        for robot_id, last_seen in list(self.last_health.items()):
            if now - last_seen > self.timeout and robot_id not in self.quarantined:
                self._incident(robot_id, "", "stale_heartbeat")

    def _incident(self, robot_id: str, mission_id: str, fault: str) -> None:
        self.quarantined.add(robot_id)
        active = self.active_missions.get(robot_id)
        if active is not None:
            active_mission_id, goal_handle = active
            goal_handle.cancel_goal_async()
            if active_mission_id not in self.retry_queue:
                self.retry_queue.append(active_mission_id)
        incident = FleetIncident()
        incident.stamp = self.get_clock().now().to_msg()
        incident.incident_id = f"{robot_id}-{self.get_clock().now().nanoseconds}"
        incident.robot_id = robot_id
        incident.mission_id = mission_id
        incident.fault_code = fault
        incident.action = "quarantine_and_reassign"
        incident.resolved = False
        self.incident_publisher.publish(incident)
        self._event("robot_quarantined", robot_id, mission_id)

    def _event(self, event: str, robot_id: str, mission_id: str) -> None:
        message = String()
        message.data = json.dumps({"event": event, "robot_id": robot_id, "mission_id": mission_id})
        self.event_publisher.publish(message)


def main() -> None:
    rclpy.init()
    node = FleetController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
