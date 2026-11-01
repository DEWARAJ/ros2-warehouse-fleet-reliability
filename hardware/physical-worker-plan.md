# Physical worker integration plan

This plan upgrades one simulated worker to a real ESP32 micro-ROS or Raspberry Pi heartbeat source. It is an implementation contract and does not claim that hardware validation has been completed.

## Device telemetry

Publish at 2 Hz:

- stable robot identifier, using `robot-05`
- heartbeat sequence and device monotonic time
- battery voltage or supply voltage
- Wi-Fi RSSI
- CPU or board temperature when available
- current mission identifier
- device fault code

## Fleet behavior

1. Launch the controller and simulated workers 01 through 04.
2. Register the physical worker as robot-05.
3. Assign a mission and record the active identifier.
4. Disconnect Wi-Fi or power during execution.
5. Verify heartbeat timeout, quarantine, mission requeue, and reassignment.
6. Restore the device and require consecutive healthy heartbeats before re-registration.
7. Record detection, reassignment, and recovery times from fleet events.

## Required evidence before making a hardware claim

- device wiring or hardware photograph
- firmware revision and configuration
- ROS topic capture before, during, and after failure
- mission event showing reassignment
- recovered health message
- measured detection and recovery times
- short video showing the physical interruption and controller response

The README and resume must continue to describe the current system as simulated until this evidence exists.
