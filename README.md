<div align="center">
  <h1>AI News Open</h1>
  <p><strong>Open-source workflow for aggregating AI news, translating global coverage into Chinese, and publishing daily digests across channels.</strong></p>
  <p><a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a></p>
  <p>
    <a href="https://github.com/X-PG13/ainews-open/actions/workflows/ci.yml"><img src="https://github.com/X-PG13/ainews-open/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <a href="https://github.com/X-PG13/ainews-open/releases"><img src="https://img.shields.io/github/v/release/X-PG13/ainews-open" alt="Release" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/X-PG13/ainews-open" alt="License" /></a>
    <a href="pyproject.toml"><img src="https://img.shields.io/badge/python-3.9%2B-3776AB" alt="Python" /></a>
  </p>
  <p>
    <a href="https://github.com/X-PG13/ainews-open">Repository</a> ·
    <a href="https://github.com/X-PG13/ainews-open/releases">Releases</a> ·
    <a href="docs/github-launch-kit.md">Launch Kit</a> ·
    <a href="docs/demo/index.html">Demo</a>
  </p>
</div>

![AI News Open Real Console Screenshot](docs/assets/console-real.png)
![AI News Open Operations Overview](docs/assets/operations-panel-preview.svg)

## Product Snapshot

AI News Open is an open-source AI news stack built for maintainers, content teams, and operators who need more than a toy feed reader. It turns scattered domestic and international AI sources into one workflow: ingest, clean up, deduplicate, extract article bodies, translate global stories into Chinese, generate daily digests, archive them, and publish them across channels.

## Why It Exists

- Aggregate domestic and international AI news without paying for a commercial news API.
- Translate global AI coverage into Chinese titles, summaries, and "why it matters" notes.
- Ship one stack that includes CLI, FastAPI, a zero-build admin console, and publishing targets.
- Meet open-source engineering expectations with tests, CI, lint, Docker, issue templates, and security policy.

## What You Ship

| Layer | Included |
| --- | --- |
| Sources | Domestic and international RSS/Atom source registry |
| Processing | Cleanup, deduplication, extraction, enrichment, digest generation |
| Interfaces | CLI, FastAPI API, zero-build admin dashboard |
| Publishing | Telegram, Feishu, static site, WeChat draft/publish |
| Engineering | Tests, lint, pre-commit, CI, Docker, changelog, security policy |

## Use Cases

- Run your own AI news digest as an individual maintainer.
- Build a Chinese editorial workflow for international AI news.
- Support a lightweight AI media product or internal intelligence feed.
- Push daily digests to Telegram, Feishu, a static site, or a WeChat official account.

## 60-Second Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
cp .env.example .env
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --persist --export
python -m ainews serve --port 8000
```

After startup you can:

- Open the admin console at `http://127.0.0.1:8000/`
- Use the Operations panel to inspect `/health`, recent pipeline runs, source cooldowns, source alerts, and publication failures in one screen
- Browse the article pool, digest archive, publication history, and WeChat publish status
- Trigger ingest, extraction, translation, digest generation, and publishing from the dashboard

## Public Demo

- Sample demo page: [docs/demo/index.html](docs/demo/index.html)
- Sample digest markdown (ZH): [docs/demo/sample-digest.md](docs/demo/sample-digest.md)
- Sample digest markdown (EN): [docs/demo/sample-digest.en.md](docs/demo/sample-digest.en.md)
- Sample digest JSON: [docs/demo/sample-digest.json](docs/demo/sample-digest.json)
- Sample health payload: [docs/demo/sample-health.json](docs/demo/sample-health.json)
- Sample operations payload: [docs/demo/sample-operations.json](docs/demo/sample-operations.json)
- Sample publication history: [docs/demo/sample-publications.json](docs/demo/sample-publications.json)

## Maintainer Flow

```bash
python -m pip install -e ".[dev]"
pre-commit install
make check
make coverage
make smoke
```

## Operator Docs

- [Compatibility Contract](docs/compatibility.md)
- [Configuration Matrix](docs/configuration.md)
- [First Deploy Guide](docs/first-deploy.md)
- [Deployment Guide](docs/deployment.md)
- [Database Migrations](docs/database-migrations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Monitoring](docs/monitoring.md)
- [PR Review Policy](docs/pr-review-policy.md)
- [Release Artifacts](docs/release-artifacts.md)
- [Use Cases](docs/use-cases.md)
- [Contributor Playbook](docs/contributor-playbook.md)
- [Release Checklist](docs/release-checklist.md)
- [Support Policy](SUPPORT.md)
- [Roadmap](ROADMAP.md)

