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

- one-time repository setup in [maintainer-bootstrap.md](./maintainer-bootstrap.md) is complete if this repository publishes to GitHub Pages or PyPI
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

3. Follow the [release artifact verification flow](./release-artifacts.md#copy-paste-verification-flow) for the final tag. At minimum, verify the wheel installs and the CLI starts:

```bash
python -m pip install ainews_open-X.Y.Z-py3-none-any.whl
python -m ainews --help
```

## After Release

Run the post-release smoke checklist before announcing the release or closing its milestone.

### Published Tag And Release Page

- [ ] The release page is published, not a draft, and not marked as a prerelease unless that was intentional.
- [ ] The tag points to the intended `main` commit.
- [ ] GitHub marks the intended tag as `Latest`.
- [ ] The final release notes match `CHANGELOG.md` and `docs/releases/vX.Y.Z.md`.
- [ ] The demo page and public docs links still load.

### Automation And Assets

- [ ] GitHub Actions `Release` completed successfully for the tag.
- [ ] GitHub Actions `Release Artifact Smoke` completed successfully for the tag.
- [ ] GitHub Actions `CI`, `Smoke`, and `CodeQL` are green for the release commit or tag.
- [ ] The GitHub Release contains the wheel, source archive, `sha256sums.txt`, SBOM, and provenance attestation.
- [ ] The [release artifact verification flow](./release-artifacts.md#copy-paste-verification-flow) passes against the published assets.

### Install Smoke

- [ ] A clean wheel install from the downloaded release asset succeeds.
- [ ] A clean source archive install from the downloaded release asset succeeds.
- [ ] `python -m ainews --help` runs from the clean install.
- [ ] `python -m ainews stats` runs from the clean install.
- [ ] Package metadata on GitHub and PyPI looks correct if PyPI publication is enabled for this release.

### Closeout

- [ ] Close the release milestone only after the release page, assets, and smoke workflows are verified.
- [ ] Announce the release using `docs/releases/` copy if applicable.
- [ ] Leave deferred work in a separate milestone instead of carrying it inside the closed release milestone.

## Post-Release Failure Triage

- Missing or partial release assets: confirm the tag points to the intended commit, then re-run the `Release` workflow. Do not move or recreate a public tag unless the published tag itself points to the wrong commit and the maintainer explicitly accepts the compatibility risk.
- Failed `Release Artifact Smoke`: inspect whether the failure is checksum, wheel install, source archive install, CLI startup, or `/health` startup. Fix the release workflow or package issue in a follow-up PR, then publish a new patch tag if the released assets are already public.
- Wrong release notes or `Latest` target: edit the GitHub Release metadata if the tag and assets are correct. If the wrong commit was tagged, stop and document the remediation before publishing another tag.
- PyPI mismatch: treat PyPI as a separate release channel. If PyPI is disabled or deferred, keep the GitHub Release valid and leave PyPI work in its own milestone.
