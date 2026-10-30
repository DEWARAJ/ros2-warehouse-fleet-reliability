# Ninety-second demonstration script

## 0–15 seconds: system overview

Show the repository architecture and the six-node ROS graph. Explain that five workers continuously execute simulated warehouse missions while the controller monitors health and manages retries.

## 15–35 seconds: healthy operation

Show `/fleet/health` for robot-01 while it is busy and point out the mission ID, battery, completed count, and empty fault code.

## 35–55 seconds: inject the failure

Run the fault injector for `robot-01:stale_heartbeat`. Show the controller's incident message with `quarantine_and_reassign` and the corresponding warning in the launch log.

## 55–75 seconds: maintain mission continuity

Show `mission_requeued` for robot-01 followed by `mission_assigned` to another worker. Explain that the mission ID is reused so the operation remains traceable and bounded by the retry policy.

## 75–90 seconds: recovery and evidence

Show `robot_re_registered` and robot-01 reporting healthy with an empty fault code. Finish on the Prometheus/Grafana architecture and the 500-mission recovery comparison.

Every number and runtime statement in the narration should point to a committed result or topic capture.
