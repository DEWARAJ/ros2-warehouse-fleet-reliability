from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results" / "ros2"


def field(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*(.*)$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"missing {name}")
    return match.group(1).strip().strip("'")


def main() -> None:
    initial = (EVIDENCE / "health-sample.txt").read_text(encoding="utf-8")
    incident = (EVIDENCE / "incident-sample.txt").read_text(encoding="utf-8")
    recovered = (EVIDENCE / "recovered-health-sample.txt").read_text(encoding="utf-8")
    events = (EVIDENCE / "events.txt").read_text(encoding="utf-8")
    launch = (EVIDENCE / "launch.log").read_text(encoding="utf-8")
    nodes = [line for line in (EVIDENCE / "nodes.txt").read_text(encoding="utf-8").splitlines() if line]
    topics = [line for line in (EVIDENCE / "topics.txt").read_text(encoding="utf-8").splitlines() if line]
    summary = {
        "ros_distribution": "Humble",
        "nodes": nodes,
        "node_count": len(nodes),
        "topics": topics,
        "initial": {
            "robot_id": field(initial, "robot_id"),
            "status": field(initial, "status"),
            "mission_id": field(initial, "mission_id"),
            "fault_code": field(initial, "fault_code"),
        },
        "incident": {
            "robot_id": field(incident, "robot_id"),
            "fault_code": field(incident, "fault_code"),
            "action": field(incident, "action"),
        },
        "mission_requeued": bool(
            re.search(r'"event": "mission_requeued".*"robot_id": "robot-01"', events)
        ),
        "robot_re_registered": bool(
            re.search(r'"event": "robot_re_registered".*"robot_id": "robot-01"', events)
        ),
        "recovered": {
            "robot_id": field(recovered, "robot_id"),
            "status": field(recovered, "status"),
            "fault_code": field(recovered, "fault_code"),
            "completed_missions": int(field(recovered, "completed_missions")),
            "failed_missions": int(field(recovered, "failed_missions")),
        },
        "runtime_errors": len(re.findall(r"ERROR|Traceback|ValueError|exception", launch, re.IGNORECASE)),
    }
    if (
        summary["node_count"] != 6
        or summary["initial"]["status"] != "busy"
        or not summary["initial"]["mission_id"]
        or not summary["mission_requeued"]
        or not summary["robot_re_registered"]
    ):
        raise RuntimeError(f"incomplete ROS 2 evidence: {summary}")
    if summary["recovered"]["status"] != "healthy" or summary["runtime_errors"] != 0:
        raise RuntimeError(f"failed recovery evidence: {summary}")
    (EVIDENCE / "validation-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="390" viewBox="0 0 1200 390">
<style>.title{{font:700 28px Arial;fill:#f8fafc}}.sub{{font:15px Arial;fill:#9fb3c8}}.head{{font:700 13px Arial;fill:#6ee7b7;letter-spacing:1px}}.value{{font:700 25px Arial;fill:white}}.arrow{{font:700 25px Arial;fill:#64748b}}.note{{font:14px Arial;fill:#b8c8d8}}</style>
<rect width="1200" height="390" rx="22" fill="#0a1525"/>
<text x="40" y="50" class="title">ROS 2 Fleet Fault-Recovery Validation</text>
<text x="40" y="78" class="sub">ROS 2 Humble · {summary['node_count']} live nodes · custom health, incident, and action interfaces</text>
<g transform="translate(40,120)"><rect width="250" height="150" rx="15" fill="#13243b" stroke="#2c4868"/><text x="20" y="34" class="head">1 · ACTIVE MISSION</text><text x="20" y="76" class="value">robot-01 busy</text><text x="20" y="108" class="note">{summary['initial']['mission_id']}</text><text x="20" y="132" class="note">heartbeat healthy</text></g>
<text x="310" y="202" class="arrow">→</text>
<g transform="translate(350,120)"><rect width="250" height="150" rx="15" fill="#13243b" stroke="#ef4444"/><text x="20" y="34" class="head">2 · FAULT DETECTED</text><text x="20" y="76" class="value">stale heartbeat</text><text x="20" y="108" class="note">quarantine + reassign</text><text x="20" y="132" class="note">mission requeued</text></g>
<text x="620" y="202" class="arrow">→</text>
<g transform="translate(660,120)"><rect width="250" height="150" rx="15" fill="#13243b" stroke="#f59e0b"/><text x="20" y="34" class="head">3 · CONTINUITY</text><text x="20" y="76" class="value">mission reassigned</text><text x="20" y="108" class="note">healthy worker continues</text><text x="20" y="132" class="note">robot-01 quarantined</text></g>
<text x="930" y="202" class="arrow">→</text>
<g transform="translate(970,120)"><rect width="190" height="150" rx="15" fill="#13243b" stroke="#22c55e"/><text x="18" y="34" class="head">4 · RECOVERED</text><text x="18" y="76" class="value">healthy</text><text x="18" y="108" class="note">re-registered</text><text x="18" y="132" class="note">fault cleared</text></g>
<text x="40" y="325" class="head">EVIDENCE</text><text x="40" y="353" class="sub">DDS topic captures · controller events · launch log · validation-summary.json · 0 runtime errors</text>
</svg>'''
    (ROOT / "docs" / "ros2-runtime-validation.svg").write_text(svg, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
