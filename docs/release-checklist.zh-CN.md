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
```

`make check` 现在已经包含本地 smoke 校验，所以只有在你单独排查启动问题时，才需要额外再跑一次 `make smoke`。

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

- 如果仓库要启用 GitHub Pages 或 PyPI，先确认 [maintainer-bootstrap.zh-CN.md](./maintainer-bootstrap.zh-CN.md) 里的首次初始化已经完成
- GitHub Actions `CI` 为绿色
- GitHub Actions `CodeQL` 为绿色
- 上一个已发布 tag 的 GitHub Actions `Release Artifact Smoke` 为绿色
- `release.yml` 存在且是当前版本
- 如果需要发 PyPI，`pypi-publish.yml` 已配置
- 仓库 secrets 已补齐

如果已发布 tag 对应的 `Release Artifact Smoke` 还没通过，这次 release 就不算完成。
标准 release 流程现在会在 GitHub Release 发布后自动触发这条 smoke workflow。

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

3. 按 [Release 产物校验](./release-artifacts.zh-CN.md) 文档里的完整流程校验最终 tag。至少要确认 wheel 可安装，并且 CLI 能启动：

```bash
python -m pip install ainews_open-X.Y.Z-py3-none-any.whl
python -m ainews --help
```

## 发版后

对外公告 release 或关闭 milestone 前，先完成这份发版后 smoke checklist。

### 已发布 tag 和 Release 页面

- [ ] Release 页面已经发布，不是 draft；除非本次有意发 prerelease，否则不能标成 prerelease。
- [ ] tag 指向预期的 `main` commit。
- [ ] GitHub 的 `Latest` 指向预期 tag。
- [ ] 最终 release notes 和 `CHANGELOG.md`、`docs/releases/vX.Y.Z.md` 一致。
- [ ] demo 页面和公开文档链接仍然可访问。

### 自动化和制品

- [ ] GitHub Actions `Release` 在该 tag 上执行成功。
- [ ] GitHub Actions `Release Artifact Smoke` 在该 tag 上执行成功。
- [ ] release commit 或 tag 对应的 GitHub Actions `CI`、`Smoke`、`CodeQL` 都是绿色。
- [ ] GitHub Release 包含 wheel、source archive、`sha256sums.txt`、SBOM 和 provenance attestation。
- [ ] 按 [Release 产物校验](./release-artifacts.zh-CN.md) 文档里的完整流程校验已发布资产，并且全部通过。

### 安装烟测

- [ ] 从已下载的 release wheel 在干净环境里安装成功。
- [ ] 从已下载的 source archive 在干净环境里安装成功。
- [ ] 在干净安装环境里 `python -m ainews --help` 可以运行。
- [ ] 在干净安装环境里 `python -m ainews stats` 可以运行。
- [ ] 如果本次 release 启用了 PyPI 发布，确认 GitHub 和 PyPI 上的包元信息都正确。

### 收尾

- [ ] 只有在 Release 页面、制品和 smoke workflows 都确认后，才关闭 release milestone。
- [ ] 如需对外公告，可直接复用 `docs/releases/` 里的文案。
- [ ] 延期事项放到单独 milestone，不要留在已经关闭的 release milestone 里。

## 发版后失败分流

- Release 制品缺失或不完整：先确认 tag 指向预期 commit，再重跑 `Release` workflow。除非公开 tag 本身指错 commit，并且维护者明确接受兼容性风险，否则不要移动或重建公开 tag。
- `Release Artifact Smoke` 失败：先判断失败点是 checksum、wheel 安装、source archive 安装、CLI 启动，还是 `/health` 启动。通过后续 PR 修复 release workflow 或打包问题；如果资产已经公开，修复后应发新的 patch tag。
- Release notes 或 `Latest` 指向错误：如果 tag 和资产正确，只编辑 GitHub Release 元数据即可。如果 tag 指错 commit，先停下来记录修复方案，再发布新的 tag。
- PyPI 不一致：把 PyPI 当成独立发布渠道处理。如果 PyPI 当前禁用或延期，保持 GitHub Release 有效，并把 PyPI 工作继续放在单独 milestone。
