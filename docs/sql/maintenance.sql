-- Maintenance helpers

-- 1) One-time CLUSTER by time (if downtime is OK). Improves locality for time scans
-- CLUSTER VERBOSE profiles USING idx_profiles_time_btree;
-- ANALYZE profiles;

-- 2) Regular analyze (after bulk loads)
ANALYZE profiles;

-- 3) Increase statistics target if needed
-- ALTER TABLE profiles ALTER COLUMN keywords SET STATISTICS 1000;

-- 4) Check bloat and visibility map (requires pgstattuple extension)
-- CREATE EXTENSION IF NOT EXISTS pgstattuple;
-- SELECT * FROM pgstattuple('profiles');
