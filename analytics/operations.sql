-- 1. Fleet mission completion rate and throughput
SELECT
    COUNT(*) AS missions_total,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / NULLIF(COUNT(*), 0), 2) AS completion_pct,
    ROUND(COUNT(*) FILTER (WHERE status = 'completed') /
          NULLIF(EXTRACT(EPOCH FROM (MAX(completed_at) - MIN(created_at))) / 3600.0, 0), 2) AS missions_per_hour
FROM missions;

-- 2. Failure and retry rate by robot
SELECT
    r.robot_id,
    r.completed_missions,
    r.failed_missions,
    ROUND(100.0 * r.failed_missions /
          NULLIF(r.completed_missions + r.failed_missions, 0), 2) AS failure_pct,
    COUNT(i.incident_id) AS incidents
FROM robots r
LEFT JOIN incidents i ON i.robot_id = r.robot_id
GROUP BY r.robot_id, r.completed_missions, r.failed_missions
ORDER BY failure_pct DESC NULLS LAST;

-- 3. Mean and p95 time to recovery by fault type
SELECT
    fault,
    COUNT(*) AS incident_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at - detected_at)))::NUMERIC, 2) AS mean_recovery_seconds,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP
          (ORDER BY EXTRACT(EPOCH FROM (resolved_at - detected_at)))::NUMERIC, 2) AS p95_recovery_seconds
FROM incidents
WHERE resolved_at IS NOT NULL
GROUP BY fault
ORDER BY incident_count DESC;

-- 4. Robots currently missing their health objective
SELECT robot_id, status, battery_pct, updated_at
FROM robots
WHERE status NOT IN ('healthy', 'busy') OR battery_pct < 20
ORDER BY updated_at;

-- 5. Incident impact: missions requiring retry or manual follow-up
SELECT
    i.fault,
    COUNT(DISTINCT i.mission_id) AS impacted_missions,
    COUNT(*) FILTER (WHERE i.resolved_at IS NULL) AS unresolved_incidents,
    ROUND(AVG(m.attempts), 2) AS mean_attempts
FROM incidents i
LEFT JOIN missions m ON m.mission_id = i.mission_id
GROUP BY i.fault
ORDER BY impacted_missions DESC;

-- 6. Estimated downtime per robot from incident intervals
SELECT
    robot_id,
    ROUND(SUM(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - detected_at)))::NUMERIC, 2) AS downtime_seconds
FROM incidents
GROUP BY robot_id
ORDER BY downtime_seconds DESC;
