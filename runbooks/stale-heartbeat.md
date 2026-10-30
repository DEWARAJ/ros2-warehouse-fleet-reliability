# Runbook: stale robot heartbeat

## Trigger

The controller has not observed a robot heartbeat inside the configured health window.

## Triage

1. Record robot ID, mission ID, last heartbeat and last odometry timestamps.
2. Check whether telemetry loss affects one robot or a site-wide group.
3. Compare process health, network reachability and ROS 2 discovery state.
4. Preserve the robot's logs before restarting the worker.

## Containment and recovery

1. Quarantine the robot so no new mission is assigned.
2. Return its running mission to the queue with the same idempotency key.
3. Restart or re-register the worker only after command ownership is cleared.
4. Require consecutive healthy heartbeats before returning the robot to service.

## Verification

Confirm that the mission was assigned once, the robot reports current odometry, and the incident has a resolved timestamp. Review recurrence by robot and software version.
