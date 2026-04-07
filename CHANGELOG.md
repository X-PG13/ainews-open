# Changelog

All notable changes to this project should be recorded in this file.

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
