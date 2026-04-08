# First Deploy Guide

[English](./first-deploy.md) · [简体中文](./first-deploy.zh-CN.md)

This guide is the shortest path from clone to a usable deployment. It is intentionally opinionated and optimized for first-time operators.

## Goal

Reach a state where:

- the API responds on `/health`
- the admin console opens in the browser
- one pipeline run writes digest files into `output/`
- you know which environment variables are actually required for your scenario

## 10-Minute Local Operator Path

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
cp .env.example .env
python -m ainews run-pipeline --since-hours 48 --limit 20 --max-items 20 --export
python -m ainews serve --port 8000
```

Then open:

```text
http://127.0.0.1:8000/
```

You should now have:

- a local database in `data/ainews.db`
- exported digest files in `output/`
- a running admin console and API on port `8000`

## Minimum Config Profiles

### Local evaluation

Only copy `.env.example` and keep defaults.

### LLM-enabled digest generation

Add:

```env
AINEWS_LLM_BASE_URL=...
AINEWS_LLM_API_KEY=...
AINEWS_LLM_MODEL=...
```

### Telegram publishing

Add:

```env
AINEWS_PUBLISH_TARGETS=telegram
AINEWS_TELEGRAM_BOT_TOKEN=...
AINEWS_TELEGRAM_CHAT_ID=...
```

### Feishu publishing

Add:

```env
AINEWS_PUBLISH_TARGETS=feishu
AINEWS_FEISHU_WEBHOOK=...
```

### WeChat publishing

Add at minimum:

```env
AINEWS_PUBLISH_TARGETS=wechat
AINEWS_WECHAT_APP_ID=...
AINEWS_WECHAT_APP_SECRET=...
AINEWS_WECHAT_THUMB_MEDIA_ID=...
```

## First Hosted Deployment Checklist

Before pointing real users at the service:

1. Set `AINEWS_ADMIN_TOKEN`.
2. Set `AINEWS_LOG_FORMAT=json`.
3. Mount `data/` and `output/` onto durable storage.
4. Confirm `/health` returns `ready: true`.
5. Run one manual `run-pipeline` before enabling schedules.
6. Verify one publish target end to end before enabling multiple channels.

## Recommended First Commands After Boot

```bash
python -m ainews list-sources
python -m ainews stats
python -m ainews run-pipeline --since-hours 48 --limit 20 --max-items 20 --export
python -m ainews publish --target static_site --persist --export
```

## If Something Fails

- Read [troubleshooting.md](./troubleshooting.md)
- Check [configuration.md](./configuration.md)
- Use `X-Request-ID` from API responses when inspecting logs

## Next Step

After your first successful deploy, move to:

- [deployment.md](./deployment.md) for Docker, Compose, `systemd`, and GitHub Actions
- [use-cases.md](./use-cases.md) for recommended operating patterns
