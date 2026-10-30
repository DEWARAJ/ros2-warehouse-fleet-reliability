# Runbook: mission timeout

## Trigger

A mission exceeds its expected completion deadline without terminal action feedback.

## Response

1. Correlate mission ID with robot state, navigation feedback and recent incidents.
2. Distinguish blocked path, lost action feedback, stale localization and unavailable worker.
3. Cancel the original command using its idempotency key before retrying.
4. Quarantine an unhealthy robot; otherwise replan once and escalate repeated failures.

## Verification

Confirm exactly one active copy of the mission, record the recovery action and compare the resulting duration with the p95 mission-duration objective.
