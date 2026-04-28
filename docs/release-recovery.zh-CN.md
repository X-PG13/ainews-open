# Release 恢复说明

[English](./release-recovery.md) · [简体中文](./release-recovery.zh-CN.md)

当 release 或 PR 收尾操作可能已经改动 GitHub 远端状态，但本地命令失败、超时，或导致本地 ref 不一致时，用这份说明恢复。本文只覆盖 GitHub release 渠道。PyPI 恢复流程保持独立。

## 恢复规则

- 重试任何会改远端状态的命令前，先读取远端状态。
- `git fetch`、`git merge --ff-only`、`git status`、`git ls-remote`、`gh pr view`、`gh release view`、`gh run list` 和 GitHub API `GET` 请求可以安全重跑。
- 如果 `git push`、`gh api` 的 `POST`、`PUT` 或 `DELETE` 超时，先假设远端操作可能已经成功，直到只读检查证明没有成功。
- 除非公开 tag 指向了错误 commit，并且维护者明确接受兼容性风险，否则不要移动或重建公开 tag。
- PyPI 恢复不要混进这条流程。如果 PyPI 当前禁用或延期，继续把它留在独立 milestone。

## PR 已合并，但本地快进失败

先确认 PR 是否真的已经合并：

```bash
PR=123
gh pr view "${PR}" --json state,merged,mergeCommit,headRefName,baseRefName,url
gh api "repos/X-PG13/ainews-open/pulls/${PR}" \
  --jq '{state,merged,merge_commit_sha,head:.head.ref,base:.base.ref}'
```

如果 `merged` 为 true，只用 fast-forward 恢复本地 `main`：

```bash
git fetch --prune origin main
git switch main
git merge --ff-only origin/main
git status --short --branch
```

如果 `git fetch` 中途失败并破坏了本地 remote-tracking ref，先验证远端 `main` commit，再修复本地 ref：

```bash
REMOTE_MAIN=$(git ls-remote origin refs/heads/main | awk '{print $1}')
git update-ref refs/remotes/origin/main "${REMOTE_MAIN}"
git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
git merge --ff-only origin/main
```

不要为了绕过问题创建本地 merge commit，也不要 push 本地 `main`。目标是让本地状态镜像 GitHub 上已经合并的状态。

## Tag 已创建，但本地 fetch 失败

先确认远端 tag 和 release 状态：

```bash
TAG=vX.Y.Z
git ls-remote --tags origin "refs/tags/${TAG}"
gh release view "${TAG}" --json tagName,targetCommitish,isDraft,isPrerelease,url
```

如果远端 tag 存在，只 fetch 这个 tag 并验证目标 commit：

```bash
git fetch origin "refs/tags/${TAG}:refs/tags/${TAG}"
git rev-parse "${TAG}^{commit}"
git show --no-patch --decorate "${TAG}"
```

如果本地已经有同名 tag，先比较它，再做下一步：

```bash
git show-ref --tags "${TAG}"
git rev-parse "${TAG}^{commit}"
```

如果本地和远端 tag 目标不一致，立刻停下。没有明确维护者决策前，不要删除、移动或重建公开 tag。

## Release workflow 成功，但还需要验证 asset smoke

确认 release workflow、artifact smoke workflow 和已发布资产：

```bash
TAG=vX.Y.Z
VERSION=${TAG#v}
gh run list --workflow release.yml --limit 10
gh run list --workflow release-artifact-smoke.yml --limit 10
gh release view "${TAG}" --json assets,isDraft,isPrerelease,isLatest,url
```

把预期资产下载到临时目录：

```bash
WORKDIR=$(mktemp -d)
gh release download "${TAG}" \
  --dir "${WORKDIR}" \
  --pattern "ainews_open-${VERSION}-py3-none-any.whl" \
  --pattern "ainews_open-${VERSION}.tar.gz" \
  --pattern "sha256sums.txt" \
  --pattern "${TAG}-sbom.json"
```

执行 checksum 和安装烟测：

```bash
(cd "${WORKDIR}" && sha256sum -c sha256sums.txt)
python -m pip install "${WORKDIR}/ainews_open-${VERSION}-py3-none-any.whl"
python -m ainews --help
```

完整的 wheel、source archive、checksum 和 SBOM 校验路径见 [Release 产物校验流程](./release-artifacts.zh-CN.md#copy-paste-verification-flow)。

## 远端操作后网络超时

如果一个会改远端状态的网络调用超时，先读取状态；只有只读检查证明操作没有发生时，才重试写操作。

| 中断的操作 | 安全验证命令 |
| --- | --- |
| 创建 PR | `gh pr list --head review/example --state all` |
| 合并 PR | `gh pr view 123 --json state,merged,mergeCommit` |
| 删除 review 分支 | `git ls-remote --heads origin review/example` |
| 推送 tag | `git ls-remote --tags origin refs/tags/vX.Y.Z` |
| 创建或上传 Release | `gh release view vX.Y.Z --json assets,isDraft,isPrerelease,url` |
| 触发 workflow | `gh run list --workflow release-artifact-smoke.yml --limit 10` |
| 更新 issue 或 milestone | `gh issue view 123 --json state,milestone,closedAt` |

只读命令可以安全重跑。`POST`、`PUT`、`DELETE` 或 `git push` 只有在验证命令显示远端操作仍然不存在时，才应该重试。
