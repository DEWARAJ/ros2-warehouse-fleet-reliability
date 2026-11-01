# Reliability prioritization from deterministic evidence

## Decision

Prioritize worker-process crash containment first, followed by localization-loss recovery. Together, these two failure modes account for 65.93% of downtime in the seeded 250-mission benchmark.

## Evidence

The benchmark used five robots, 250 missions, seed `2026`, and 12 deterministic fault injections. All missions completed, while incident records preserved the fault type, affected mission, detection time, and resolution time.

| Failure mode | Incidents | Impacted missions | Downtime | Share of downtime |
| --- | ---: | ---: | ---: | ---: |
| node crash | 4 | 4 | 18.0 s | 39.56% |
| localization drop | 3 | 3 | 12.0 s | 26.37% |
| low battery | 1 | 1 | 5.5 s | 12.09% |
| network delay | 2 | 2 | 4.0 s | 8.79% |
| stale heartbeat | 1 | 1 | 3.5 s | 7.69% |
| sensor timeout | 1 | 1 | 2.5 s | 5.49% |

Total recorded downtime was 45.5 seconds. Node crashes produced the largest individual share and affected four missions. Localization drops were second and brought the cumulative share to 65.93%.

## Recommended order

1. Shorten process-crash detection and make worker restart state explicit.
2. Add localization-confidence hysteresis and require consecutive healthy samples before re-registration.
3. Preserve low-battery charging capacity because its single incident produced 5.5 seconds of downtime.
4. Continue monitoring network delay and stale-heartbeat recurrence by robot and software version.

## Reproduction

```bash
python -m warehouse_fleet.cli --missions 250 --robots 5 --seed 2026
fleetctl triage --since 1d --db results/fleet_evidence.db --log results/ros2/launch.log
```

The PostgreSQL versions of the MTBF, MTTR, Pareto, hourly heatmap, rolling mission-success, and priority-score queries are in [`analytics/reliability.sql`](../analytics/reliability.sql).

These findings describe a deterministic simulator workload. They are engineering prioritization evidence, not production-site statistics.
