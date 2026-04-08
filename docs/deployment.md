# Deployment Guide

This guide focuses on the fastest path from clone to a working pipeline, then shows how to run AI News Open in Docker, Docker Compose, `systemd`, and GitHub Actions.

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

## Upgrade Checklist

Before upgrading:

1. Back up `data/ainews.db`.
2. Back up `output/` if you treat exported files as durable artifacts.
3. Read [database-migrations.md](./database-migrations.md).
4. Read [CHANGELOG.md](../CHANGELOG.md).
