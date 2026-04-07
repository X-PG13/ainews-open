# Changelog

All notable changes to this project should be recorded in this file.

## [1.0.0] - 2026-04-07

### Added

- Stable `v1.x` compatibility contract covering environment variables, CLI flags, HTTP endpoints, export JSON, and migration policy
- Deployment, migration, and troubleshooting docs for local runs, Docker, `systemd`, and GitHub Actions
- Source registry contract test for the default source pack
- Legacy SQLite migration coverage with explicit `schema_version` metadata

### Changed

- Package version is now `1.0.0`
- Exported digest payloads now include a top-level `schema_version`
- `publish` and `run-pipeline --publish` now persist digests before publication so publication history and idempotency are enforced
- Re-publishing the same stored digest to the same target is skipped by default unless `--force-republish` or `force_republish=true` is used
- `/health` now returns the running service version

### Fixed

- Prevented duplicate publication rows and accidental repeat outbound publishes for the same digest and target in the default operator flow

## [0.6.0] - 2026-04-07

### Added

- Open-source project governance files: Code of Conduct, Security Policy, issue templates, and pull request template
- Engineering tooling: `.editorconfig`, `.pre-commit-config.yaml`, `ruff` configuration, package build target, and expanded CI checks
- Docker packaging hygiene with `.dockerignore` and non-root container runtime
- Publication history filtering and WeChat publish-status refresh from the admin API, CLI, and dashboard

### Changed

- CI now runs lint, tests, and package builds on Python 3.9 and 3.12
- Makefile now exposes `lint`, `build`, and `check` targets

## [0.5.0] - 2026-04-07

### Added

- WeChat `freepublish/get` status refresh and publication history UI
- Feishu card fallback, WeChat thumb auto-upload, and publication record persistence

## [0.4.0] - 2026-04-07

### Added

- Content extraction cleanup for `36Kr` and `IT之家`
- Publish targets for Telegram, Feishu, WeChat, and static site export
