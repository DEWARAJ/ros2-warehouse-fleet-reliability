# ROS 2 workspace

This optional workspace turns the fleet contracts into executable ROS 2 nodes. It contains custom health and incident messages, an `ExecuteMission` action, five simulated robot workers, a heartbeat watchdog, and a fault-injection command path.

## Build on ROS 2 Humble or Jazzy

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch warehouse_fleet_ros five_robot_lab.launch.py
```

In a second shell, inject a heartbeat failure:

```bash
source install/setup.bash
ros2 run warehouse_fleet_ros fault_injector --robot robot-01 --fault stale_heartbeat --duration 5
```

Observe health and incident traffic:

```bash
ros2 topic echo /fleet/health
ros2 topic echo /fleet/incidents
ros2 topic echo /fleet/events
```

The current workers simulate mission duration and health transitions. They do not claim Nav2, Gazebo, or physical-robot validation.
