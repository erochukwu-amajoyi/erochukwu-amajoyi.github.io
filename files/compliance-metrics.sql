-- The pipeline supplies @cutoff as the exclusive reporting boundary.
-- Open cases include any not closed before that boundary.
SELECT COUNT(*) AS total_cases,
 SUM(closed_at IS NULL OR closed_at >= @cutoff) AS open_cases,
 SUM(due_at < @cutoff AND (closed_at IS NULL OR closed_at >= @cutoff)) AS overdue_open_cases,
 SUM(due_at < @cutoff) AS due_cases,
 SUM(due_at < @cutoff AND closed_at IS NOT NULL AND closed_at <= due_at) AS ontime_due_cases,
 SUM(closed_at IS NOT NULL AND closed_at < @cutoff) AS closed_cases,
 ROUND(AVG(CASE WHEN closed_at < @cutoff THEN TIMESTAMPDIFF(SECOND, opened_at, closed_at) / 86400.0 END), 4) AS mean_resolution_days
FROM cases WHERE opened_at < @cutoff;
