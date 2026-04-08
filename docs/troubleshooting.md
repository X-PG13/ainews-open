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

## Extraction retries do not happen immediately

This is usually expected behavior.

AI News Open now classifies extraction failures into:

- `throttled`
- `blocked`
- `temporary_error`
- `permanent_error`

Default retry behavior:

- `throttled`: retried automatically after a backoff window
- `temporary_error`: retried automatically after a shorter backoff window
- `blocked`: not retried frequently; intended for anti-bot or access-control cases
- `permanent_error`: not retried automatically

Use these checks:

- `python -m ainews stats`
- `curl http://127.0.0.1:8000/health`
- `curl -H "X-Admin-Token: your-secret-token" "http://127.0.0.1:8000/admin/articles?extraction_status=throttled&due_only=true"`

Manual retry examples:

```bash
python -m ainews retry-extractions --status throttled --due-only --limit 20
```

```bash
python -m ainews retry-extractions --status blocked --limit 5
```

API example:

```json
{
  "extraction_status": "throttled",
  "due_only": true,
  "limit": 20
}
```

POST it to `/admin/extract/retry` with `X-Admin-Token`.

## A source stops getting extracted and `/health` shows `source_cooldowns_active`

This means the source-level protection logic has cooled down a publisher after consecutive
`429`, `403`, or challenge-style extraction failures.

Checks:

- `python -m ainews list-sources --runtime`
- `curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/sources`
- `curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/source-alerts`
- inspect `cooldown_status`, `cooldown_until`, `consecutive_failures`, and `last_http_status`
- inspect the latest source-level alert and recovery entries to confirm whether the cooldown alert already fired
- inspect `silenced_until`, `maintenance_mode`, `acknowledged_at`, and `ack_note` before assuming alert delivery is broken

If the source is safe to resume, clear the cooldown:

```bash
python -m ainews reset-source-cooldowns --source venturebeat
```

Or clear all active cooldowns:

```bash
python -m ainews reset-source-cooldowns --all
```

API:

```json
{"source_ids": ["venturebeat"], "active_only": false}
```

POST it to `/admin/sources/cooldowns/reset` with `X-Admin-Token`.

## Alerts do not fire, or they seem too noisy

First checks:

- confirm `AINEWS_ALERT_TARGETS` is set to `telegram`, `feishu`, or both
- confirm the alert-specific destination is configured
- Telegram alerts need `AINEWS_TELEGRAM_BOT_TOKEN` plus either `AINEWS_ALERT_TELEGRAM_CHAT_ID` or `AINEWS_TELEGRAM_CHAT_ID`
- Feishu alerts need either `AINEWS_ALERT_FEISHU_WEBHOOK` or `AINEWS_FEISHU_WEBHOOK`

Expected behavior:

- repeated active failures are deduped by alert rule and fingerprint
- the resend window is controlled by `AINEWS_ALERT_COOLDOWN_MINUTES`
- when the condition clears, AI News Open sends a recovery notification

If you expect a new alert and did not receive one:

- check whether the fingerprint actually changed
- inspect `/health` and `/admin/operations` to confirm the system is still in the failing state
- inspect logs for `alert.target_error`

If alerts feel too noisy:

- increase `AINEWS_ALERT_COOLDOWN_MINUTES`
- separate publish targets from alert targets by using the `AINEWS_ALERT_*` overrides
- use `/admin/sources` to inspect which source is repeatedly driving cooldowns or blocked failures
- use `/admin/source-alerts` to verify whether the same source is repeatedly entering and leaving cooldown
- acknowledge the active source alert if the team already owns the incident
- snooze the source temporarily when you expect short-lived rate limits
- move the source into maintenance mode when you want the extraction queue and source alerts to pause together
- if a snooze expires and the source is still unhealthy, expect a fresh active alert on the next runtime dispatch
- if old source runtime history is making the SQLite file noisy, archive and prune it with `prune-source-runtime-history`

CLI examples:

```bash
python -m ainews ack-source-alerts --source venturebeat --note "owned by on-call"
python -m ainews snooze-source-alerts --source venturebeat --minutes 120
python -m ainews set-source-maintenance --source venturebeat
python -m ainews set-source-maintenance --source venturebeat --disable
python -m ainews prune-source-runtime-history --retention-days 45
```

## LLM digest generation does not happen

Checks:

- verify `AINEWS_LLM_BASE_URL`
- verify `AINEWS_LLM_API_KEY`
- verify `AINEWS_LLM_MODEL`
- rerun with `--use-llm`

Behavior:

- if the LLM is not configured or errors out, the service falls back to a rule-based digest
- this is expected behavior, not a crash

## Google News articles show `skipped` during extraction

This is expected for `news.google.com` aggregator shell pages.

- Google News RSS links often resolve to a Google wrapper page, not the publisher article body
- AI News Open now marks these as `skipped` instead of `error`
- they are excluded from default extraction retries and do not degrade `/health`

If you need the full body, use the original publisher URL instead of the Google News wrapper URL.

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
- inspect `/admin/articles` with `extraction_status`, `extraction_error_category`, and `due_only` filters for the retry queue

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
