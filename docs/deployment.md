# Deployment Guide

[English](./deployment.md) · [简体中文](./deployment.zh-CN.md)

This guide focuses on the fastest path from clone to a working pipeline, then shows how to run AI News Open in Docker, Docker Compose, `systemd`, and GitHub Actions.

If you want the shortest onboarding path first, read [first-deploy.md](./first-deploy.md).

For a variable-by-variable breakdown, see [configuration.md](./configuration.md).

## 15-Minute Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
cp .env.example .env
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --export
python -m ainews serve --port 8000
```

Open `http://127.0.0.1:8000/`.

What this gives you:

- local SQLite database under `data/`
- exported digest files under `output/`
- admin console on port `8000`

If you want Chinese LLM summaries, set:

```env
AINEWS_LLM_BASE_URL=...
AINEWS_LLM_API_KEY=...
AINEWS_LLM_MODEL=...
```

Then rerun:

```bash
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --export
```

## Docker

Build:

```bash
docker build -t ainews-open:latest .
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/output:/app/output" \
  --env-file .env \
  ainews-open:latest
```

If you want a one-shot pipeline in Docker:

```bash
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/output:/app/output" \
  --env-file .env \
  ainews-open:latest \
  python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --export
```

The image now includes:

- a built-in `HEALTHCHECK` against `http://127.0.0.1:8000/health`
- JSON log output by default inside containers

## Docker Compose

The repository includes [compose.yaml](../compose.yaml).

Start the service:

```bash
docker compose up --build
```

Stop it:

```bash
docker compose down
```

Compose mounts:

- `./data` to `/app/data`
- `./output` to `/app/output`

## systemd

Example unit:

```ini
[Unit]
Description=AI News Open API
After=network.target

[Service]
WorkingDirectory=/srv/ainews-open
Environment=AINEWS_HOME=/srv/ainews-open
ExecStart=/srv/ainews-open/.venv/bin/python -m ainews serve --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
User=ainews
Group=ainews

[Install]
WantedBy=multi-user.target
```

Reload and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ainews-open
sudo systemctl status ainews-open
```

For scheduled digests, use a timer or cron to run:

```bash
/srv/ainews-open/.venv/bin/python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --export --publish
```

## GitHub Actions

The repository already includes [daily-digest.yml](../.github/workflows/daily-digest.yml).

Use it when:

- you want scheduled digest generation
- you are comfortable storing credentials in GitHub repository secrets
- exporting artifacts is enough for your current workflow

The repository also includes:

- [ci.yml](../.github/workflows/ci.yml) for matrix test, coverage, and build checks
- [smoke.yml](../.github/workflows/smoke.yml) for install-and-health smoke validation
- [release.yml](../.github/workflows/release.yml) for tag-based release builds, checksums, SBOM, and provenance
- [pypi-publish.yml](../.github/workflows/pypi-publish.yml) for trusted PyPI publishing
- [demo-pages.yml](../.github/workflows/demo-pages.yml) for publishing the sample demo to GitHub Pages
- [codeql.yml](../.github/workflows/codeql.yml) for security analysis
- [.github/dependabot.yml](../.github/dependabot.yml) for dependency update PRs

Release maintainers should also configure:

- a `pypi` environment with PyPI trusted publishing enabled
- GitHub Pages if the demo site should be public

Recommended secrets:

- `AINEWS_LLM_BASE_URL`
- `AINEWS_LLM_API_KEY`
- `AINEWS_LLM_MODEL`
- `AINEWS_TELEGRAM_BOT_TOKEN`
- `AINEWS_TELEGRAM_CHAT_ID`
- `AINEWS_FEISHU_WEBHOOK`
- `AINEWS_WECHAT_APP_ID`
- `AINEWS_WECHAT_APP_SECRET`

## Data Directories

Default paths:

- database: `data/ainews.db`
- digest export: `output/`
- static site export: `output/site/`

Mount or back up these paths in any real deployment.

## Extraction Retry Policy

Production operators should treat extraction retry state as part of normal operations.

Automatic behavior:

- `pending` articles are eligible for the normal extraction queue
- `throttled` articles re-enter the queue after backoff
- `temporary_error` articles re-enter the queue after backoff
- `blocked` articles are delayed much more aggressively
- `permanent_error` articles do not re-enter the queue automatically

The admin API exposes queue filters on `/admin/articles`:

- `extraction_status`
- `extraction_error_category`
- `due_only`

Manual retry options:

```bash
python -m ainews retry-extractions --status throttled --due-only --limit 20
```

```bash
python -m ainews retry-extractions --status blocked --limit 5
```

```bash
curl -X POST http://127.0.0.1:8000/admin/extract/retry \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-token" \
  -d '{"extraction_status":"throttled","due_only":true,"limit":20}'
```

Recommended operator loop:

1. Inspect `/health` and `/admin/operations`.
2. Filter `/admin/articles` for retry-due extraction failures.
3. Retry only the due subset first.
4. Retry `blocked` or `permanent_error` items manually after reviewing the source behavior.

## Source Cooldown Policy

Extraction retries now also have a source-level protection layer.

When the same source hits consecutive protective failures such as:

- `429`
- `403`
- anti-bot challenge pages

AI News Open can put the source into a cooldown window. During that cooldown:

- queued articles from that source are skipped by the default extraction queue
- `/health` reports `source_cooldowns_active`
- `/admin/sources` and the console show the affected source and cooldown deadline

Manual reset examples:

```bash
python -m ainews reset-source-cooldowns --source venturebeat
```

```bash
python -m ainews reset-source-cooldowns --all
```

Relevant environment variables:

- `AINEWS_SOURCE_COOLDOWN_FAILURE_THRESHOLD`
- `AINEWS_SOURCE_THROTTLE_COOLDOWN_MINUTES`
- `AINEWS_SOURCE_BLOCKED_COOLDOWN_MINUTES`

## Upgrade Checklist

Before upgrading:

1. Back up `data/ainews.db`.
2. Back up `output/` if you treat exported files as durable artifacts.
3. Read [database-migrations.md](./database-migrations.md).
4. Read [CHANGELOG.md](../CHANGELOG.md).
