# Release Artifacts

[English](./release-artifacts.md) · [简体中文](./release-artifacts.zh-CN.md)

Every tagged GitHub release publishes a release bundle with:

- source distribution (`.tar.gz`)
- wheel (`.whl`)
- `sha256sums.txt`
- CycloneDX SBOM JSON
- provenance attestation

## Download And Verify

From a release page, download the wheel, source archive, and `sha256sums.txt`.

### Linux

```bash
sha256sum -c sha256sums.txt
```

### macOS

```bash
shasum -a 256 -c sha256sums.txt
```

## Install From The Wheel

```bash
python -m pip install ainews_open-X.Y.Z-py3-none-any.whl
```

## Install From The Source Archive

```bash
python -m pip install ainews_open-X.Y.Z.tar.gz
```

## Quick Post-Install Check

```bash
python -m ainews --help
python -m ainews stats
```

## SBOM And Provenance

- The SBOM file is published as `vX.Y.Z-sbom.json`.
- Provenance is attached through GitHub artifact attestations in the release workflow.
- Use these assets when you need a lightweight supply-chain review or internal package intake evidence.
