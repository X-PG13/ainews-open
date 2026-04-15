# Contributing

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
pre-commit install
make check
```

## Quality Gates

- Run `make lint` before opening a pull request.
- Run `make test` for behavior changes.
- Run `make check` before merging behavior, contract, release, or workflow changes. It is the local maintainer gate and includes lint, coverage, build, and smoke.
- Run `make coverage` separately only when you need to iterate on coverage failures without re-running the full local gate.
- Run `make build` when packaging, entry points, or included assets change.
- Run `make sbom` when supply chain or release files change.
- Keep CI green on all supported Python versions before merging.

## Contributor Playbook

- Add feeds in `src/ainews/sources.default.json` and keep source ids stable.
- Add extraction fixtures under `tests/fixtures/extraction/` when site-specific cleanup is needed.
- Route new publish targets through `src/ainews/publisher.py`, CLI, API, and docs together.
- Use [docs/contributor-playbook.md](docs/contributor-playbook.md) for step-by-step extension guidance.

## Source Changes

- Add or disable feeds in `src/ainews/sources.default.json`.
- Keep source ids stable once published.
- Prefer public RSS or Atom feeds over brittle HTML scraping.

## Frontend

- The dashboard is plain static assets under `src/ainews/web/`.
- Keep it zero-build unless there is a strong reason to add a frontend toolchain.
- Any new admin action should be exposed in both API and dashboard.

## Content Extraction

- Prefer improving extraction heuristics in `src/ainews/content_extractor.py` over adding source-specific one-off hacks.
- Keep extraction resilient when article pages return incomplete HTML or extra site chrome.

## Pull Requests

- Include tests for parser, filtering, storage, enrichment, or digest changes.
- Keep source configuration changes documented in `README.md`.
- Do not remove existing sources without documenting the reason.
- Use the pull request template and summarize validation clearly.
- Prefer existing labels such as `good first issue`, `help wanted`, `source`, `extractor`, and `publisher`.
- Follow `docs/pr-review-policy.md` for review scope and single-maintainer rules.
- Check `CODEOWNERS` before moving code across ownership boundaries.

## Issues And Security

- Use GitHub issues for reproducible bugs, scoped documentation defects, and concrete feature work.
- Use GitHub Discussions for usage questions, early ideas, deployment notes, and design exploration that is not yet implementation-ready.
- Start with `docs/community-triage.md` and `SUPPORT.md` if you are not sure which channel fits.
- Do not report vulnerabilities through public issues; follow `SECURITY.md`.
- Private vulnerability reports should go through the GitHub Security Advisory channel configured in `.github/ISSUE_TEMPLATE/config.yml`.
