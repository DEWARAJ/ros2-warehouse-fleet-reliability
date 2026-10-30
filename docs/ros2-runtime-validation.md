# ROS 2 Humble runtime validation

## Environment

- Ubuntu 22.04 under WSL2
- ROS 2 Humble
- Python 3.10
- `colcon build --symlink-install`
- one fleet controller and five simulated robot workers

## Procedure

The checked-in `scripts/validate_ros2_runtime.sh` performs the complete test:

1. Launch the controller and five workers.
2. Wait for DDS discovery of `/fleet/health`.
3. Record the node and topic graphs.
4. Capture robot-01 while executing a mission.
5. Publish three `stale_heartbeat` fault commands after subscribers are discovered.
6. Capture the controller's incident message.
7. Verify the interrupted mission is requeued.
8. Verify robot-01 reports healthy again and is re-registered.
9. Shut down every launched node.

## Observed evidence

- Six nodes were present: `/fleet_controller` and `/robot_worker_01` through `/robot_worker_05`.
- Robot-01 was initially busy on a mission with an empty fault code.
- The controller emitted a `stale_heartbeat` incident for robot-01 with the action `quarantine_and_reassign`.
- The event stream recorded `mission_requeued` for robot-01.
- The event stream recorded `robot_re_registered` for robot-01.
- Robot-01 subsequently reported `healthy` with an empty fault code.
- The launch log contained no runtime errors or tracebacks in the successful run.

Raw evidence is stored in `results/ros2/`.

## Defects found by runtime testing

### Invalid action namespaces

Application robot IDs used hyphens, such as `robot-01`, which ROS graph names reject. The implementation now preserves the business identifier in messages while mapping action namespaces to `robot_01`.

### False heartbeat failures during mission execution

The initial worker used a single-threaded executor. Its mission callback prevented the heartbeat timer from running and caused healthy busy robots to appear stale. The worker now uses a reentrant action callback group with a multithreaded executor, allowing mission execution, fault commands, and health publication to proceed concurrently.

These failures were discovered through the real ROS 2 runtime rather than source inspection.
