# Contributor Playbook

## Add A News Source

1. Update `src/ainews/sources.default.json`.
2. Keep `id` stable and descriptive.
3. Prefer RSS or Atom before adding brittle HTML collection paths.
4. Add or update tests that cover parsing, filtering, and ingestion behavior.
5. Document noteworthy source behavior in `README.md` when it affects operators.

## Add Or Refine Extraction Rules

1. Start in `src/ainews/content_extractor.py`.
2. Add fixture HTML under `tests/fixtures/extraction/` when site-specific cleanup is needed.
3. Keep generic heuristics intact unless the regression suite proves the change is safe.
4. Strip navigation, recommendations, share bars, and site chrome before storing body text.
5. Add a focused test that proves the cleaned text is closer to article body than raw page text.

## Add A Publish Target

1. Implement target handling in `src/ainews/publisher.py`.
2. Route the target through CLI, API, and dashboard affordances when it is operator-facing.
3. Persist enough response metadata to support refresh, idempotency, and troubleshooting.
4. Add tests for success, platform error, and missing credential cases.
5. Document required configuration variables in `docs/configuration.md` and `README.md`.

## Validate Before Opening A PR

- `make lint`
- `make test`
- `make coverage`
- `make build`

If packaging or supply chain files changed, also run `make sbom`.
