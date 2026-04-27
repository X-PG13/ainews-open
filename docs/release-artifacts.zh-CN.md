# Release 产物校验

[English](./release-artifacts.md) · [简体中文](./release-artifacts.zh-CN.md)

每个带 tag 的 GitHub Release 都会发布一组 release bundle，包含：

- source distribution（`.tar.gz`）
- wheel（`.whl`）
- `sha256sums.txt`
- CycloneDX SBOM JSON
- provenance attestation

仓库还提供了一个自动验收 workflow：

- `.github/workflows/release-artifact-smoke.yml`

它会下载已经发布的 release 资产，校验 checksum，在干净环境里分别安装 wheel 和 source archive，并执行最小 CLI 与 `/health` 烟雾测试。

这条 workflow 应该被视为 release 完成前的强制门禁。它没通过之前，不要对外公告新 tag。
如果 tag 是通过 `.github/workflows/release.yml` 发出来的，这条 smoke workflow 会在 GitHub Release 发布后自动触发。你仍然可以针对任意已发布 tag 手动重跑。

## 可直接复制的校验流程

把 `VERSION` 设置为不带前导 `v` 的 release tag，然后把 release 资产下载到一个干净目录：

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

用 Python 校验 checksum，这样同一条命令可以同时适用于 Linux 和 macOS：

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

从已下载的 wheel 安装，而不是从 PyPI 安装 `ainews-open`，并做最小烟测：

```bash
python -m venv .venv-wheel
. .venv-wheel/bin/activate
python -m pip install --upgrade pip
python -m pip install "./ainews_open-${VERSION}-py3-none-any.whl"
python -m ainews --help
python -m ainews stats
deactivate
```

在另一个干净环境里从 source archive 安装：

```bash
python -m venv .venv-sdist
. .venv-sdist/bin/activate
python -m pip install --upgrade pip
python -m pip install "./ainews_open-${VERSION}.tar.gz"
python -m ainews --help
python -m ainews stats
deactivate
```

检查 SBOM 至少是可机器读取的 CycloneDX JSON：

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

## 下载并校验

从 Release 页面下载 wheel、source archive 和 `sha256sums.txt`。
在这些文件所在的同一目录里执行 checksum 校验命令。

### Linux

```bash
sha256sum -c sha256sums.txt
```

### macOS

```bash
shasum -a 256 -c sha256sums.txt
```

## 从 Wheel 安装

```bash
python -m pip install ainews_open-X.Y.Z-py3-none-any.whl
```

## 从 Source Archive 安装

```bash
python -m pip install ainews_open-X.Y.Z.tar.gz
```

## 安装后快速检查

```bash
python -m ainews --help
python -m ainews stats
```

如果你想跑 GitHub 托管环境里的同等校验，直接对已发布 tag 重新执行 `Release Artifact Smoke` workflow。

## SBOM 和 Provenance

- SBOM 文件会作为 `vX.Y.Z-sbom.json` 发布
- provenance 通过 GitHub release workflow 的 artifact attestations 生成
- 如果你要做内部制品准入或轻量供应链审计，可以直接使用这些文件
