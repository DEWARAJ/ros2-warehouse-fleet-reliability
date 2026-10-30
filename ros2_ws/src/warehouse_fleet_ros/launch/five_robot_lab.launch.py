from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    workers = [
        Node(
            package="warehouse_fleet_ros",
            executable="robot_worker",
            name=f"robot_worker_{index:02d}",
            parameters=[{"robot_id": f"robot-{index:02d}"}],
            output="screen",
        )
        for index in range(1, 6)
    ]
    return LaunchDescription(
        [
            Node(
                package="warehouse_fleet_ros",
                executable="fleet_controller",
                name="fleet_controller",
                output="screen",
            ),
            *workers,
        ]
    )
