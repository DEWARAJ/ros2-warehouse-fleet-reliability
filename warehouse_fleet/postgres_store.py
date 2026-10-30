from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Incident, Mission, Robot


class PostgresEventStore:
    """PostgreSQL persistence adapter with the same writes as the local evidence store."""

    def __init__(self, dsn: str, schema_path: str | Path | None = None) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install the postgres extra: pip install -e '.[postgres]'") from exc
        self.connection = psycopg.connect(dsn)
        if schema_path is not None:
            schema = Path(schema_path).read_text(encoding="utf-8")
            with self.connection.cursor() as cursor:
                cursor.execute(schema)
            self.connection.commit()

    def snapshot(self, now_ms: int, robots: Iterable[Robot]) -> None:
        with self.connection.cursor() as cursor:
            for robot in robots:
                cursor.execute(
                    """INSERT INTO robots(robot_id, status, battery_pct, completed_missions, failed_missions, updated_at)
                    VALUES (%s, %s, %s, %s, %s, TO_TIMESTAMP(%s / 1000.0))
                    ON CONFLICT(robot_id) DO UPDATE SET status=EXCLUDED.status,
                    battery_pct=EXCLUDED.battery_pct, completed_missions=EXCLUDED.completed_missions,
                    failed_missions=EXCLUDED.failed_missions, updated_at=EXCLUDED.updated_at""",
                    (robot.robot_id, robot.status.value, robot.battery_pct, robot.completed_missions, robot.failed_missions, now_ms),
                )
                cursor.execute(
                    """INSERT INTO telemetry(recorded_at, robot_id, status, battery_pct, mission_id)
                    VALUES (TO_TIMESTAMP(%s / 1000.0), %s, %s, %s, %s)""",
                    (now_ms, robot.robot_id, robot.status.value, robot.battery_pct, robot.mission_id),
                )
        self.connection.commit()

    def save_mission(self, mission: Mission) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO missions(mission_id, robot_id, status, created_at, started_at, completed_at, attempts)
                VALUES (%s, %s, %s, TO_TIMESTAMP(%s / 1000.0),
                        CASE WHEN %s IS NULL THEN NULL ELSE TO_TIMESTAMP(%s / 1000.0) END,
                        CASE WHEN %s IS NULL THEN NULL ELSE TO_TIMESTAMP(%s / 1000.0) END, %s)
                ON CONFLICT(mission_id) DO UPDATE SET robot_id=EXCLUDED.robot_id,
                status=EXCLUDED.status, started_at=EXCLUDED.started_at,
                completed_at=EXCLUDED.completed_at, attempts=EXCLUDED.attempts""",
                (
                    mission.mission_id,
                    mission.robot_id,
                    mission.status.value,
                    mission.created_ms,
                    mission.started_ms,
                    mission.started_ms,
                    mission.completed_ms,
                    mission.completed_ms,
                    mission.attempts,
                ),
            )
        self.connection.commit()

    def save_incident(self, incident: Incident) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO incidents(incident_id, robot_id, mission_id, fault, detected_at, resolved_at, action, details)
                VALUES (%s, %s, %s, %s, TO_TIMESTAMP(%s / 1000.0),
                        CASE WHEN %s IS NULL THEN NULL ELSE TO_TIMESTAMP(%s / 1000.0) END, %s, %s::jsonb)
                ON CONFLICT(incident_id) DO UPDATE SET resolved_at=EXCLUDED.resolved_at, details=EXCLUDED.details""",
                (
                    incident.incident_id,
                    incident.robot_id,
                    incident.mission_id,
                    incident.fault.value,
                    incident.detected_ms,
                    incident.resolved_ms,
                    incident.resolved_ms,
                    incident.action,
                    json.dumps(incident.details, sort_keys=True),
                ),
            )
        self.connection.commit()

    def save_audit(self, timestamp_ms: int, actor: str, action: str, target: str, details: dict[str, object]) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO operator_audit(recorded_at, actor, action, target, details)
                VALUES (TO_TIMESTAMP(%s / 1000.0), %s, %s, %s, %s::jsonb)""",
                (timestamp_ms, actor, action, target, json.dumps(details, sort_keys=True)),
            )
        self.connection.commit()

    def query(self, sql: str) -> list[dict[str, object]]:
        with self.connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [description.name for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self) -> None:
        self.connection.close()
