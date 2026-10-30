# Recovery-control experiment

## Question

How much operational capacity does automatic quarantine, mission reassignment, worker recovery, and re-registration preserve after robot failures?

## Method

Two deterministic trials used the same seed, five simulated robots, 500 missions, mission-duration distribution, and two injected faults: a node crash and localization-confidence failure.

- **Recovery disabled:** failed robots remain quarantined; interrupted work is reassigned to the remaining fleet.
- **Recovery enabled:** failed robots are quarantined, repaired after the configured recovery interval, and re-registered after a health transition.

These are simulation results and do not represent physical warehouse uptime.

## Results

| Metric | Recovery disabled | Recovery enabled | Change |
|---|---:|---:|---:|
| Missions completed | 500/500 | 500/500 | — |
| Fleet availability | 66.94% | 99.04% | +32.10 points |
| Throughput | 121.83 missions/min | 179.37 missions/min | +47.23% |
| Workload duration | 246.25 s | 167.25 s | −32.08% |
| Automatically recovered faults | 0/2 | 2/2 | +2 |
| Median mission latency | 36.875 s | 12.000 s | −67.46% |

The source evidence is committed in [`results/recovery_comparison.json`](../results/recovery_comparison.json) and can be regenerated with:

```bash
python -m warehouse_fleet.comparison
```

## Interpretation

Both configurations eventually completed every mission because three healthy robots retained enough capacity. The no-recovery baseline accumulated a longer queue and substantially higher mission latency. Automatic recovery restored the two workers, producing higher measured availability and throughput under the same workload.

## Limitations

The simulator uses deterministic recovery durations and does not yet include physical navigation, wireless contention, ROS 2 DDS discovery behavior, or human repair time. The ROS 2 workspace provides the executable heartbeat, action, and incident interfaces needed for the next validation stage.
