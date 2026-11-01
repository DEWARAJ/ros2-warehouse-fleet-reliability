from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


DURATION_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd])$")
ROBOT_PATTERN = re.compile(r"robot(?:_worker)?[-_](\d{2})")
FAULT_PATTERN = re.compile(
    r"node_crash|stale_heartbeat|stale_odometry|sensor_timeout|"
    r"localization_drop|network_delay|low_battery|obstacle_timeout"
)
RUNBOOKS = {
    "stale_heartbeat": "runbooks/stale-heartbeat.md",
    "localization_drop": "runbooks/localization-failure.md",
    "stale_odometry": "runbooks/localization-failure.md",
    "obstacle_timeout": "runbooks/mission-timeout.md",
}


@dataclass(frozen=True)
class TriageFinding:
    robot_id: str
    fault: str
    incident_count: int
    impacted_missions: int
    downtime_ms: int
    unresolved_incidents: int
    log_matches: int
    impact_score: float
    runbook: str


def parse_duration(value: str) -> int:
    match = DURATION_PATTERN.fullmatch(value.strip().lower())
    if not match:
        raise ValueError("duration must use s, m, h, or d, for example 30m or 1h")
    scale = {"s": 1_000, "m": 60_000, "h": 3_600_000, "d": 86_400_000}
    return int(match.group("value")) * scale[match.group("unit")]


def _log_counts(paths: list[Path]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for path in paths:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            robot = ROBOT_PATTERN.search(line)
            fault = FAULT_PATTERN.search(line)
            if not robot or not fault:
                continue
            key = (f"robot-{robot.group(1)}", fault.group())
            counts[key] = counts.get(key, 0) + 1
    return counts


def analyze(database: Path, logs: list[Path], since_ms: int) -> list[TriageFinding]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        latest = connection.execute(
            "SELECT COALESCE(MAX(COALESCE(resolved_ms, detected_ms)), 0) FROM incidents"
        ).fetchone()[0]
        cutoff = max(0, int(latest) - since_ms)
        rows = connection.execute(
            """
            SELECT
                robot_id,
                fault,
                COUNT(*) AS incident_count,
                COUNT(DISTINCT mission_id) AS impacted_missions,
                CAST(SUM(COALESCE(resolved_ms, ?) - detected_ms) AS INTEGER) AS downtime_ms,
                SUM(CASE WHEN resolved_ms IS NULL THEN 1 ELSE 0 END) AS unresolved_incidents
            FROM incidents
            WHERE detected_ms >= ?
            GROUP BY robot_id, fault
            """,
            (latest, cutoff),
        ).fetchall()
    finally:
        connection.close()

    log_counts = _log_counts(logs)
    findings = []
    database_keys: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["robot_id"]), str(row["fault"]))
        database_keys.add(key)
        downtime_ms = int(row["downtime_ms"] or 0)
        impacted = int(row["impacted_missions"] or 0)
        unresolved = int(row["unresolved_incidents"] or 0)
        score = round(impacted * 10 + unresolved * 25 + downtime_ms / 1_000, 2)
        findings.append(
            TriageFinding(
                robot_id=key[0],
                fault=key[1],
                incident_count=int(row["incident_count"]),
                impacted_missions=impacted,
                downtime_ms=downtime_ms,
                unresolved_incidents=unresolved,
                log_matches=log_counts.get(key, 0),
                impact_score=score,
                runbook=RUNBOOKS.get(key[1], "runbooks/mission-timeout.md"),
            )
        )
    for key, matches in log_counts.items():
        if key in database_keys:
            continue
        findings.append(
            TriageFinding(
                robot_id=key[0],
                fault=key[1],
                incident_count=0,
                impacted_missions=0,
                downtime_ms=0,
                unresolved_incidents=0,
                log_matches=matches,
                impact_score=round(matches * 0.1, 2),
                runbook=RUNBOOKS.get(key[1], "runbooks/mission-timeout.md"),
            )
        )
    return sorted(findings, key=lambda finding: (-finding.impact_score, finding.robot_id, finding.fault))


def render_text(findings: list[TriageFinding], since: str) -> str:
    lines = [f"Fleet incident triage | window={since}"]
    if not findings:
        return "\n".join([*lines, "No matching incidents."])
    lines.append("rank  robot     fault               incidents  missions  downtime  logs  score  runbook")
    for rank, finding in enumerate(findings, start=1):
        lines.append(
            f"{rank:>4}  {finding.robot_id:<8}  {finding.fault:<18}  "
            f"{finding.incident_count:>9}  {finding.impacted_missions:>8}  "
            f"{finding.downtime_ms / 1_000:>7.1f}s  {finding.log_matches:>4}  "
            f"{finding.impact_score:>5.1f}  {finding.runbook}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fleetctl triage",
        description="Correlate fleet incidents with ROS 2 logs and rank failures by mission impact.",
    )
    parser.add_argument("command", nargs="?", default="triage", choices=["triage"])
    parser.add_argument("--since", default="1h", help="relative window such as 30m, 1h, or 1d")
    parser.add_argument("--db", type=Path, default=Path("results/fleet_evidence.db"))
    parser.add_argument("--log", type=Path, action="append", default=[])
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    findings = analyze(args.db, args.log, parse_duration(args.since))
    if args.as_json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2))
    else:
        print(render_text(findings, args.since))


if __name__ == "__main__":
    main()
