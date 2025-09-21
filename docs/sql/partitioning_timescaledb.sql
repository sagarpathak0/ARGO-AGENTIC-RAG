-- Optional: TimescaleDB hypertable setup (Aiven supports Timescale)
-- Requires: CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1) Convert `profiles` into a hypertable on time_coverage_start
-- SELECT create_hypertable('profiles', 'time_coverage_start', if_not_exists => TRUE);

-- 2) Compression for older chunks (optional)
-- ALTER TABLE profiles SET (timescaledb.compress, timescaledb.compress_segmentby = 'float_id');
-- SELECT add_compression_policy('profiles', INTERVAL '90 days');

-- 3) Retention policy (if desired)
-- SELECT add_retention_policy('profiles', INTERVAL '15 years');

-- Note: Recreate relevant indexes after hypertable conversion if needed.
