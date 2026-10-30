from __future__ import annotations

import argparse

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class FaultInjector(Node):
    def __init__(self, robot_id: str, fault: str, duration: float) -> None:
        super().__init__("fault_injector")
        self.publisher = self.create_publisher(String, "/fleet/fault_commands", 10)
        self.command = f"{robot_id}:{fault}:{duration}"
        self.timer = self.create_timer(1.0, self._publish_once)

    def _publish_once(self) -> None:
        message = String()
        message.data = self.command
        self.publisher.publish(message)
        self.get_logger().info(f"injected {self.command}")
        self.timer.cancel()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot", default="robot-01")
    parser.add_argument("--fault", default="stale_heartbeat")
    parser.add_argument("--duration", type=float, default=5.0)
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    node = FaultInjector(args.robot, args.fault, args.duration)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
