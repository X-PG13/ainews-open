# Support

## Supported Versions

| Version line | Status | Notes |
| --- | --- | --- |
| `1.x` latest minor | Active support | Receives bug fixes, docs updates, and security guidance. |
| `1.x` immediately previous minor | Maintenance support | Upgrade to the latest `1.x`; backports are best-effort and severe regressions are handled case by case. |
| Older `1.x` minors | Unsupported | Historical releases only. |
| `0.x` | Unsupported | Historical releases only. |

See `docs/support-lifecycle.md` for the full minor-release support window and deprecation policy.

## Where To Ask For Help

- Bugs: open a GitHub issue with the bug template.
- Security: use GitHub Security Advisories, not public issues.
- Feature requests: use the feature request template once the request is concrete enough to track as implementation work.
- Usage questions, early ideas, showcase posts, and design discussion: use GitHub Discussions. See `docs/community-triage.md` for the issue-vs-discussion split.

## Discussions Categories

- `Q&A`: installation, configuration, publishing, and upgrade help.
- `Ideas`: early feature or workflow proposals that still need scope and tradeoff discussion.
- `Show and Tell`: demos, deployment notes, and sample output from real usage.
- `General`: community process and repository topics that do not fit the categories above.

## Maintainer Expectations

- Reproduce reported bugs against the latest release or `main`.
- Ask for logs with `X-Request-ID`, health payload, and publication status when the report involves operations.
- Close stale reports that cannot be reproduced after an upgrade path has been provided.

## Support Boundaries

- Maintainers do not guarantee custom feed stability for third-party websites that remove RSS or block extraction.
- External platform outages for Telegram, Feishu, WeChat, or LLM providers are treated as dependency incidents, not repository defects by default.
- Production deployments should pin a release, not `main`.