## What You Get

The current version includes:

- A domestic and international AI source registry with Chinese sites, global media, and official blogs
- RSS/Atom ingestion, basic cleanup, deduplicated persistence
- Article body extraction, source-specific cleanup, and local storage
- LLM-powered translation and summary enrichment for international stories
- Chinese daily digest generation and digest history
- A publication layer for Telegram, Feishu, a static site, and WeChat draft publishing
- Feishu card messages and automatic WeChat cover upload
- Publication history management and WeChat publish-status refresh
- A `FastAPI` HTTP API
- A zero-build admin console
- CLI commands for ingest, extraction, enrichment, digest generation, publication, and full pipeline execution
- SQLite storage
- Unit tests, API smoke tests, Dockerfile, CI workflows
- `ruff`, coverage, `pre-commit`, issue/PR templates, Security, and Code of Conduct

The default sources were verified as reachable on `2026-04-07`, including:

- Chinese: `36Kr`, `TMTPost`, `IT之家`, `Google News CN AI`
- Global: `OpenAI News`, `Google AI Blog`, `Google DeepMind Blog`, `Hugging Face Blog`, `TechCrunch AI`, `The Verge AI`, `VentureBeat AI`, `Google News Global AI`

## Why It Is Designed This Way

This version optimizes for four practical constraints:

1. No paid news API dependency. Everything starts from public RSS or Atom feeds.
2. Easy extensibility. All default sources live in `src/ainews/sources.default.json`.
3. International stories can be extracted first and then translated into Chinese titles, summaries, and "why it matters" notes through a configurable LLM.
4. The same project can run as a service, a CLI task, a dashboard-backed tool, or a scheduled workflow on a server, in Docker, or in GitHub Actions.

## Project Layout

```text
src/ainews/
  api.py               FastAPI entrypoint
  cli.py               CLI entrypoint
  config.py            Environment variables and settings
  content_extractor.py Article body extraction
  feed_parser.py       RSS / Atom parsing
  http.py              HTTP fetching helpers
  llm.py               OpenAI-compatible LLM client
  models.py            Data models
  publisher.py         Digest publishing layer
  repository.py        SQLite storage
  service.py           Ingest and aggregation service
  web/                 Admin console
  sources.default.json Default source registry
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
cp .env.example .env
python -m ainews ingest
python -m ainews extract --since-hours 48 --limit 20
python -m ainews stats
python -m ainews print-digest --region all --limit 20
python -m ainews publish --use-llm --persist --export --target static_site
python -m ainews serve --port 8000
```

If you are maintaining or publicly shipping the repository, also run:

```bash
python -m pip install -e ".[dev]"
pre-commit install
make check
```

Open the console at:

```text
http://127.0.0.1:8000/
```

If you prefer to start the API directly:

```bash
uvicorn ainews.api:create_app --factory --host 0.0.0.0 --port 8000
```

If you prefer to run it in containers:

```bash
docker compose up --build
```

If you want Prometheus and Grafana alongside the API:

```bash
docker compose --profile monitoring up --build
```

If your local `pip` is recent enough and you want editable installs:

```bash
python -m pip install -e ".[dev]"
```

## Open-Source Engineering Baseline

This repository already includes the expected open-source project baseline:

