# Troubleshooting

This page lists the most common operator failures for AI News Open.

## The pipeline runs but there are no articles

Checks:

- Run `python -m ainews list-sources` and confirm the source list loads.
- Run `python -m ainews ingest` and inspect per-source status.
- Check your outbound network access.
- Check whether the source was filtered out by `include_keywords` or `exclude_keywords`.

## Content extraction says "extracted article text is too short"

Meaning:

- the feed item exists
- the article page was reachable
- the extractor could not find enough real article body

What to do:

- inspect the raw article page
- add or tune a site-specific selector in [content_extractor.py](../src/ainews/content_extractor.py)
- add a regression fixture and test before shipping the selector change

## LLM digest generation does not happen

Checks:

- verify `AINEWS_LLM_BASE_URL`
- verify `AINEWS_LLM_API_KEY`
- verify `AINEWS_LLM_MODEL`
- rerun with `--use-llm`

Behavior:

- if the LLM is not configured or errors out, the service falls back to a rule-based digest
- this is expected behavior, not a crash

## Publish returns `skipped`

Meaning:

- the same stored digest was already published to the same target
- the latest publication record for that `digest_id + target` is `ok` or `pending`

This is the default idempotency guard.

If you intentionally want another outbound publish:

```bash
python -m ainews publish --digest-id 1 --target static_site --force-republish
```

Or through the API send:

```json
{"digest_id": 1, "targets": ["static_site"], "force_republish": true}
```

## WeChat publish fails before draft creation

Common causes:

- no `AINEWS_WECHAT_ACCESS_TOKEN`
- missing `AINEWS_WECHAT_APP_ID` or `AINEWS_WECHAT_APP_SECRET`
- invalid `AINEWS_WECHAT_THUMB_MEDIA_ID`
- invalid `AINEWS_WECHAT_THUMB_IMAGE_PATH`
- thumb upload uses a non-JPG file or a file larger than `64KB`

## Static site files are missing

Checks:

- confirm `AINEWS_OUTPUT_DIR`
- confirm `AINEWS_STATIC_SITE_DIR`
- rerun with `--export` or target `static_site`
- check write permissions on the output directories

## I need better operational traceability

Checks:

- set `AINEWS_LOG_LEVEL=INFO` or `DEBUG`
- set `AINEWS_LOG_FORMAT=json` for container or log pipeline deployments
- look for `X-Request-ID` in API responses and match it to request logs
- inspect `/health` for `ready`, `degraded_reasons`, recent operation timings, and failure categories
- inspect `/admin/operations` for the last tracked `ingest`, `extract`, `enrich`, `digest`, `publish`, and `pipeline` runs

## Health is `degraded`

Meaning:

- the service is still responding
- the database and sources are available
- one or more operator-visible failure categories were observed

Typical degraded reasons:

- `article_extraction_errors`
- `llm_enrichment_errors`
- `publication_errors`
- `recent_pipeline_errors`

Start with:

- `python -m ainews stats`
- `curl http://127.0.0.1:8000/health`
- `curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/operations`

## Contributors or GitHub stats look wrong

Checks:

- confirm commit email matches a verified GitHub email
- wait for GitHub contributor stats to finish recomputing after force-push or history rewrite

## How to verify database migration state

Run:

```bash
python -m ainews stats
```

Or:

```bash
curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/stats
```

Check for:

- `schema_version`
- article counts
- digest counts
- publication counts
