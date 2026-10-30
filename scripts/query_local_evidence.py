from __future__ import annotations

import json
import sqlite3
from pathlib import Path


DATABASE = Path(__file__).resolve().parents[1] / "results" / "fleet_evidence.db"

QUERIES = {
    "mission_status": "SELECT status, COUNT(*) AS count FROM missions GROUP BY status ORDER BY status",
    "incidents_by_fault": "SELECT fault, COUNT(*) AS count, ROUND(AVG(resolved_ms - detected_ms), 2) AS mean_recovery_ms FROM incidents GROUP BY fault ORDER BY count DESC, fault",
    "robot_outcomes": "SELECT robot_id, completed_missions, failed_missions FROM robots ORDER BY robot_id",
}


def main() -> None:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    report = {name: [dict(row) for row in connection.execute(sql)] for name, sql in QUERIES.items()}
    connection.close()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
