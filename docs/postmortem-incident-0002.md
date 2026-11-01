# ROS 2 incident report: stale robot heartbeat

**Incident:** ROS-0002  
**Environment:** ROS 2 Humble six-node validation under WSL2  
**Severity:** simulated mission interruption, no safety impact  
**Status:** recovered and runtime-validated

## Summary

Robot-01 stopped publishing health messages while executing a mission. The fleet controller detected the stale heartbeat, quarantined the worker, preserved the mission identifier, requeued the interrupted work, and assigned it to robot-02. Robot-01 later resumed healthy heartbeats and was re-registered.

## Impact

One simulated mission was interrupted and reassigned. The remaining workers continued receiving missions. The successful validation run recorded zero runtime errors.

## Timeline

| Relative event | Evidence |
| --- | --- |
| Robot-01 executing a mission | `results/ros2/health-sample.txt` |
| Stale-heartbeat command published | `results/ros2/fault-injection.txt` |
| Mission requeued from robot-01 | `results/ros2/events.txt` |
| Same mission assigned to robot-02 | `results/ros2/events.txt` |
| Controller published quarantine incident | `results/ros2/incident-sample.txt` |
| Robot-01 re-registered | `results/ros2/events.txt` |
| Robot-01 healthy with empty fault code | `results/ros2/recovered-health-sample.txt` |

## Root cause

The heartbeat pause was deliberately injected to validate loss-of-contact handling. Runtime testing also exposed two implementation defects before the successful run: invalid ROS graph names derived from hyphenated business identifiers, and heartbeat starvation caused by single-threaded action execution.

## Corrective actions

- mapped external robot identifiers to valid ROS action namespaces
- moved worker action execution to a reentrant callback group and multithreaded executor
- made the fault injector wait for subscribers and publish repeatably
- added explicit incident requeue tracking to prevent duplicate retry insertion
- committed raw DDS topic captures and a machine-readable validation summary

## Follow-up

Repeat the scenario with a physical heartbeat source and preserve Wi-Fi signal, power, and device-temperature telemetry. Until that test is run, the result remains labeled as ROS 2 simulation evidence.
