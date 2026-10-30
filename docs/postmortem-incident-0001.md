# Simulation incident report: robot worker crash

**Incident:** SIM-0001  
**Environment:** deterministic warehouse fleet benchmark  
**Severity:** simulated mission interruption, no safety impact  
**Status:** resolved automatically

## Summary

An injected worker crash interrupted an active mission. The controller quarantined the affected robot, returned the mission to the bounded-retry queue, assigned it to a healthy robot, and re-registered the failed worker after recovery.

## Impact

One simulated mission required another attempt. The fleet retained service through the remaining workers, and the interrupted mission completed without a duplicate terminal result.

## Detection

The controller detected the injected failure through the robot-health state transition. Production ROS 2 integration maps the same detection path to `/fleet/health`, diagnostics, and heartbeat freshness.

## Timeline

| Relative time | Event |
|---:|---|
| T+0 ms | node-crash fault injected on a busy robot |
| T+0 ms | incident recorded; robot quarantined |
| T+250 ms | interrupted mission reassigned to a healthy robot |
| T+4,000 ms | worker entered recovery state |
| T+4,500 ms | worker passed recovery transition and re-registered |

## Root cause

The fault was deliberately injected to validate containment and recovery. The relevant failure mechanism was loss of the worker process while it owned an active mission.

## Corrective controls validated

- idempotent mission identifiers
- quarantine before reassignment
- bounded retry count
- separate recovery and healthy states
- incident timestamps and audit evidence
- consecutive controller transitions before re-registration

## Follow-up

Replay the scenario using ROS 2 lifecycle nodes and rosbag2 evidence, then repeat with DDS communication loss and physical navigation state. This report must remain labeled as simulation evidence until that validation is complete.
