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
- Run `make build` when packaging, entry points, or included assets change.
- Keep CI green on all supported Python versions before merging.

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

## Issues And Security

- Use the GitHub issue templates for bugs and feature requests.
- Do not report vulnerabilities through public issues; follow `SECURITY.md`.
- Replace placeholder contact information in `.github/ISSUE_TEMPLATE/config.yml` before publishing the repository.
