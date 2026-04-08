# Use Cases

[English](./use-cases.md) · [简体中文](./use-cases.zh-CN.md)

This page translates the project from "feature list" into actual operating patterns.

## Solo Maintainer Digest

Use this when you want one personal AI digest workflow without extra infrastructure.

Recommended setup:

- local SQLite
- no LLM at first
- `static_site` export for easy review

Recommended commands:

```bash
python -m ainews run-pipeline --since-hours 48 --limit 20 --max-items 20 --persist --export
python -m ainews publish --digest-id 1 --target static_site
```

Why it fits:

- lowest setup cost
- easy to inspect generated artifacts
- no channel credentials required on day one

## Bilingual Editorial Workflow

Use this when a content team needs global AI coverage translated into Chinese for review and publishing.

Recommended setup:

- LLM configured
- admin token enabled
- dashboard as the main operator surface

Recommended commands:

```bash
python -m ainews extract --since-hours 48 --limit 30
python -m ainews enrich --since-hours 48 --limit 30
python -m ainews print-digest --use-llm --persist
```

Why it fits:

- article body extraction gives the LLM stronger context
- digest results can be reviewed before publication
- editorial notes, hide, and pin actions remain available in the console

## Team Broadcast Pipeline

Use this when you need a digest pushed to chat tools every day.

Recommended setup:

- GitHub Actions or a server-side scheduler
- `telegram` and/or `feishu`
- structured logs enabled

Recommended command:

```bash
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --persist --export --publish --target telegram
```

Why it fits:

- one command covers ingest, extraction, enrichment, digest generation, export, and publication
- persisted digests make publication status auditable
- idempotency prevents duplicate publishes for the same digest and target

## WeChat Operator Flow

Use this when your final destination is a WeChat official account.

Recommended setup:

- WeChat app credentials configured
- cover upload configured through `thumb_media_id` or automatic cover upload
- refresh workflow retained for `freepublish/get`

Recommended commands:

```bash
python -m ainews publish --use-llm --persist --target wechat --wechat-submit
python -m ainews refresh-publications --target wechat --limit 20
```

Why it fits:

- draft creation and optional publish submission are handled in one workflow
- publication records remain queryable later
- status refresh lets operators track pending versus final publish state

## Public Demo And Evaluation

Use this when you want to show the project to contributors, users, or stakeholders before wiring real credentials.

Recommended assets:

- [docs/demo/index.html](./demo/index.html)
- [docs/demo/sample-digest.md](./demo/sample-digest.md)
- [docs/demo/sample-digest.en.md](./demo/sample-digest.en.md)
- [docs/demo/sample-health.json](./demo/sample-health.json)
- [docs/demo/sample-publications.json](./demo/sample-publications.json)
