# Support

## Supported Versions

| Version line | Status | Notes |
| --- | --- | --- |
| `1.x` latest minor | Supported | Receives bug fixes, docs updates, and security guidance. |
| Older `1.x` minors | Best effort | Upgrade to the latest `1.x` before opening support requests. |
| `0.x` | Unsupported | Historical releases only. |

## Where To Ask For Help

- Bugs: open a GitHub issue with the bug template.
- Security: use GitHub Security Advisories, not public issues.
- Feature requests: use the feature request template.
- Usage questions and design discussion: GitHub Discussions is the preferred destination once enabled for the repository.

## Maintainer Expectations

- Reproduce reported bugs against the latest release or `main`.
- Ask for logs with `X-Request-ID`, health payload, and publication status when the report involves operations.
- Close stale reports that cannot be reproduced after an upgrade path has been provided.

## Support Boundaries

- Maintainers do not guarantee custom feed stability for third-party websites that remove RSS or block extraction.
- External platform outages for Telegram, Feishu, WeChat, or LLM providers are treated as dependency incidents, not repository defects by default.
- Production deployments should pin a release, not `main`.
