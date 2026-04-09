# Release Checklist

[English](./release-checklist.md) · [简体中文](./release-checklist.zh-CN.md)

Use this checklist before cutting a new public release.

## Before Tagging

1. Read `CHANGELOG.md` and add the new release notes file under `docs/releases/`.
2. Confirm `README.md` and `README.zh-CN.md` still point to valid docs and demo assets.
3. Confirm `docs/release-artifacts.md` still matches the current release bundle shape.
4. Run:

```bash
make check
```

`make check` now includes the local smoke check, so a separate `make smoke` rerun is only needed when you are debugging startup behavior by itself.

5. Confirm `docker compose config -q` passes with the current compose profile.
6. Confirm open code scanning alerts are `0`.
7. Confirm the demo page still renders and sample assets exist under `docs/demo/`.

## Versioning

1. Update the version in `pyproject.toml`.
2. Update the version in `src/ainews/__init__.py`.
3. Add the release section to `CHANGELOG.md`.
4. Add or update `docs/releases/vX.Y.Z.md`.

## Release Automation Readiness

Confirm:

- GitHub Actions `CI` is green
- GitHub Actions `CodeQL` is green
- GitHub Actions `Release Artifact Smoke` is green for the last published tag
- `release.yml` is present and current
- `pypi-publish.yml` is present if PyPI publication is intended
- required repository secrets are configured

Release is not considered complete until `Release Artifact Smoke` passes for the published tag.
The standard release flow now dispatches that smoke workflow automatically after publishing the GitHub Release.

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
- artifact install and checksum verification guidance

3. Verify the release artifact instructions still work:

```bash
python -m pip install ainews_open-X.Y.Z-py3-none-any.whl
python -m ainews --help
```

## After Release

1. Verify the release page and demo page are still reachable.
2. Confirm `Release Artifact Smoke` passed for the published tag. This is a mandatory pass gate before you announce or close the release work.
3. Confirm the package metadata on GitHub and PyPI looks correct.
4. Confirm `Latest` points to the intended tag.
5. Announce the release using `docs/releases/` copy if applicable.
