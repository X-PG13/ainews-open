# Support Lifecycle

[English](./support-lifecycle.md) · [简体中文](./support-lifecycle.zh-CN.md)

This document defines the support window and deprecation policy for public AI News Open releases.

## Support States

AI News Open uses three release states for the current stable major line.

- `Active support`: the latest released minor in the current major line. Maintainers accept bug fixes, docs updates, security guidance, and normal compatibility clarifications here.
- `Maintenance support`: the immediately previous minor in the current major line. Maintainers may still help with upgrades, regressions, and security guidance, but backports are best-effort and new fixes should target the latest minor first.
- `Unsupported`: any release older than the immediately previous minor, and all historical `0.x` releases.

## Minor-Release Support Window

Support moves forward one minor at a time.

Example for `v1.x`:

- when `1.2.x` is the newest released minor, `1.2.x` is `Active support`
- `1.1.x` is `Maintenance support`
- `1.0.x` and older are `Unsupported`

When `1.3.0` ships:

- `1.3.x` becomes `Active support`
- `1.2.x` becomes `Maintenance support`
- `1.1.x` and older become `Unsupported`

This keeps the support policy predictable without promising long-lived backport branches for a single-maintainer project.

## What Maintainers Support In Each State

### Active Support

- bug fixes and behavioral regressions
- docs corrections and operator guidance
- security guidance and release follow-up
- compatibility clarifications for public contract changes

### Maintenance Support

- upgrade help to the latest minor
- security guidance
- severe regressions at maintainer discretion

Maintenance support does not guarantee backported fixes. If a fix lands only on the latest minor, the recommended path is to upgrade.

### Unsupported Releases

- historical versions remain visible for reference
- maintainers may still answer questions, but no compatibility guarantee is implied
- new fixes should not target these releases

## Deprecation Policy

Deprecations apply to the public contract defined in [compatibility.md](./compatibility.md), including documented environment variables, CLI flags, HTTP routes, and exported JSON fields.

Rules:

- announce the deprecation in `CHANGELOG.md` in the first release that introduces it
- document the replacement path or migration note in the relevant docs
- keep the deprecated contract accepted for the rest of the current major line when practical
- treat hard removals as major-version work by default

For the current `v1.x` line, the default policy is:

- deprecations may be introduced in a minor release
- deprecated public contract remains supported through the rest of `v1.x` unless a security or safety issue requires earlier action
- removals should wait for `v2.0.0`

## Exception Path

If a deprecated behavior cannot remain in place because of security, safety, or an external platform break:

1. document the reason in `CHANGELOG.md`
2. publish migration notes or fallback behavior
3. keep a compatibility bridge when practical
4. call out the operational impact in release notes before the old behavior is disabled

## Related Docs

- [SUPPORT.md](../SUPPORT.md)
- [Compatibility Contract](./compatibility.md)
- [Roadmap](../ROADMAP.md)
- [Release Notes](./releases/README.md)
- [Release Checklist](./release-checklist.md)
