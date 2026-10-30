# Runbook: localization-confidence failure

## Trigger

Pose covariance exceeds the operational threshold or odometry becomes stale.

## Triage and containment

1. Stop motion and preserve the latest pose, scan and transform timestamps.
2. Check sensor freshness, frame transforms, map version and time synchronization.
3. Quarantine the robot and reassign its mission only after the stop is acknowledged.

## Recovery

Attempt relocalization from a known-safe pose. Return the robot to service only after pose covariance and transform freshness remain healthy for the configured observation window.
