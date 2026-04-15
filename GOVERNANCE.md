# Governance

## Scope

This document defines how AI News Open makes decisions about code, documentation, releases, and community operations.

## Current Model

The repository currently operates with a single-maintainer model.

- `CODEOWNERS` defines the default owner for each area.
- Pull requests are the default path for behavior, contract, deployment, workflow, and governance changes.
- Protected-branch checks, CI, and release workflows provide the baseline change-control system.

This model optimizes for shipping velocity without dropping reviewability.

## Decision Rules

- Routine fixes, documentation updates, and source registry maintenance can be merged by the active maintainer once validation is complete.
- Behavior changes that affect CLI output, API payloads, database schema, publishing targets, or release automation must include tests and docs updates in the same change.
- Breaking changes must be called out in `CHANGELOG.md`, release notes, and any impacted operator documentation before release.
- Security-sensitive issues follow `SECURITY.md` and should not be discussed in public issues before a fix and disclosure plan exists.
- Governance, support, and review-process changes should be proposed through a pull request so the rationale is visible in-repo.

## Maintainer Responsibilities

Active maintainers are expected to:

- keep CI, release, and packaging workflows passing;
- triage issues and pull requests on a best-effort basis;
- preserve documented compatibility and release expectations;
- review security reports and coordinate fixes privately;
- keep `README.md`, `CONTRIBUTING.md`, `SUPPORT.md`, and release notes aligned with reality.

## Adding Maintainers

New maintainers should meet all of the following:

- sustained, high-quality contribution history across multiple changesets;
- demonstrated familiarity with release, support, and security expectations;
- willingness to review changes outside their original contribution area;
- ability to keep project metadata and public communication accurate.

When a maintainer is added, update all of the following together:

- `MAINTAINERS.md`
- `.github/CODEOWNERS`
- protected-branch review settings
- package and repository metadata if needed

## Decision Escalation

When there is disagreement:

1. Prefer the most reversible option.
2. Prefer documented contracts over ad hoc precedent.
3. Prefer smaller scoped changes over bundled refactors.
4. The active maintainer makes the final merge decision for unresolved disputes.

## Community Signals

The repository should keep these project-health signals current:

- support boundaries in `SUPPORT.md`
- security intake in `SECURITY.md`
- contribution expectations in `CONTRIBUTING.md`
- ownership routing in `.github/CODEOWNERS`
- release history in `CHANGELOG.md` and `docs/releases/`
