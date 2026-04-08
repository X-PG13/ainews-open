# Changelog

All notable changes to this project should be recorded in this file.

## [1.2.1] - 2026-04-09

### Added

- Multi-source feed fixtures for `Jiqizhixin`, `Ars Technica`, `Substack`, and `Yahoo` syndication pages in the pipeline end-to-end suite
- A deterministic partial-error pipeline regression that keeps extraction timeout handling covered without depending on live network behavior

### Changed

- Package version is now `1.2.1`
- Fixture-driven pipeline coverage now spans domestic media, international media, newsletter/blog layouts, and syndication targets in one CI-safe bundle

### Fixed

- Closed issue `#8` by expanding pipeline fixture coverage across more sources while keeping the regression suite deterministic

## [1.2.0] - 2026-04-09

### Added

- A one-screen `Operations` dashboard panel that aggregates `/health`, metrics, recent pipeline runs, source cooldown hotspots, source alerts, and publication failures
- A richer `/admin/operations` payload with runtime summaries for operators and demo assets for the new operations surface
- New source-specific extraction regression fixtures for `Jiqizhixin`, `Ars Technica`, `Substack`, and `Yahoo` syndication targets

### Changed

- Package version is now `1.2.0`
- Content extraction cleanup now covers more Chinese media, English media, blog/newsletter layouts, and syndication-style article pages
- README and public demo assets now show the operator-focused overview and sample operations payload

### Fixed

- Reduced over-cleaning risk on Chinese publisher pages by separating editorial label noise from the first body paragraph
- Improved article body extraction on additional noisy layouts where share widgets, subscribe prompts, and recirculation blocks previously contaminated the output

## [1.1.2] - 2026-04-08

### Changed

- The tag release workflow now explicitly dispatches `Release Artifact Smoke` after publishing the GitHub Release
- Release documentation now reflects that published tags trigger artifact smoke automatically, while manual reruns remain available
- Package version is now `1.1.2`

### Fixed

- Closed the last manual step in the release flow by wiring release publication to post-release artifact validation

## [1.1.1] - 2026-04-08

### Added

- A dedicated `Release Artifact Smoke` workflow that downloads published release assets, verifies checksums, installs both wheel and source archive, and runs minimal CLI plus `/health` smoke checks

### Changed

- Package version is now `1.1.1`
- Release documentation now treats `Release Artifact Smoke` as a mandatory pass gate before a release is considered complete
- PyPI publication is now opt-in by default through `AINEWS_ENABLE_PYPI_PUBLISH=true`, while manual workflow dispatch remains available

### Fixed

- Corrected release artifact checksum verification so the smoke workflow validates the published bundle paths exactly as recorded in `sha256sums.txt`

## [1.1.0] - 2026-04-08

### Added

- Source runtime protections with cooldown state, maintenance mode, alert acknowledgement, snooze controls, and recovery lifecycle automation
- Source operations coverage across API, dashboard, and CLI, including runtime history pruning and cooldown reset commands
- Google News wrapper resolution at ingest time, historical backfill support, and end-to-end coverage for wrapper-to-article extraction flow
- Prometheus-compatible `/metrics` endpoint, monitoring docs, and Docker Compose monitoring profile with Prometheus and Grafana assets
- Scheduled housekeeping workflow for pruning archived source runtime history
- Expanded regression fixtures for Chinese, international, and noise-heavy media pages including TechCrunch, VentureBeat, Reuters, Wired, Google AI Blog, and Google News wrapper samples

### Changed

- Package version is now `1.1.0`
- Smoke workflow now runs on `push` to `main` and on all pull requests so it can be used as a required branch check
- Source extraction retries now classify `throttled`, `blocked`, `temporary_error`, and `permanent_error` states with explicit retry metadata
- `/health`, stats, and runtime views now surface source cooldown and recovery state instead of treating all extraction failures as generic degradation
- Alert delivery now covers degraded health, publication failures, pipeline errors, and source cooldown transitions with deduplication and recovery notices

### Fixed

- Stopped Google News wrapper URLs from polluting deduplication and downstream publication links by resolving canonical targets before ingest
- Prevented repeated extraction pressure on blocked or throttled sources by honoring source cooldowns, maintenance state, and retry windows
- Sanitized API and service error payloads so internal exception details are not exposed to clients
- Reduced false-positive extraction failures by improving source-specific cleanup for blog-style and noisy article layouts

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
