# Security Policy

## Supported Versions

Only the latest released minor version is considered actively supported for security fixes.
The immediately previous minor may receive security guidance, but fixes should
target the latest minor first unless the maintainer explicitly decides to
backport a severe issue.

## Reporting A Vulnerability

Do not open a public issue for security-sensitive bugs.

Report vulnerabilities privately with:

- Affected version or commit
- Impact summary
- Reproduction steps
- Proof-of-concept if available
- Suggested mitigation if known

If you are operating this project in production, rotate any leaked API keys or admin tokens immediately before reporting.

Preferred reporting channel for this repository:

- GitHub Security Advisories: `https://github.com/X-PG13/ainews-open/security/advisories/new`

If a dedicated security mailbox is added later, it can be listed here as a secondary contact path.

## Private Disclosure Expectations

Keep security reports private until a fix and disclosure plan are agreed.

- Do not post exploit details, credentials, private logs, or proof-of-concept payloads in public issues, pull requests, discussions, or release comments.
- Share only the minimum reproduction details needed for maintainers to confirm impact.
- Redact API keys, admin tokens, webhook secrets, database paths, and production hostnames before attaching logs.
- If a report affects a third-party platform, coordinate disclosure with that platform before making the issue public.

Maintainers may move a public report into a private advisory and redact public
comments if a vulnerability is accidentally disclosed in the open.

## Maintainer Triage Flow

Use this flow for incoming security reports:

1. Acknowledge receipt privately and keep discussion in the GitHub Security Advisory thread.
2. Confirm the affected version, deployment mode, credentials involved, and whether the issue is reproducible on `main`.
3. Classify impact and severity:
   - `Critical`: unauthenticated remote code execution, credential exfiltration, or default-token bypass.
   - `High`: authenticated privilege escalation, stored secret exposure, or broad data disclosure.
   - `Medium`: denial of service, limited data exposure, or bypass that requires unusual deployment choices.
   - `Low`: hardening gaps, misleading errors, or issues with minimal practical impact.
4. Decide whether the fix can be developed publicly without exposing exploit details. Use a private advisory branch when public work would reveal the vulnerability.
5. Record the expected fix vehicle: patch release, documentation advisory, configuration mitigation, or no-code clarification.
6. Keep the reporter updated when the impact assessment, fix plan, or disclosure timeline changes.

## Fix And Release Checklist

For confirmed vulnerabilities:

1. Write the smallest safe fix and include a regression test when practical.
2. Run `make check PYTHON=./.venv-dev/bin/python`.
3. Update `CHANGELOG.md` and release notes with user-facing impact and mitigation details that do not include exploit instructions.
4. Prepare a patch release from a maintainer-authored branch.
5. Publish the GitHub Release and confirm release assets, checksums, SBOM, and release artifact smoke checks.
6. Update the GitHub Security Advisory with affected versions, patched version, impact, workaround, and credits if the reporter wants attribution.
7. Close or convert any related public issue only after the patched release is available.

If an immediate code fix is not available, publish a mitigation advisory that
documents safe configuration changes, credential rotation, or feature disablement
steps.

## Public Disclosure

Public disclosure should happen after the patched release or mitigation advisory
is available.

- Keep exploit payloads and secret values out of release notes.
- Credit reporters only with explicit permission.
- If the issue has no practical impact, document the reasoning in the advisory and close it without a release.

## Response Expectations

Maintainers should aim to:

- Acknowledge valid reports within 3 business days
- Provide an initial impact assessment within 7 business days
- Coordinate a fix and disclosure timeline before public discussion
