from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Incident, Mission, Robot


class EventStore:
    """Local SQLite evidence store with a schema mirrored in database/schema.sql."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS robots (
                robot_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                battery_pct REAL NOT NULL,
                completed_missions INTEGER NOT NULL,
                failed_missions INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS missions (
                mission_id TEXT PRIMARY KEY,
                robot_id TEXT,
                status TEXT NOT NULL,
                created_ms INTEGER NOT NULL,
                started_ms INTEGER,
                completed_ms INTEGER,
                attempts INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                robot_id TEXT NOT NULL,
                mission_id TEXT,
                fault TEXT NOT NULL,
                detected_ms INTEGER NOT NULL,
                resolved_ms INTEGER,
                action TEXT NOT NULL,
                details_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_ms INTEGER NOT NULL,
                robot_id TEXT NOT NULL,
                status TEXT NOT NULL,
                battery_pct REAL NOT NULL,
                mission_id TEXT
            );
            CREATE TABLE IF NOT EXISTS operator_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_ms INTEGER NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                details_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_incidents_robot ON incidents(robot_id);
            CREATE INDEX IF NOT EXISTS idx_incidents_fault ON incidents(fault);
            CREATE INDEX IF NOT EXISTS idx_telemetry_robot_time ON telemetry(robot_id, timestamp_ms);
            """
        )

    def snapshot(self, now_ms: int, robots: Iterable[Robot]) -> None:
        for robot in robots:
            self.connection.execute(
                """INSERT INTO robots VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(robot_id) DO UPDATE SET
                    status=excluded.status, battery_pct=excluded.battery_pct,
                    completed_missions=excluded.completed_missions,
                    failed_missions=excluded.failed_missions""",
                (
                    robot.robot_id,
                    robot.status.value,
                    robot.battery_pct,
                    robot.completed_missions,
                    robot.failed_missions,
                ),
            )
            self.connection.execute(
                "INSERT INTO telemetry(timestamp_ms, robot_id, status, battery_pct, mission_id) VALUES (?, ?, ?, ?, ?)",
                (now_ms, robot.robot_id, robot.status.value, robot.battery_pct, robot.mission_id),
            )
        self.connection.commit()

    def save_mission(self, mission: Mission) -> None:
        self.connection.execute(
            """INSERT INTO missions VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mission_id) DO UPDATE SET
                robot_id=excluded.robot_id, status=excluded.status,
                started_ms=excluded.started_ms, completed_ms=excluded.completed_ms,
                attempts=excluded.attempts""",
            (
                mission.mission_id,
                mission.robot_id,
                mission.status.value,
                mission.created_ms,
                mission.started_ms,
                mission.completed_ms,
                mission.attempts,
            ),
        )
        self.connection.commit()

    def save_incident(self, incident: Incident) -> None:
        self.connection.execute(
            """INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(incident_id) DO UPDATE SET resolved_ms=excluded.resolved_ms,
                details_json=excluded.details_json""",
            (
                incident.incident_id,
                incident.robot_id,
                incident.mission_id,
                incident.fault.value,
                incident.detected_ms,
                incident.resolved_ms,
                incident.action,
                json.dumps(incident.details, sort_keys=True),
            ),
        )
        self.connection.commit()

    def query(self, sql: str) -> list[dict[str, object]]:
        return [dict(row) for row in self.connection.execute(sql).fetchall()]

    def save_audit(self, timestamp_ms: int, actor: str, action: str, target: str, details: dict[str, object]) -> None:
        self.connection.execute(
            "INSERT INTO operator_audit(timestamp_ms, actor, action, target, details_json) VALUES (?, ?, ?, ?, ?)",
            (timestamp_ms, actor, action, target, json.dumps(details, sort_keys=True)),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
