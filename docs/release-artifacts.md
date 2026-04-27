# Release Artifacts

[English](./release-artifacts.md) · [简体中文](./release-artifacts.zh-CN.md)

Every tagged GitHub release publishes a release bundle with:

- source distribution (`.tar.gz`)
- wheel (`.whl`)
- `sha256sums.txt`
- CycloneDX SBOM JSON
- provenance attestation

The repository also includes a GitHub Actions validation workflow:

- `.github/workflows/release-artifact-smoke.yml`

It downloads the published release assets, verifies checksums, installs the wheel and source archive in clean jobs, and runs minimal CLI and `/health` smoke checks.

Treat this workflow as a release-completion gate. Do not announce a new public tag until it passes.
For tags created through `.github/workflows/release.yml`, the smoke workflow is dispatched automatically after the GitHub Release is published. You can still re-run it manually for any published tag.

## Copy-Paste Verification Flow

Set `VERSION` to the release tag without the leading `v`, then download the release assets into a clean directory:

```bash
export VERSION=1.2.49
export REPO=X-PG13/ainews-open
mkdir -p "ainews-open-${VERSION}-release"
cd "ainews-open-${VERSION}-release"

curl -LO "https://github.com/${REPO}/releases/download/v${VERSION}/ainews_open-${VERSION}-py3-none-any.whl"
curl -LO "https://github.com/${REPO}/releases/download/v${VERSION}/ainews_open-${VERSION}.tar.gz"
curl -LO "https://github.com/${REPO}/releases/download/v${VERSION}/sha256sums.txt"
curl -LO "https://github.com/${REPO}/releases/download/v${VERSION}/v${VERSION}-sbom.json"
```

Verify checksums with Python so the same command works on Linux and macOS:

```bash
python - <<'PY'
from pathlib import Path
import hashlib

for line in Path("sha256sums.txt").read_text(encoding="utf-8").splitlines():
    expected, filename = line.split(maxsplit=1)
    filename = filename.lstrip("*")
    actual = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    if actual != expected.lower():
        raise SystemExit(f"checksum mismatch: {filename}")
    print(f"ok {filename}")
PY
```

Install and smoke-check the downloaded wheel instead of installing `ainews-open` from PyPI:

```bash
python -m venv .venv-wheel
. .venv-wheel/bin/activate
python -m pip install --upgrade pip
python -m pip install "./ainews_open-${VERSION}-py3-none-any.whl"
python -m ainews --help
python -m ainews stats
deactivate
```

Install the source archive in a separate clean environment:

```bash
python -m venv .venv-sdist
. .venv-sdist/bin/activate
python -m pip install --upgrade pip
python -m pip install "./ainews_open-${VERSION}.tar.gz"
python -m ainews --help
python -m ainews stats
deactivate
```

Inspect the SBOM enough to confirm it is machine-readable CycloneDX JSON:

```bash
python - <<'PY'
from pathlib import Path
import json
import os

sbom_path = Path(f"v{os.environ['VERSION']}-sbom.json")
sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
components = len(sbom.get("components", []))
print(f"{sbom.get('bomFormat')} {sbom.get('specVersion')} components={components}")
if sbom.get("bomFormat") != "CycloneDX":
    raise SystemExit("unexpected SBOM format")
PY
```

## Download And Verify

From a release page, download the wheel, source archive, and `sha256sums.txt`.
Run the checksum command from the same directory that contains those downloaded files.

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

For the GitHub-hosted equivalent, re-run the `Release Artifact Smoke` workflow against any published tag.

## SBOM And Provenance

- The SBOM file is published as `vX.Y.Z-sbom.json`.
- Provenance is attached through GitHub artifact attestations in the release workflow.
- Use these assets when you need a lightweight supply-chain review or internal package intake evidence.
