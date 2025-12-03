# Agentic RAG for ARGO Oceanographic Data

## Vision
Unlock ARGO float observations with an agentic Retrieval-Augmented Generation platform that combines a geospatially aware PostgreSQL foundation, semantic search via pgvector, and FastAPI-powered multi-agent reasoning. Researchers, students, and developers get a single interface to ask oceanographic questions, retrieve curated data, and receive analytical narratives with maps, charts, and citations.

## Conceptual Architecture
- **Data & Storage**: PostgreSQL 16.10 on Aiven with PostGIS, pgvector, and pg_trgm extensions; ingestion pipelines normalize 240k+ ARGO profiles, enrich metadata, and pre-compute quality scores.
- **Vector & Retrieval Fabric**: OpenAI `text-embedding-ada-002` vectors stored in pgvector enable mixed keyword/semantic search across profiles, metadata, and derived summaries.
- **Agentic Backend**: FastAPI service hosts authentication, routing, and specialized agents (retrieval, analysis, visualization) that collaborate via tool APIs to satisfy complex questions.
- **User Interface**: Next.js frontend (in `frontend/argo-frontend`) delivers chat-style interactions, dashboards, and download workflows tailored to researcher personas.

## Repository Map
```
agrodata/
  IMPLEMENTATION_PLAN.md      # 26-step master plan with status
  README.md                   # High-level idea, progress, roadmap

  backend/                    # FastAPI + agent orchestration
    api/                      # Route definitions, schemas, tests
    agents/                   # Agent logic, tool coordination
    tools/                    # Retrieval, analysis, viz toolkits
    database/                 # Schemas, migrations, connections

  helpers/                    # Data setup & ingestion utilities
  config/                     # Environment-specific settings
  docs/                       # Architecture + SQL references
  frontend/argo-frontend/     # Next.js UI scaffold
  gadr/                       # Raw ARGO datasets (gitignored)
```

## Implementation Progress
| Step | Scope | Status | Highlights |
| --- | --- | --- | --- |
| 1 | Database setup & vector extensions | ✅ Complete | PostgreSQL + PostGIS + pgvector stack provisioned; 240,773 profiles loaded with geospatial indexes |
| 2 | Core database schema optimization | ✅ Complete | Comprehensive normalized schema, generated columns, audit logging, documented in `backend/database/SCHEMA_DOCUMENTATION.md` |
| 3 | Ingestion update for new schema | ✅ Complete | Enhanced ingestion (`helpers/extractor/test_ultra_fast_enhanced.py`) adds quality scoring, basin tagging, metadata extraction |
| 4 | Safe schema migration rollout | ✅ Complete | `backend/database/migrations/001_comprehensive_migration.sql` applied; auth, analytics, and embedding tables live |
| 5 | Vector embedding infrastructure | ✅ Complete | Batch + refresh jobs in `helpers/extractor/` and `vectorization/production_embeddings.py` populate pgvector with OpenAI `ada-002` embeddings |
| 6 | FastAPI backend service setup | ✅ Complete | Modular API in `backend/api` + `agents/api` exposes `/ask`, `/profiles`, `/health`, `/metrics` with middleware, pooling, and test coverage |
| 8 | RAG/NLP query processing | 🟡 In progress | Early intent classification + retrieval chaining wired via `backend/agents` and `tools/retrieval/`; natural-language responses flowing but tuning remains |

**Progress summary**: Foundation plus core runtime (vector search, FastAPI backend, Next.js UI) are operational. NLP/agent behavior is partially tuned, while advanced auth, analytics, and visualization phases are upcoming.

## Current Capabilities
- **Backend API**: FastAPI modular service (`backend/run_modular_api.py`) handles authenticated requests, query routing, and health/metrics endpoints.
- **Vector search**: pgvector-backed semantic search spans metadata, summaries, and measurements thanks to the embedding pipelines in `tools/vectorization/`.
- **Agent/NLP loop**: Retrieval + analysis agents can answer many oceanographic prompts; intent parsing and response synthesis live in `backend/agents`.
- **Frontend UI**: Next.js client (`frontend/argo-frontend`) offers chat, map, and dataset views already connected to the backend endpoints.

## Upcoming Milestones
1. Finish Step 8 tuning: improve query intent detection, disambiguation, and fallback behavior; expand evaluation coverage.
2. Deliver Step 7 authentication layer: JWT + refresh tokens, API keys, and tiered permissions integrated with the existing middleware skeleton.
3. Advance Steps 9–10: strengthen analysis/viz agents, add dedicated visualization outputs, and wire download/export flows.
4. Harden observability/performance stack (Steps 12–13) once the above layers stabilize.

## Additional References
- Detailed blueprint: `IMPLEMENTATION_PLAN.md`
- Schema documentation: `backend/database/SCHEMA_DOCUMENTATION.md`
- SQL helper scripts: `docs/sql/*.sql`
- Frontend starter: `frontend/argo-frontend/README.md`
