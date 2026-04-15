# Community Triage

[English](./community-triage.md) · [简体中文](./community-triage.zh-CN.md)

This repository uses GitHub Issues for actionable work items and GitHub Discussions for questions, idea validation, and community knowledge sharing.

## Use GitHub Issues For

- Reproducible bugs and regressions.
- Concrete feature requests with a clear problem statement and expected outcome.
- Scoped documentation defects or operator workflow gaps.
- Release, packaging, CI, or compatibility work that should be tracked to completion.

## Use GitHub Discussions For

- Installation, configuration, publishing, or upgrade questions.
- Early ideas that still need problem framing, API design, or workflow tradeoff discussion.
- Showcase posts, deployment notes, and example digests from real usage.
- General repository process questions that do not point to a specific actionable defect.

## Recommended Discussions Categories

- `Q&A`: usage help, debugging guidance, configuration questions, and operator how-to requests.
- `Ideas`: proposed capabilities, workflow changes, and roadmap exploration before an issue is ready.
- `Show and Tell`: demos, screenshots, deployment stories, and production lessons.
- `General`: governance, contributor workflow, or other community topics that do not fit the categories above.

## Maintainer Triage Rules

- Move usage questions and broad design exploration out of Issues and into Discussions whenever no immediate implementation task exists.
- Ask bug reporters to reproduce against the latest supported release or `main` before deep triage.
- Use the `discussion` label when an issue needs design clarification before it can become implementation work.
- Apply `good first issue` and `help wanted` only after the issue is concrete enough for someone else to pick up.
- Add area labels such as `source`, `extractor`, `publisher`, `docs`, and `operations` after the scope is clear.
- Redirect private vulnerability reports to `SECURITY.md` and GitHub Security Advisories instead of public threads.

## Converting Between The Two

- If a Discussion produces a bounded implementation task, open an Issue and link back to the discussion thread.
- If an Issue turns out to be a support question, early idea, or showcase post, close it with a pointer to the appropriate Discussion category.
- Keep the final actionable decision in the Issue so pull requests, milestones, and release notes still point to one tracked work item.
