# 发版清单

[English](./release-checklist.md) · [简体中文](./release-checklist.zh-CN.md)

每次准备公开发版前，建议按这份清单走一遍。

## 打 tag 前

1. 阅读 `CHANGELOG.md`，并在 `docs/releases/` 下补本次版本说明。
2. 确认 `README.md` 和 `README.zh-CN.md` 里的文档、demo 链接都有效。
3. 确认 `docs/release-artifacts.zh-CN.md` 仍然和当前 release bundle 结构一致。
4. 运行：

```bash
make check
make smoke
```

5. 用当前 compose profile 验证 `docker compose config -q` 能通过。
6. 确认 open code scanning alerts 为 `0`。
7. 确认 demo 页面和 `docs/demo/` 下的样例文件都还在。

## 版本更新

1. 更新 `pyproject.toml` 中的版本号。
2. 更新 `src/ainews/__init__.py` 中的版本号。
3. 在 `CHANGELOG.md` 中增加本次版本条目。
4. 新增或更新 `docs/releases/vX.Y.Z.md`。

## 发布自动化检查

确认以下项都正常：

- GitHub Actions `CI` 为绿色
- GitHub Actions `CodeQL` 为绿色
- 上一个已发布 tag 的 GitHub Actions `Release Artifact Smoke` 为绿色
- `release.yml` 存在且是当前版本
- 如果需要发 PyPI，`pypi-publish.yml` 已配置
- 仓库 secrets 已补齐

## GitHub Release

1. 创建并推送 tag：

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

2. 确认 GitHub Release 页面中包含：

- 构建出的 distributions
- `sha256sums.txt`
- SBOM
- provenance attestation
- 最终版 release notes
- release artifact 的安装与校验说明

3. 额外验证一次 release artifact 安装说明可用：

```bash
python -m pip install ainews_open-X.Y.Z-py3-none-any.whl
python -m ainews --help
```

## 发版后

1. 检查 Release 页面和 demo 页面仍可访问。
2. 检查已发布 tag 的 `Release Artifact Smoke` 是否通过。
3. 检查 GitHub / PyPI 上的包元信息是否正确。
4. 检查 `Latest` 是否指向预期 tag。
5. 如需对外公告，可直接复用 `docs/releases/` 里的文案。
