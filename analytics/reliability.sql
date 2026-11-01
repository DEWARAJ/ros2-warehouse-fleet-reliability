-- 1. MTBF and MTTR by robot. MTBF uses time between consecutive detected incidents.
WITH incident_intervals AS (
    SELECT
        robot_id,
        detected_at,
        resolved_at,
        detected_at - LAG(detected_at) OVER (
            PARTITION BY robot_id ORDER BY detected_at
        ) AS time_between_failures
    FROM incidents
)
SELECT
    robot_id,
    COUNT(*) AS incidents,
    ROUND(AVG(EXTRACT(EPOCH FROM time_between_failures))::NUMERIC, 2) AS mtbf_seconds,
    ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at - detected_at)))::NUMERIC, 2) AS mttr_seconds
FROM incident_intervals
GROUP BY robot_id
ORDER BY incidents DESC, robot_id;

-- 2. Failure-mode Pareto: downtime and cumulative share of total downtime.
WITH fault_downtime AS (
    SELECT
        fault,
        COUNT(*) AS incidents,
        COUNT(DISTINCT mission_id) AS impacted_missions,
        SUM(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - detected_at))) AS downtime_seconds
    FROM incidents
    GROUP BY fault
), ranked AS (
    SELECT
        *,
        SUM(downtime_seconds) OVER (ORDER BY downtime_seconds DESC) AS cumulative_downtime,
        SUM(downtime_seconds) OVER () AS total_downtime
    FROM fault_downtime
)
SELECT
    fault,
    incidents,
    impacted_missions,
    ROUND(downtime_seconds::NUMERIC, 2) AS downtime_seconds,
    ROUND(100 * downtime_seconds / NULLIF(total_downtime, 0), 2) AS downtime_pct,
    ROUND(100 * cumulative_downtime / NULLIF(total_downtime, 0), 2) AS cumulative_downtime_pct
FROM ranked
ORDER BY downtime_seconds DESC;

-- 3. Incident volume by hour of day for heatmap input.
SELECT
    EXTRACT(ISODOW FROM detected_at)::INTEGER AS day_of_week,
    EXTRACT(HOUR FROM detected_at)::INTEGER AS hour_of_day,
    COUNT(*) AS incidents,
    COUNT(*) FILTER (WHERE resolved_at IS NULL) AS unresolved
FROM incidents
GROUP BY day_of_week, hour_of_day
ORDER BY day_of_week, hour_of_day;

-- 4. Rolling one-hour mission success rate.
SELECT
    created_at,
    mission_id,
    status,
    ROUND(
        100 * AVG((status = 'completed')::INTEGER) OVER (
            ORDER BY created_at
            RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_one_hour_success_pct
FROM missions
ORDER BY created_at;

-- 5. Data-driven priority score: mission impact, unresolved work, and downtime.
SELECT
    fault,
    COUNT(*) AS incidents,
    COUNT(DISTINCT mission_id) AS impacted_missions,
    COUNT(*) FILTER (WHERE resolved_at IS NULL) AS unresolved,
    ROUND(SUM(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - detected_at)))::NUMERIC, 2) AS downtime_seconds,
    ROUND((
        10 * COUNT(DISTINCT mission_id)
        + 25 * COUNT(*) FILTER (WHERE resolved_at IS NULL)
        + SUM(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - detected_at)))
    )::NUMERIC, 2) AS priority_score
FROM incidents
GROUP BY fault
ORDER BY priority_score DESC;
