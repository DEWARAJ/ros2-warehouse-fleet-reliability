#!/usr/bin/env bash
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/ros2_ws"
source /opt/ros/humble/setup.bash
source install/setup.bash
mkdir -p "$ROOT/results/ros2"
rm -f "$ROOT/results/ros2/"*.txt "$ROOT/results/ros2/launch.log"

cleanup() {
  kill "${LAUNCH_PID:-}" 2>/dev/null || true
  pkill -f "/warehouse_fleet_ros/" 2>/dev/null || true
}
trap cleanup EXIT

ros2 launch warehouse_fleet_ros five_robot_lab.launch.py > "$ROOT/results/ros2/launch.log" 2>&1 &
LAUNCH_PID=$!

for _ in $(seq 1 25); do
  if ros2 topic list 2>/dev/null | grep -qx '/fleet/health'; then
    break
  fi
  sleep 1
done

if ! ros2 topic list 2>/dev/null | grep -qx '/fleet/health'; then
  echo "fleet health topic did not become discoverable" >&2
  exit 1
fi

ros2 node list | sort > "$ROOT/results/ros2/nodes.txt"
ros2 topic list -t > "$ROOT/results/ros2/topics.txt"
timeout 12s ros2 topic echo --once /fleet/health warehouse_fleet_interfaces/msg/RobotHealth \
  --filter "m.robot_id == 'robot-01' and m.status == 'busy' and m.mission_id != ''" \
  > "$ROOT/results/ros2/health-sample.txt"

timeout 18s ros2 topic echo /fleet/events std_msgs/msg/String \
  > "$ROOT/results/ros2/events.txt" &
EVENT_ECHO_PID=$!
timeout 15s ros2 topic echo --once /fleet/incidents warehouse_fleet_interfaces/msg/FleetIncident \
  --filter "m.robot_id == 'robot-01'" > "$ROOT/results/ros2/incident-sample.txt" &
INCIDENT_ECHO_PID=$!

set +e
timeout 8s ros2 run warehouse_fleet_ros fault_injector \
  --robot robot-01 --fault stale_heartbeat --duration 5 \
  > "$ROOT/results/ros2/fault-injection.txt" 2>&1
INJECT_STATUS=$?
set -e
if [[ $INJECT_STATUS -ne 0 && $INJECT_STATUS -ne 124 ]]; then
  exit "$INJECT_STATUS"
fi

wait "$INCIDENT_ECHO_PID"
sleep 6
timeout 12s ros2 topic echo --once /fleet/health warehouse_fleet_interfaces/msg/RobotHealth \
  --filter "m.robot_id == 'robot-01' and m.status == 'healthy' and m.fault_code == ''" \
  > "$ROOT/results/ros2/recovered-health-sample.txt"

set +e
wait "$EVENT_ECHO_PID"
EVENT_STATUS=$?
set -e
if [[ $EVENT_STATUS -ne 0 && $EVENT_STATUS -ne 124 ]]; then
  exit "$EVENT_STATUS"
fi
grep -q 'mission_requeued.*robot-01' "$ROOT/results/ros2/events.txt"
grep -q 'robot_re_registered.*robot-01' "$ROOT/results/ros2/events.txt"

echo "ROS2_RUNTIME_VALIDATED"
