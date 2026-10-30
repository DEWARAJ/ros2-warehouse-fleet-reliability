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
        self.done = False
        self.publish_count = 0
        self.timer = self.create_timer(0.5, self._publish_until_confirmable)

    def _publish_until_confirmable(self) -> None:
        if self.publisher.get_subscription_count() == 0:
            return
        message = String()
        message.data = self.command
        self.publisher.publish(message)
        self.publish_count += 1
        self.get_logger().info(f"injected {self.command} ({self.publish_count}/3)")
        if self.publish_count >= 3:
            self.timer.cancel()
            self.done = True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot", default="robot-01")
    parser.add_argument("--fault", default="stale_heartbeat")
    parser.add_argument("--duration", type=float, default=5.0)
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    node = FaultInjector(args.robot, args.fault, args.duration)
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.2)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
