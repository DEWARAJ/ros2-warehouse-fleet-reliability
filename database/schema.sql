CREATE TABLE robots (
    robot_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    battery_pct DOUBLE PRECISION NOT NULL CHECK (battery_pct BETWEEN 0 AND 100),
    completed_missions INTEGER NOT NULL DEFAULT 0,
    failed_missions INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE missions (
    mission_id TEXT PRIMARY KEY,
    robot_id TEXT REFERENCES robots(robot_id),
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE incidents (
    incident_id TEXT PRIMARY KEY,
    robot_id TEXT NOT NULL REFERENCES robots(robot_id),
    mission_id TEXT REFERENCES missions(mission_id),
    fault TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    action TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE TABLE telemetry (
    id BIGSERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL,
    robot_id TEXT NOT NULL REFERENCES robots(robot_id),
    status TEXT NOT NULL,
    battery_pct DOUBLE PRECISION NOT NULL,
    mission_id TEXT
);

CREATE TABLE operator_audit (
    id BIGSERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE INDEX incidents_robot_idx ON incidents(robot_id);
CREATE INDEX incidents_fault_idx ON incidents(fault);
CREATE INDEX telemetry_robot_recorded_idx ON telemetry(robot_id, recorded_at DESC);
