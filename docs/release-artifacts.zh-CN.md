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

## 下载并校验

从 Release 页面下载 wheel、source archive 和 `sha256sums.txt`。

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
