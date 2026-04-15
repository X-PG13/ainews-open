# Architecture Overview

## System Shape

AI News Open is a layered Python application with one shared SQLite data store and three operator-facing surfaces:

- CLI for scheduled and local workflows
- FastAPI for automation and admin APIs
- Zero-build web console for operational control

The same service layer drives all three so behavior stays consistent across entrypoints.

## End-To-End Flow

1. Source definitions are loaded from `src/ainews/sources.default.json` or an override file.
2. Feed items are fetched and parsed into normalized `ArticleRecord` objects.
3. URLs, titles, and content-derived signals are used to deduplicate and group cross-source variants.
4. Article bodies are extracted and optionally enriched through an OpenAI-compatible LLM.
5. A digest payload is built, optionally frozen into an editable snapshot, and persisted.
6. The publishing layer renders that payload into channel-specific formats and records publication history.

## Core Modules

| Path | Responsibility |
| --- | --- |
| `src/ainews/cli.py` | CLI entrypoint and command routing |
| `src/ainews/api.py` | FastAPI app and admin/public HTTP routes |
| `src/ainews/service.py` | Application orchestration, business rules, and workflow composition |
| `src/ainews/repository.py` | SQLite schema, persistence, deduplication, and query layer |
| `src/ainews/content_extractor.py` | Article body extraction and source cleanup heuristics |
| `src/ainews/publisher.py` | Channel rendering and outbound publishing adapters |
| `src/ainews/llm.py` | OpenAI-compatible enrichment and digest generation client |
| `src/ainews/telemetry.py` / `metrics.py` | Runtime history, counters, and monitoring surfaces |
| `src/ainews/web/` | Static admin console assets |

## Data Boundaries

- `articles` are the operational source of truth for ingest, extraction, enrichment, and editorial curation.
- `digests` store persisted snapshot payloads that can be served again without recomputing a fresh digest.
- `digest_snapshot_versions` tracks editor history and rollback points for stored digests.
- `publications` is append-only history for outbound delivery attempts and status refreshes.

## Important Invariants

- Duplicate clustering should be stable across replayed or historical feeds; it must not depend on the wall clock alone.
- Admin actions exposed in the dashboard should map to API routes and service-layer methods together.
- Publication records must preserve the digest snapshot version they were created from.
- Public error payloads must stay sanitized even when internal exceptions contain sensitive details.

## Extension Points

- Add or disable feeds in `src/ainews/sources.default.json`.
- Improve extraction behavior in `src/ainews/content_extractor.py` with fixture-backed tests.
- Add publish targets in `src/ainews/publisher.py`, then wire CLI, API, and docs in the same change.
- Extend operator views through `src/ainews/api.py` and `src/ainews/web/` without introducing a frontend build step unless there is a strong reason.

## Operational Design Choices

- SQLite is the default persistence layer to keep local and single-node deployment simple.
- Static frontend assets keep the admin surface easy to inspect, patch, and ship.
- OpenAI-compatible LLM configuration keeps the enrichment layer provider-flexible.
- Docker, Compose, monitoring assets, and release workflows are shipped in-repo so operators can audit the full path to production.