- Community docs: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`
- Collaboration templates: GitHub issue templates, pull request template, `CODEOWNERS`, and review policy
- Quality gates: `ruff`, unit tests, coverage, package build validation, `pre-commit`
- Automation: CI, tag-based release workflow, CodeQL, Dependabot
- Release verification: published artifact checksum and install smoke workflow
- Packaging and runtime: non-root Docker runtime, `HEALTHCHECK`, `compose.yaml`, `.dockerignore`, `.editorconfig`
- Supply chain: release checksums, CycloneDX SBOM, build provenance, PyPI trusted publishing workflow
- Observability: Prometheus-compatible `/metrics`, source runtime history, housekeeping workflow, and ready-to-run monitoring profile
- Demo assets: sample site content, GitHub Pages workflow, sample digest markdown and JSON output

Before publishing the repository, still confirm two things:

1. Your private security reporting channel is configured in GitHub Security Advisories.
2. The organization name, repository URLs, and maintainer metadata in `README.md` and `pyproject.toml` match your real public values.

If you are preparing a GitHub launch, you can reuse:

- `docs/github-launch-kit.md`
- `docs/project-intro.md`

Recommended community scaffolding:

- `ROADMAP.md`
- `SUPPORT.md`
- `.github/labels.yml`

## LLM Translation and Digest Generation

If you want international stories translated into Chinese and daily digests generated by an LLM, configure an OpenAI-compatible endpoint in `.env`:

```env
AINEWS_LLM_PROVIDER=openai_compatible
AINEWS_LLM_BASE_URL=your-compatible-endpoint
AINEWS_LLM_API_KEY=your-key
AINEWS_LLM_MODEL=your-model
```

Then run:

```bash
python -m ainews extract --since-hours 48 --limit 20
python -m ainews enrich --since-hours 48 --limit 20
python -m ainews print-digest --region all --limit 20 --use-llm --persist
```

Notes:

- `extract` fetches article bodies for downstream translation and summarization.
- `enrich` only targets international stories and fills Chinese title, summary, and importance fields.
- `print-digest --use-llm` prefers translated content to generate a Chinese daily digest.
- If no LLM is configured, the system falls back to a rule-based digest template so the workflow remains available.

If you want the full pipeline in one command:

```bash
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --persist --export
```

That pipeline executes:

1. Ingest the latest stories
2. Extract article bodies
3. Translate international stories
4. Generate a digest
5. Export `output/*.md` and `output/*.json`

To publish as part of the same pipeline:

```bash
python -m ainews run-pipeline \
  --since-hours 48 \
  --limit 30 \
  --max-items 30 \
  --use-llm \
  --persist \
  --export \
  --publish \
  --target static_site
```

Notes:

- `publish` and `run-pipeline --publish` automatically persist the digest so publication status can be refreshed later and idempotency can work.
- Publishing the same stored `digest` to the same `target` returns `skipped` by default and does not create duplicate publication records.
- If you intentionally want to publish again, add `--force-republish`.

## Content Extraction and Source-Specific Cleanup

The content extractor ships with two layers:

- Generic article detection that prefers containers such as `article`, `main`, `entry-content`, and `post-content`
- Source-specific cleanup rules that currently prioritize the real article body for `36Kr` and `IT之家`, while dropping recommendation panels, share widgets, breadcrumbs, comments, and other site noise

Even if `beautifulsoup4` is not installed, the project falls back to a standard-library parser and still applies source-specific extraction rules for `36Kr` and `IT之家`.

## Publishing Layer

The current release supports four publication targets:

- `telegram`: send text digests through the Bot API
- `feishu`: send digests through a custom webhook, with `text` and `interactive` card modes
- `wechat`: create drafts in a WeChat official account and optionally submit them for publication; supports automatic cover upload to produce `thumb_media_id`
- `static_site`: generate a zero-dependency static page and `latest.json`

Examples:

```bash
python -m ainews publish --use-llm --target telegram
python -m ainews publish --use-llm --target feishu --target static_site
python -m ainews publish --use-llm --target wechat --wechat-submit
python -m ainews publish --digest-id 1 --target static_site --force-republish
```

If `--target` is omitted, the system reads `AINEWS_PUBLISH_TARGETS`.

### Feishu Cards

If you want cards instead of plain text by default:

```env
AINEWS_FEISHU_MESSAGE_TYPE=card
```

The implementation tries `interactive` cards first and falls back to `text` automatically if the card send fails.

### Automatic WeChat Cover Upload

If you do not want to prepare a `thumb_media_id` manually, provide a cover image source instead:

```env
AINEWS_WECHAT_APP_ID=your-app-id
AINEWS_WECHAT_APP_SECRET=your-app-secret
AINEWS_WECHAT_THUMB_IMAGE_PATH=assets/wechat-cover.jpg
# or
AINEWS_WECHAT_THUMB_IMAGE_URL=https://example.com/wechat-cover.jpg
AINEWS_WECHAT_THUMB_UPLOAD_TYPE=thumb
```

Notes:

- `thumb` mode uses the permanent material upload API with `type=thumb`, which is better suited for cover images. Per the official constraint, the image must be `JPG` and under `64KB`.
- If you already have a media asset, you can still set `AINEWS_WECHAT_THUMB_MEDIA_ID` directly.
- The current implementation only uploads the cover asset automatically. It does not yet rewrite external image links inside the article body.

### WeChat Publication Status Refresh

If you use `--wechat-submit` or `AINEWS_WECHAT_PUBLISH_AFTER_DRAFT=true`, the system stores submitted publication records and lets you refresh the final publication state later.

Use:

```bash
python -m ainews list-publications --target wechat --limit 20
python -m ainews refresh-publications --target wechat --limit 20
```

The current implementation maps the official `freepublish/get` status into:

- `pending`: still being published
- `ok`: publication succeeded
- `error`: originality validation failure, generic failure, review rejection, deletion after publication, or account restriction

## Admin Console

The root path `/` provides an out-of-the-box admin page that supports:

- News ingest
- Batch translation for international stories
- Batch article body extraction
- Digest generation and review
- Target selection and one-click publishing
- Publication history with manual WeChat refresh
- Digest history
- Manual curation such as pinning, hiding, and editorial notes

If you want simple protection for admin routes, set:

```env
AINEWS_ADMIN_TOKEN=your-secret-token
```

The frontend will automatically send `X-Admin-Token` to the admin API.

## CLI

```bash
python -m ainews ingest
python -m ainews extract --limit 20
python -m ainews enrich --limit 20
python -m ainews print-digest --use-llm --persist
python -m ainews run-pipeline --use-llm --persist --export
python -m ainews publish --use-llm --persist --target static_site
python -m ainews publish --digest-id 1 --target static_site --force-republish
python -m ainews list-digests --limit 10
python -m ainews list-publications --limit 20
python -m ainews refresh-publications --target wechat --limit 20
python -m ainews stats
python -m ainews serve --port 8000
```

## API

### `GET /health`

Health check. Returns `status`, current service `version`, database checks, and `schema_version`.

### `GET /sources`

List enabled sources.

### `POST /ingest`

Trigger one ingest run.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/ingest?source_id=36kr-ai&source_id=openai-news"
```

### `GET /articles`

List stored articles.

Example:

```bash
curl "http://127.0.0.1:8000/articles?region=domestic&since_hours=24&limit=20"
```

### `GET /digest/daily`

Return the aggregated digest view. This route is read-only by default. If `use_llm=true` is added, it will try to generate a digest through the currently configured LLM.

Example:

```bash
curl "http://127.0.0.1:8000/digest/daily?region=all&since_hours=24&limit=30"
```

### `GET /admin/stats`

Return article, enrichment, digest archive, and LLM configuration statistics.

### `POST /admin/enrich`

Batch-translate international stories.

```bash
curl -X POST "http://127.0.0.1:8000/admin/enrich" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-token" \
  -d '{"since_hours":48,"limit":20}'
```

### `POST /admin/extract`

Batch-extract article bodies.

```bash
curl -X POST "http://127.0.0.1:8000/admin/extract" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-token" \
  -d '{"since_hours":48,"limit":20}'
```

### `POST /admin/digests/generate`

Generate and optionally persist a Chinese daily digest.

```bash
curl -X POST "http://127.0.0.1:8000/admin/digests/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-token" \
  -d '{"region":"all","since_hours":48,"limit":20,"use_llm":true,"persist":true}'
```

### `PATCH /admin/articles/{id}`

Apply manual curation such as hide, pin, or editorial note.

### `POST /admin/pipeline`

Run ingest, extraction, enrichment, digest generation, export, and optionally publication in one call.

### `POST /admin/publish`

Build or load a digest and publish it to configured targets.

```bash
curl -X POST "http://127.0.0.1:8000/admin/publish" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-token" \
  -d '{"targets":["static_site","telegram"],"use_llm":true,"persist":true,"export":true,"force_republish":false}'
```

### `GET /admin/publications`

View recent publication records, including target platform, status, external ID, and response summary.

Optional query parameters:

- `digest_id`
- `target`
- `status`

### `POST /admin/publications/refresh`

Refresh publication state for platforms that support polling. This is currently used mainly for WeChat `freepublish/get`.

```bash
curl -X POST "http://127.0.0.1:8000/admin/publications/refresh" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-token" \
  -d '{"target":"wechat","limit":20,"only_pending":true}'
```

## Configuration

See `.env.example` for a concrete sample.

- `AINEWS_DATABASE_URL`: SQLite database location
- `AINEWS_SOURCES_FILE`: source registry file
- `AINEWS_HOME`: working directory root, defaults to the current command directory
- `AINEWS_OUTPUT_DIR`: exported digest directory
- `AINEWS_STATIC_SITE_DIR`: static site output directory
- `AINEWS_STATIC_SITE_BASE_URL`: optional external base URL for the static site
- `AINEWS_REQUEST_TIMEOUT`: fetch timeout in seconds
- `AINEWS_DEFAULT_LOOKBACK_HOURS`: default lookback window
- `AINEWS_MAX_ARTICLES_PER_SOURCE`: default per-source ingest cap
- `AINEWS_ALLOWED_ORIGINS`: API CORS allowlist
- `AINEWS_ADMIN_TOKEN`: optional admin API token
- `AINEWS_LOG_LEVEL`: log level, typically `INFO` or `DEBUG`
- `AINEWS_LOG_FORMAT`: `text` or `json`
- `AINEWS_EXTRACTION_TEXT_LIMIT`: maximum number of locally stored characters per extracted article
- `AINEWS_LLM_ARTICLE_CONTEXT_CHARS`: maximum number of article-body characters sent to the LLM
- `AINEWS_LLM_PROVIDER`: defaults to `openai_compatible`
- `AINEWS_LLM_BASE_URL`: LLM base URL
- `AINEWS_LLM_API_KEY`: LLM API key
- `AINEWS_LLM_MODEL`: LLM model name
- `AINEWS_LLM_TIMEOUT`: LLM timeout
- `AINEWS_LLM_TEMPERATURE`: temperature for translation and digest generation
- `AINEWS_LLM_DIGEST_MAX_ARTICLES`: maximum number of articles used for digest generation
- `AINEWS_PUBLISH_TARGETS`: default publish targets, comma-separated, for example `telegram,static_site`
- `AINEWS_TELEGRAM_BOT_TOKEN`: Telegram bot token
- `AINEWS_TELEGRAM_CHAT_ID`: Telegram chat ID or channel name
- `AINEWS_TELEGRAM_DISABLE_NOTIFICATION`: Telegram silent delivery toggle
- `AINEWS_FEISHU_WEBHOOK`: Feishu custom bot webhook
- `AINEWS_FEISHU_SECRET`: optional Feishu signing secret
- `AINEWS_FEISHU_MESSAGE_TYPE`: `text` or `card`
- `AINEWS_WECHAT_ACCESS_TOKEN`: optional fixed WeChat access token
- `AINEWS_WECHAT_APP_ID`: AppID used for access token retrieval
- `AINEWS_WECHAT_APP_SECRET`: AppSecret used for access token retrieval
- `AINEWS_WECHAT_THUMB_MEDIA_ID`: WeChat cover material ID, required for draft creation unless you upload one automatically
- `AINEWS_WECHAT_THUMB_IMAGE_PATH`: local cover image path, can replace `AINEWS_WECHAT_THUMB_MEDIA_ID`
- `AINEWS_WECHAT_THUMB_IMAGE_URL`: remote cover image URL, can replace `AINEWS_WECHAT_THUMB_MEDIA_ID`
- `AINEWS_WECHAT_THUMB_UPLOAD_TYPE`: upload type for the cover, default `thumb`
- `AINEWS_WECHAT_AUTHOR`: WeChat article author name
- `AINEWS_WECHAT_CONTENT_SOURCE_URL`: optional "Read more" URL in the WeChat article
- `AINEWS_WECHAT_NEED_OPEN_COMMENT`: whether comments are enabled
- `AINEWS_WECHAT_ONLY_FANS_CAN_COMMENT`: whether only followers can comment
- `AINEWS_WECHAT_PUBLISH_AFTER_DRAFT`: whether to submit the draft for publication automatically

## v1.0 Contract Notes

- Exported JSON includes top-level `schema_version`
- `publish` and `run-pipeline --publish` are idempotent by default on the tuple `(stored digest, target)`
- Database upgrades follow [Database Migrations](docs/database-migrations.md); the current schema version is `3`
- Public compatibility guarantees are documented in [Compatibility Contract](docs/compatibility.md)

## How to Keep Improving the Project

The repository already has a solid open-source skeleton, but if you want to push further toward production use, these are the next four upgrades:

1. Add source health checks, retries, and ingest monitoring.
2. Add permissions and multi-user editing logs to the admin console.
3. Add more source-specific extraction rules beyond the current generic DOM strategy.
4. Add more publishing targets or deeper platform support, such as richer Telegram formatting, automatic inline image upload for WeChat, and more publication polling.

The repository already includes one scheduled workflow example:

- [daily-digest.yml](.github/workflows/daily-digest.yml)

It runs `run-pipeline` every day and uploads the generated digest files as workflow artifacts.

## Testing

```bash
python -m unittest discover -s tests -v
```

## License

MIT. See `LICENSE`.
