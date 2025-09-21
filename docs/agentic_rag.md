# Agentic RAG for ARGO Indian Ocean (1999–2012)

This document outlines how we will implement an agentic Retrieval-Augmented Generation (RAG) system that answers questions about ARGO profiles over the Indian Ocean (1999–2012) using the data now stored in Postgres and linked Parquet profile measurements.

## Goals

- Natural language Q&A about ARGO profiles: where/when/what (e.g., salinity trends, temperature-depth structure, counts).
- Tool-using agent that can: (1) query Postgres with geospatial/time filters, (2) load measurement Parquet files, (3) compute stats/plots, and (4) summarize results in plain English.
- Fast, reliable answers with provenance (profile IDs, counts, links to parquet paths).

## Data sources

- Postgres (Aiven): table `profiles` with columns (subset):
  - profile_id (PK), float_id, platform_number, cycle_number
  - profile_time (TEXT), latitude, longitude
  - file_path, parquet_path
  - qc_summary (JSONB), attrs (JSONB)
  - institution, data_source, depth_min, depth_max, time_coverage_start, time_coverage_end, conventions, keywords
  - PostGIS enabled; indexes for latitude/longitude/time/float_id/keywords.
- Parquet measurements: per-profile files with columns like pres, temp, psal, and QC flags.

## Why "Agentic" and not just RAG?

- Most questions are structured (filters by time, region, float, and summarization). A plain vector RAG over text is suboptimal.
- The agent decides which tool(s) to use:
  1) SQL tool for candidate selection (fast filters via Postgres/PostGIS),
  2) Parquet reader tool for numeric analysis,
  3) Optional text/vector retrieval for unstructured metadata (attrs, keywords),
  4) Plotting tool for quick charts.

## High-level architecture

- User → Orchestrator (Agent) → Toolset:
  - SQLRetriever: parameterized SQL over Postgres with safe templates.
  - GeoTimePlanner: extracts geo/time/intents from user prompt.
  - MeasurementsLoader: reads parquet paths returned by SQL and loads psal/temp/pres.
  - Analyzer: computes summary stats (min/max/mean, profiles per area/time), depth slices, time series.
  - Plotter: generates lightweight PNGs (matplotlib) and returns paths or base64 for UI.
  - Optional VectorStore: embeddings over `attrs`/`keywords` for free-form descriptive queries.
- Outputs: textual answer, optional figure, citations (profile count, example profile_ids), and the SQL used.

## Retrieval strategy

- Primary: Structured retrieval via SQL
  - Geospatial: ST_MakeEnvelope bbox, or latitude/longitude ranges. Example:
    SELECT profile_id, latitude, longitude, parquet_path, time_coverage_start
    FROM profiles
    WHERE time_coverage_start BETWEEN $1 AND $2
      AND ST_Within(geom, ST_MakeEnvelope($lon_min, $lat_min, $lon_max, $lat_max, 4326));
- Secondary: Vector search (optional)
  - Build embeddings on (institution, keywords, attrs textualized). Use for questions like "Which missions focused on monsoon season?" to pre-filter profiles/floats.
- Measurement access:
  - Batch read Parquet for a sampled subset (e.g., up to N profiles) to compute stats quickly. Use stratified sampling across time/space to avoid bias.

## Agent plan (reasoning steps)

1) Intent detection: metric (salinity/temp) + scope (area/time/depth/float) + output type (summary/plot/table).
2) Compose a SQL query with parameters (time range, bbox, optional keyword filter, float ids).
3) Fetch candidates (profile_id, parquet_path, metadata). Cap at a configurable limit (e.g., 2000) with sampling strategy.
4) Load parquet for the chosen subset; compute requested statistics or build the requested visualization.
5) Summarize results using an LLM with a concise template, including numeric facts and provenance.
6) Return answer + optional chart + SQL used + counts.

## Tools (contracts)

- SQLRetriever
  - input: {time_range, bbox, depth_hint, keywords?, float_ids?, limit}
  - output: [{profile_id, lat, lon, parquet_path, time_coverage_start, depth_min, depth_max, institution}]
  - errors: DB unavailable, malformed params → return friendly error
- MeasurementsLoader
  - input: list of parquet_path, columns=["pres","temp","psal"], sample_k, depth_bins?
  - output: tidy DataFrame or dict of arrays, with N profiles sampled
  - errors: missing files, IO errors → skip and report count
- Analyzer
  - input: measurement DF + intent (e.g., psal stats by depth bands)
  - output: stats dict (min/max/mean, percentiles), optional groupby (time/depth)
- Plotter
  - input: analyzer output + style
  - output: PNG filepath or base64 string

## Prompting templates (LLM)

- System: "You are an oceanography assistant. Use the tools to get precise numbers. Include numeric ranges, counts, and uncertainty if sampling."
- Planner: "Given the user query, extract metric, area (bbox or region name), time range, depth interest, and whether a plot is requested."
- Answer: "Summarize in 3–6 sentences. Report sample size and any QC caveats."

## Example queries

- "Show average salinity profile (0–1000 m) in the eastern Indian Ocean (90–110E, 10–20S) during 2005."
- "How many ARGO profiles are available near Indonesia in 1999?"
- "Plot temperature vs depth for a random sample of 50 profiles between 200 and 800 m in 2010."

## MVP implementation plan

1) Backend service (FastAPI)
   - /ask endpoint: accepts NL question; returns JSON with answer, figures, and citations.
   - /health, /metrics for observability.
2) Tools
   - SQLRetriever using psycopg/sqlalchemy with safe templates.
   - MeasurementsLoader using pandas.read_parquet; capped sampling; async-friendly.
   - Analyzer and Plotter utilities.
3) Minimal agent
   - Rule-based planner (regex + heuristics) for MVP; swap to LLM planning later.
   - Deterministic templates to ensure reproducibility for common queries.
4) Optional vector store
   - Build embeddings for `attrs/keywords` with a lightweight store (FAISS) if needed.
5) Observability
   - Structured logs: SQL, counts, timing, sample size, errors.
   - Save generated plots under ./outputs/ with timestamped names.

## Deployment

- Config via env vars: PG_URL, MAX_ROWS, SAMPLE_SIZE, OUTPUT_DIR.
- Run as a service behind uvicorn; optional Dockerfile later.
- Security: DO NOT hardcode credentials; use env or secret manager; limit query burst via rate limiting.

## Evaluation

- Unit tests: SQL parameterization; analyzer math; plotting smoke tests.
- Golden answers: canonical results for a fixed area/time; compare stats within tolerance.
- Load test: ensure <2s latency for metadata-only queries, <10s for sampled analysis.

## Risks and mitigations

- Large scans: enforce LIMIT and TILED sampling; paginate.
- Missing parquet files: robust skip+report; ensure ingestion maintains invariants.
- QC flags: surface when data quality may be low; allow filters by QC.

## Roadmap

- v0 (MVP): Rule-based planner → SQL → sample parquet → stats → text answer.
- v1: LLM planner + tool calling; add plots; add vector support for unstructured asks.
- v2: Caching, richer geospatial (polygons), comparative queries (multi-period/regions).

---

### Quick start (local)

- Ensure Postgres URL is set in env:
  - Windows PowerShell:
    $env:PG_URL = "postgresql://<user>:<pass>@<host>:<port>/<db>?sslmode=require"
- Start service (after implementation):
  python app.py  # or uvicorn app:app --reload
- Ask:
  curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"How many profiles near 95–140E, -15 to -5 in 1999?"}'
