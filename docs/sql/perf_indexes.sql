-- Performance indexes for `profiles`
-- Run on your Aiven Postgres. Safe to run multiple times.

-- 1) Time indexes
CREATE INDEX IF NOT EXISTS idx_profiles_time_btree
ON profiles (time_coverage_start);

CREATE INDEX IF NOT EXISTS idx_profiles_time_brin
ON profiles USING BRIN (time_coverage_start);

-- 2) Covering index for common projections (Postgres 11+ supports INCLUDE)
-- Adjust included columns to match your app's SELECT list
CREATE INDEX IF NOT EXISTS idx_profiles_time_cover
ON profiles (time_coverage_start) INCLUDE (profile_id, parquet_path, latitude, longitude);

-- 3) Composite index for time + bbox
CREATE INDEX IF NOT EXISTS idx_profiles_time_lat_lon
ON profiles (time_coverage_start, latitude, longitude);

-- 4) Expression index for year filters
CREATE INDEX IF NOT EXISTS idx_profiles_year
ON profiles ((date_trunc('year', time_coverage_start)));

-- 5) Ensure spatial index exists (created in table DDL)
-- CREATE INDEX IF NOT EXISTS idx_profiles_geom ON profiles USING GIST (geom);

-- Optional: if you frequently filter by institution or float_id with time
-- CREATE INDEX IF NOT EXISTS idx_profiles_institution_time
-- ON profiles (institution, time_coverage_start);
-- CREATE INDEX IF NOT EXISTS idx_profiles_float_time
-- ON profiles (float_id, time_coverage_start);

-- Maintenance after creating indexes
ANALYZE profiles;