# Maintainers

## Active Maintainers

| Handle | Role | Responsibilities |
| --- | --- | --- |
| `@X-PG13` | Lead maintainer | Core application, release management, docs, workflows, issue triage, and security coordination |

## Maintainer Expectations

Active maintainers should:

- review pull requests for correctness, scope, and release impact;
- keep issue labels, templates, and roadmap signals usable for contributors;
- verify release artifacts before tagging or publishing;
- update governance and support documents when process expectations change.

## Ownership Notes

- Path-level ownership lives in `.github/CODEOWNERS`.
- Security reporting flow lives in `SECURITY.md`.
- User support boundaries live in `SUPPORT.md`.
- PR review expectations live in `docs/pr-review-policy.md`.

## Succession Checklist

If ownership changes, update these files and settings in the same change:

- `MAINTAINERS.md`
- `GOVERNANCE.md`
- `.github/CODEOWNERS`
- `pyproject.toml` maintainer metadata
- repository branch protection and release credentials
