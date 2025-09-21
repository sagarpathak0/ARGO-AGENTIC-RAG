# Query Optimization Plan for `profiles`

Your `profiles` table is large, and a naive `SELECT *` takes ~27s. The plan below focuses on: (1) projecting fewer columns, (2) ensuring the right indexes exist and are used, (3) partitioning and maintenance, and (4) app-side patterns that avoid full scans.

## 1) Avoid `SELECT *` — project only what you need

Most queries only need a handful of columns to pick candidate profiles.
- Example: profile_id, parquet_path, latitude, longitude, time_coverage_start
- Make sure your app queries only those columns. This unlocks index-only scans when paired with covering indexes.

## 2) Purpose-built indexes (create concurrently)

- Geospatial: Use the GiST index on `geom` with a bbox pre-filter for ST_Intersects/Within. Ensure SRID=4326.
- Time: Add both a BTREE and a BRIN on `time_coverage_start` (BRIN is great for large append-only tables). Use only one in queries; the planner will choose.
- Covering index for index-only scans: BTREE on time with INCLUDE of columns you select frequently.
- Composite index for common WHERE patterns: (time_coverage_start, latitude, longitude) for time-bounded bbox queries.
- Expression index for year/month queries: date_trunc('year', time_coverage_start).

See `docs/sql/perf_indexes.sql` for ready-to-run statements.

## 3) Partitioning (strongly recommended)

- Range partition by year (`time_coverage_start`) for 1999–2012. Queries with time filters prune partitions → no full scans.
- Alternative: Use TimescaleDB hypertable on `time_coverage_start` (Aiven supports it). You’ll get automatic chunking, compression, and great time-range performance with minimal app changes.

## 4) Table layout and maintenance

- CLUSTER (one-time) on a time index to physically order by time; improves locality for time-bounded scans.
- VACUUM (ANALYZE) after bulk inserts to update visibility map and stats. Index-only scans need the visibility map to be set.
- Increase stats target for skewed columns:
  - ALTER TABLE profiles ALTER COLUMN keywords SET STATISTICS 1000;
- Autovacuum tuning (Aiven managed) — ensure it’s not too conservative for this table.

## 5) Spatial query patterns (make the index kick in)

- Prefer:
  - geom && ST_MakeEnvelope($lon_min, $lat_min, $lon_max, $lat_max, 4326)
  - AND ST_Intersects(geom, ST_MakeEnvelope(...))
- Avoid computed transforms on the indexed column (e.g., ST_Transform(geom, ...)) in WHERE; transform the constant instead.
- If you don’t need exact polygon coverage, bbox is fastest.

## 6) App-side patterns to keep latency low

- LIMIT + keyset pagination (never OFFSET for large pages). Use `WHERE time_coverage_start > $last` or `profile_id > $last` as appropriate.
- Server-side cursors/streaming results to avoid RAM spikes.
- Sampling: read only N parquet files per answer (e.g., 200–1000), stratified by time/space.
- Pre-aggregation: build materialized views for common counts by (year, 1° grid cell, depth bands). Refresh nightly.
- Don’t join big JSONB unless needed; pull minimal columns first.

## 7) Validate with EXPLAIN ANALYZE

- Always profile slow queries with `EXPLAIN (ANALYZE, BUFFERS)`.
- Look for Seq Scan; if you see it, check predicates and missing indexes.
- Confirm index-only scans (Index Only Scan) for projected columns.

## 8) Step-by-step rollout

1) Apply indexes in `docs/sql/perf_indexes.sql` (CONCURRENTLY).
2) Run ANALYZE and a small CLUSTER-by-time if feasible.
3) Switch app queries to projections (no `*`) + LIMIT + keyset.
4) If still slow for big windows, implement yearly partitioning or Timescale hypertable.
5) Add materialized views for the top 2–3 dashboards/asks.

## Example fast query template

```sql
-- Bounded by time and bbox; projects only needed columns
SELECT profile_id, parquet_path, latitude, longitude, time_coverage_start
FROM profiles
WHERE time_coverage_start BETWEEN $1 AND $2
  AND geom && ST_MakeEnvelope($3, $4, $5, $6, 4326)
  AND ST_Intersects(geom, ST_MakeEnvelope($3, $4, $5, $6, 4326))
ORDER BY time_coverage_start DESC
LIMIT $7;
```

## Example keyset pagination (no OFFSET)

```sql
SELECT profile_id, parquet_path, latitude, longitude, time_coverage_start
FROM profiles
WHERE time_coverage_start < $1 -- last seen timestamp
  AND geom && ST_MakeEnvelope($2, $3, $4, $5, 4326)
ORDER BY time_coverage_start DESC
LIMIT $6;
```
