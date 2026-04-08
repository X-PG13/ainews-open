# Release Checklist

[English](./release-checklist.md) · [简体中文](./release-checklist.zh-CN.md)

Use this checklist before cutting a new public release.

## Before Tagging

1. Read `CHANGELOG.md` and add the new release notes file under `docs/releases/`.
2. Confirm `README.md` and `README.zh-CN.md` still point to valid docs and demo assets.
3. Run:

```bash
make check
make smoke
```

4. Confirm `docker compose config -q` passes with `.env.example`.
5. Confirm open code scanning alerts are `0`.
6. Confirm the demo page still renders and sample assets exist under `docs/demo/`.

## Versioning

1. Update the version in `pyproject.toml`.
2. Update the version in `src/ainews/__init__.py`.
3. Add the release section to `CHANGELOG.md`.
4. Add or update `docs/releases/vX.Y.Z.md`.

## Release Automation Readiness

Confirm:

- GitHub Actions `CI` is green
- GitHub Actions `CodeQL` is green
- `release.yml` is present and current
- `pypi-publish.yml` is present if PyPI publication is intended
- required repository secrets are configured

## GitHub Release

1. Create and push the tag:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

2. Verify the GitHub Release includes:

- built distributions
- `sha256sums.txt`
- SBOM artifact
- provenance attestation
- final release notes

## After Release

1. Verify the release page and demo page are still reachable.
2. Confirm the package metadata on GitHub and PyPI looks correct.
3. Confirm `Latest` points to the intended tag.
4. Announce the release using `docs/releases/` copy if applicable.
