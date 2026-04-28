# Roadmap

[English](./ROADMAP.md) · [简体中文](./ROADMAP.zh-CN.md)

This roadmap tracks current maintainer priorities. Release notes remain the historical record after work ships.

## Current Status

- Stable line: `v1.2.x`
- Latest release: `v1.2.49`
- Current open milestone: `v1.2.50`
- Deferred release-engineering item: trusted PyPI publishing bootstrap and the first package publish

## In Progress: v1.2.50 Maintenance

- Improve release verification and post-release smoke documentation.
- Keep roadmap, support lifecycle, and release notes easier to discover from primary docs entry points.
- Keep release automation, checksum verification, SBOM generation, and provenance attestation healthy as ongoing maintenance.

## Deferred: PyPI

- Configure the PyPI trusted publisher for `ainews-open`.
- Publish the package to PyPI for the first time after the trusted-publisher bootstrap is complete.

## Planned: v1.3 Product Surface

- Ship a public demo site backed by sample digests and API examples.
- Add operator views for operation metrics and failure history.
- Provide deployment recipes for Docker Compose, systemd, and GitHub Actions at production depth.
- Improve multi-channel publishing previews before outbound sends.

## Ongoing Quality Work

- Expand source-specific extraction rules for high-value AI media sites.
- Add regression fixtures for additional Chinese and international publishers.
- Improve digest ranking and editorial curation workflows.
- Support stronger duplicate detection across syndication-heavy feeds.

## Recently Completed

- Enabled GitHub Discussions and documented the issue-vs-discussion triage policy.
- Defined support windows and deprecation policy for the public `v1.x` contract.
- Hardened release artifacts with checksums, SBOMs, provenance, and smoke validation.
- Added maintainer bootstrap guidance for GitHub Pages and PyPI setup.
- Added governance, maintainer, citation, architecture, and review-policy documents to the repository baseline.

## Community And Contributor Experience

- Keep `good first issue`, `help wanted`, `v1.x`, and area labels current as triage metadata.
- Document more worked examples for extending sources, extraction rules, and publishers over time.
- Keep roadmap, milestone, and release documentation aligned so feature requests land against current priorities instead of stale backlog items.

## Related Docs

- [Release Notes](docs/releases/README.md)
- [Support Lifecycle](docs/support-lifecycle.md)
