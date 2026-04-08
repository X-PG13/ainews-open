# Release 产物校验

[English](./release-artifacts.md) · [简体中文](./release-artifacts.zh-CN.md)

每个带 tag 的 GitHub Release 都会发布一组 release bundle，包含：

- source distribution（`.tar.gz`）
- wheel（`.whl`）
- `sha256sums.txt`
- CycloneDX SBOM JSON
- provenance attestation

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

## SBOM 和 Provenance

- SBOM 文件会作为 `vX.Y.Z-sbom.json` 发布
- provenance 通过 GitHub release workflow 的 artifact attestations 生成
- 如果你要做内部制品准入或轻量供应链审计，可以直接使用这些文件
