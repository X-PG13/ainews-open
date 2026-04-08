# PR Review Policy

[English](./pr-review-policy.md) · [简体中文](./pr-review-policy.zh-CN.md)

This repository uses `CODEOWNERS` and branch protection to keep changes reviewable without overcomplicating a single-maintainer workflow.

## Review Baseline

- Open a pull request for any change that touches behavior, contracts, workflows, deployment, or governance files.
- Keep `main` green before merging. The current merge gate is the protected-branch check set on GitHub.
- Use the PR template and fill in validation clearly.
- Resolve review conversations before merging.

## What Reviewers Should Check

- Scope: the PR solves one bounded problem and does not bundle unrelated refactors.
- Behavior: any user-visible or operator-visible change is called out in the summary.
- Safety: no secrets, private endpoints, or internal paths are exposed.
- Contracts: config, CLI, API, export payloads, and schema changes are documented when affected.
- Validation: tests and manual checks match the type of change.

## Review Expectations By Change Type

- Source registry changes: include source rationale and keep source ids stable.
- Extraction logic changes: include or update HTML fixtures and regression tests.
- API or dashboard changes: update both API tests and operator-facing docs.
- Release or workflow changes: update release docs or checklist when the operator flow changes.

## CODEOWNERS Usage

- `CODEOWNERS` assigns default ownership for core code, docs, workflows, and release assets.
- GitHub will suggest the listed owner when a pull request touches those paths.
- In the current single-maintainer setup, `CODEOWNERS` is used for ownership clarity and review routing, not for mandatory code-owner approval, to avoid deadlocking releases.

## Single-Maintainer Rule

- Until there is another maintainer, the repository keeps required status checks and conversation resolution enabled on `main`.
- Review count is intentionally not forced to `1` yet, because a solo maintainer cannot self-satisfy a mandatory review gate under strict branch protection.
- If another maintainer joins, enable code-owner review and at least one approving review in branch protection.
