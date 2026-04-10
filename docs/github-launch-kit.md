# GitHub Launch Kit

This file is the first public-facing copy pack for the GitHub repository and release page.

## Release

### Suggested Tag

`v1.2.41`

### Suggested Title

`AI News Open v1.2.41 · Override Approval and Replay Waiver Coverage`

### Release Notes

```md
## AI News Open v1.2.41

AI News Open `v1.2.41` hardens extraction quality for override-approval-matrix, continuity-revalidation-checklist, and audit-replay-waiver-faq layouts across more developer-doc publishers.

### What it does

- Aggregates AI news from domestic and international RSS/Atom sources
- Cleans and deduplicates articles before storage
- Extracts full article content with source-specific cleanup
- Uses an OpenAI-compatible LLM to translate and summarize international stories into Chinese
- Generates Chinese AI daily digests
- Publishes digests to Telegram, Feishu, static sites, and WeChat draft/publish flows
- Ships with FastAPI, CLI, SQLite storage, and a zero-build admin dashboard

### Engineering baseline

- Unit tests and API smoke tests
- Ruff lint and pre-commit hooks
- GitHub Actions for CI and scheduled digest generation
- Docker packaging and non-root runtime
- Contributing guide, security policy, code of conduct, changelog, and GitHub issue/PR templates
- Compatibility contract, migration docs, deployment guide, and troubleshooting guide

### Highlights in this release

- New deterministic override-approval-matrix, continuity-revalidation-checklist, and audit-replay-waiver-faq fixtures for `OpenAI`, `Anthropic`, and `Together`
- Better cleanup for override approval summaries, continuity revalidation checklist summaries, audit replay waiver summaries, audit replay matrices, and related-guide recirculation on developer policy pages
- The international extraction suite now covers standard articles, live updates, briefing pages, multimedia-heavy pages, opinion layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy/research feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, recovery-exception-matrix layouts, continuity-waiver-faq layouts, audit-restoration-checklist layouts, recovery-override-matrix layouts, continuity-exception-checklist layouts, audit-replay-faq layouts, recovery-override-faq layouts, continuity-revalidation-matrix layouts, audit-replay-checklist layouts, override-escalation-checklist layouts, continuity-revalidation-faq layouts, audit-replay-exception-matrix layouts, override-approval-matrix layouts, continuity-revalidation-checklist layouts, and audit-replay-waiver-faq layouts
- Published-artifact smoke validation still runs automatically after release publication

### Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
cp .env.example .env
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --export
docker compose --profile monitoring up --build
```

Open the dashboard at `http://127.0.0.1:8000/`.

### Release Notes

- Private vulnerability reports are routed through GitHub Security Advisories
- Grafana defaults to `admin / admin` in the local monitoring profile and should be changed before remote exposure
- Repeat publishing for the same stored digest and target is skipped by default
- Use `--force-republish` only when you intentionally want another outbound publish attempt
- Configure your own LLM, Telegram, Feishu, or WeChat credentials in `.env`
- Review generated content before external publishing

### Artifact Verification

```bash
shasum -a 256 -c sha256sums.txt
python -m pip install ainews_open-X.Y.Z-py3-none-any.whl
python -m ainews --help
```
```

## Repository About

### GitHub About Description

Turn domestic and global AI news into a Chinese daily digest workflow with translation, archiving, and publishing built in.

### GitHub About Description Shorter Variant

AI news to Chinese daily digests, with translation and publishing built in.

### Website

If you do not have a project site yet, leave this empty for now.

When you have a deployed static digest site, you can use that URL as the repository website.

## Social Preview Asset

Prepared asset files in this repository:

- `docs/assets/social-preview.png`
- `docs/assets/console-real.png`

GitHub's official documentation describes social preview setup through the repository web UI:

1. Open the repository main page
2. Go to `Settings`
3. Under `Social preview`, click `Edit`
4. Upload `docs/assets/social-preview.png`

Official docs:

- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview

## Topics

Suggested GitHub topics:

`ai-news`
`news-aggregation`
`llm`
`fastapi`
`python`
`rss`
`daily-digest`
`china-tech`
`telegram-bot`
`feishu`
`wechat`
`open-source`

## Project Intro

### Chinese Intro

AI News Open 是一个面向开源发布的 AI 新闻聚合工具。它可以每天自动抓取国内外 AI 新闻，完成清洗、去重、正文提取、国际新闻中文翻译与摘要生成，并进一步产出中文 AI 日报。项目同时提供 CLI、FastAPI API、零构建管理后台，以及 Telegram、飞书、静态站点、微信公众号等发布能力，适合个人维护、内容团队和轻量化 AI 媒体工作流。

### English Intro

AI News Open is an open-source toolkit for daily AI news aggregation across Chinese and international sources. It ingests RSS and Atom feeds, cleans and deduplicates articles, extracts full content, translates global stories into Chinese with an OpenAI-compatible LLM, and generates daily AI digest output. The project includes a CLI, FastAPI service, zero-build admin dashboard, SQLite storage, and multi-channel publishing workflows for Telegram, Feishu, static sites, and WeChat.

## Social Copy

### Short Launch Post

We just open-sourced AI News Open.

It aggregates domestic and international AI news, extracts article content, translates global coverage into Chinese, generates daily AI digests, and can publish to Telegram, Feishu, static sites, and WeChat.

Repo: `https://github.com/X-PG13/ainews-open`

### One-Line Chinese Post

AI News Open 已开源：自动抓取国内外 AI 新闻，做正文提取、国际新闻中文翻译、AI 日报生成和多渠道发布。
