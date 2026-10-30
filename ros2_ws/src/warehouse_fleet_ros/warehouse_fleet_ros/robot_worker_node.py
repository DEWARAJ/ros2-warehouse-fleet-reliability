from __future__ import annotations

import threading
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from warehouse_fleet_interfaces.action import ExecuteMission
from warehouse_fleet_interfaces.msg import RobotHealth


class RobotWorker(Node):
    def __init__(self) -> None:
        super().__init__("robot_worker")
        self.declare_parameter("robot_id", "robot-01")
        self.robot_id = self.get_parameter("robot_id").value
        action_namespace = self.robot_id.replace("-", "_")
        self.publisher = self.create_publisher(RobotHealth, "/fleet/health", 20)
        self.create_subscription(String, "/fleet/fault_commands", self._fault_command, 20)
        self.create_timer(0.5, self._heartbeat)
        self.action_callback_group = ReentrantCallbackGroup()
        self.action_server = ActionServer(
            self,
            ExecuteMission,
            f"/{action_namespace}/execute_mission",
            execute_callback=self._execute,
            goal_callback=lambda _: GoalResponse.ACCEPT,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=self.action_callback_group,
        )
        self.status = "healthy"
        self.fault = ""
        self.mission_id = ""
        self.battery_pct = 100.0
        self.completed = 0
        self.failed = 0
        self.pause_until = 0.0
        self.lock = threading.Lock()

    def _heartbeat(self) -> None:
        with self.lock:
            if time.monotonic() < self.pause_until and self.fault == "stale_heartbeat":
                return
            if self.fault and time.monotonic() >= self.pause_until:
                self.fault = ""
                self.status = "healthy"
            message = RobotHealth()
            message.stamp = self.get_clock().now().to_msg()
            message.robot_id = self.robot_id
            message.status = self.status
            message.battery_pct = self.battery_pct
            message.mission_id = self.mission_id
            message.fault_code = self.fault
            message.completed_missions = self.completed
            message.failed_missions = self.failed
            self.publisher.publish(message)

    def _fault_command(self, message: String) -> None:
        parts = message.data.split(":", maxsplit=2)
        if len(parts) != 3 or parts[0] != self.robot_id:
            return
        with self.lock:
            self.fault = parts[1]
            self.status = "degraded"
            self.pause_until = time.monotonic() + float(parts[2])
            self.get_logger().warning(f"fault injected: {self.fault}; heartbeat pause until {self.pause_until:.3f}")

    def _execute(self, goal_handle: object) -> ExecuteMission.Result:
        request = goal_handle.request
        start = time.monotonic()
        duration = max(request.expected_duration_ms / 1000.0, 0.5)
        with self.lock:
            self.mission_id = request.mission_id
            self.status = "busy"
        while time.monotonic() - start < duration:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result = ExecuteMission.Result()
                result.completed = False
                result.outcome = "cancelled"
                return result
            with self.lock:
                if self.fault and time.monotonic() < self.pause_until:
                    self.failed += 1
                    self.status = "quarantined"
                    goal_handle.abort()
                    result = ExecuteMission.Result()
                    result.completed = False
                    result.outcome = self.fault
                    result.elapsed_ms = int((time.monotonic() - start) * 1000)
                    self.mission_id = ""
                    return result
            feedback = ExecuteMission.Feedback()
            feedback.progress = min(1.0, (time.monotonic() - start) / duration)
            feedback.state = "executing"
            goal_handle.publish_feedback(feedback)
            time.sleep(0.1)
        with self.lock:
            self.completed += 1
            self.battery_pct = max(5.0, self.battery_pct - 1.0)
            self.status = "healthy"
            self.fault = ""
            self.mission_id = ""
        goal_handle.succeed()
        result = ExecuteMission.Result()
        result.completed = True
        result.outcome = "completed"
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result


def main() -> None:
    rclpy.init()
    node = RobotWorker()
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
