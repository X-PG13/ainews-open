# Compatibility Contract

This document defines the compatibility surface AI News Open intends to keep stable for `v1.x`.

## Scope

Starting with `v1.0.0`, the project treats the following as stable public contract:

- Environment variable names in [.env.example](../.env.example)
- CLI command names and documented flags in [src/ainews/cli.py](../src/ainews/cli.py)
- HTTP endpoints in [src/ainews/api.py](../src/ainews/api.py)
- Exported digest JSON shape produced by `run-pipeline --export` and `publish --export`
- SQLite schema migration path managed by [src/ainews/repository.py](../src/ainews/repository.py)

## Compatibility Rules

- Additive changes are allowed in `v1.x`.
- Renaming or removing environment variables, CLI flags, HTTP routes, or exported JSON fields is treated as a breaking change.
- Breaking changes must wait for `v2.0.0` or ship with an explicit compatibility bridge and migration notes.
- Exported JSON keeps a top-level `schema_version` field so downstream consumers can pin behavior.

## Stable Environment Variables

The variables listed in [.env.example](../.env.example) are the supported configuration contract.

Rules:

- Existing variable names remain valid for the whole `v1.x` line.
- New variables may be added.
- Default values may become safer, but semantics of existing variables should not invert silently.

## Stable CLI Surface

The following commands are the intended stable CLI surface for `v1.x`:

- `ingest`
- `list-sources`
- `extract`
- `enrich`
- `print-digest`
- `list-digests`
- `publish`
- `list-publications`
- `refresh-publications`
- `run-pipeline`
- `stats`
- `serve`

Rules:

- Existing command names stay valid.
- Existing documented flags stay valid.
- New flags may be added when they are backward compatible.
- `publish` and `run-pipeline --publish` persist a digest before publication so idempotency can be enforced.
- Re-publishing the same stored digest to the same target is skipped by default.
- Use `--force-republish` when you intentionally want another outbound publish attempt.

## Stable HTTP API Surface

The following routes are the intended stable HTTP surface for `v1.x`:

- `GET /health`
- `GET /sources`
- `POST /ingest`
- `GET /articles`
- `GET /digest/daily`
- `GET /admin/stats`
- `GET /admin/articles`
- `POST /admin/ingest`
- `POST /admin/enrich`
- `POST /admin/extract`
- `POST /admin/digests/generate`
- `POST /admin/pipeline`
- `POST /admin/publish`
- `GET /admin/digests`
- `GET /admin/publications`
- `POST /admin/publications/refresh`
- `PATCH /admin/articles/{article_id}`

Rules:

- Existing routes remain available for `v1.x`.
- Existing request fields remain accepted.
- Existing response fields remain available.
- New response fields may be added.

## Stable Export JSON Surface

The exported digest JSON keeps these top-level fields:

- `schema_version`
- `region`
- `since_hours`
- `total_articles`
- `counts_by_region`
- `articles`
- `digest`
- `body_markdown`
- `generation_mode`
- `stored_digest` when persistence is enabled

The `digest` object keeps these fields:

- `title`
- `overview`
- `highlights`
- `sections`
- `closing`
- `provider`
- `model`

The `articles` list keeps these fields as stable downstream contract:

- `id`
- `source_id`
- `source_name`
- `title`
- `url`
- `published_at`
- `region`
- `language`
- `display_title_zh`
- `display_summary_zh`
- `display_brief_zh`
- `compact_summary_zh`
- `is_translated`
- `content_available`

## Publishing Idempotency Contract

Publication behavior is part of the `v1.x` contract:

- A stored digest plus target pair is idempotent by default.
- When the latest record for the same `digest_id + target` is `ok` or `pending`, the next publish call returns `skipped`.
- A skipped duplicate publish does not create a new publication row.
- `--force-republish` and `force_republish=true` bypass this guard intentionally.

This contract prevents duplicate records and repeated outbound publishes in the normal operator path.

## Breaking Change Process

When a future change must break contract:

1. Document it in [CHANGELOG.md](../CHANGELOG.md).
2. Add migration notes.
3. Keep the old behavior during a deprecation window when practical.
4. Only remove the old contract in the next major version.
