# Release 恢复说明

[English](./release-recovery.md) · [简体中文](./release-recovery.zh-CN.md)

当 release 或 PR 收尾操作可能已经改动 GitHub 远端状态，但本地命令失败、超时，或导致本地 ref 不一致时，用这份说明恢复。本文只覆盖 GitHub release 渠道。PyPI 恢复流程保持独立。

## 恢复规则

- 重试任何会改远端状态的命令前，先读取远端状态。
- `git fetch`、`git merge --ff-only`、`git status`、`git ls-remote`、`gh pr view`、`gh release view`、`gh run list` 和 GitHub API `GET` 请求可以安全重跑。
- 如果 `git push`、`gh api` 的 `POST`、`PUT` 或 `DELETE` 超时，先假设远端操作可能已经成功，直到只读检查证明没有成功。
- 除非公开 tag 指向了错误 commit，并且维护者明确接受兼容性风险，否则不要移动或重建公开 tag。
- PyPI 恢复不要混进这条流程。如果 PyPI 当前禁用或延期，继续把它留在独立 milestone。

## 快速索引

当 release 收尾步骤超时，或本地状态不确定时，先从这里判断该看哪条详细流程。

| 症状 | 第一个安全检查 | 详细流程 |
| --- | --- | --- |
| PR 合并命令超时 | `gh pr view 123 --json state,merged,mergeCommit` | [PR 已合并，但本地快进失败](#pr-已合并但本地快进失败) |
| PR 已合并，但本地 `main` 不能 fast-forward | `git status --short --branch` 和 `git ls-remote origin refs/heads/main` | [PR 已合并，但本地快进失败](#pr-已合并但本地快进失败) |
| GitHub 上已有 tag，但本地 fetch 失败 | `git ls-remote --tags origin "refs/tags/${TAG}"` | [Tag 已创建，但本地 fetch 失败](#tag-已创建但本地-fetch-失败) |
| 创建 Release 前推送 tag 超时 | `git ls-remote --tags origin "refs/tags/${TAG}"` | [推送 tag 超时，但尚未创建 Release](#推送-tag-超时但尚未创建-release) |
| Release workflow 已完成，但还要确认资产 | `gh release view "${TAG}" --json assets,isDraft,isPrerelease,url` | [Release workflow 成功，但还需要验证 asset smoke](#release-workflow-成功但还需要验证-asset-smoke) |
| 触发 workflow、更新 issue 或删除分支超时 | 重跑超时表中对应的只读命令 | [远端操作后网络超时](#远端操作后网络超时) |

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

## 推送 tag 超时，但尚未创建 Release

如果 `git push origin "${TAG}"` 超时，不要立刻再次推送。先按下面的流程确认远端 tag 状态：

```bash
TAG=vX.Y.Z
TARGET=$(git rev-parse "${TAG}^{commit}")
REMOTE_TAG=$(git ls-remote --tags origin "refs/tags/${TAG}" | awk '{print $1}')
```

- 如果 `REMOTE_TAG` 为空，说明远端 tag 没有创建成功。可以安全重试 `git push origin "${TAG}"`。
- 如果 `REMOTE_TAG` 等于 `TARGET`，说明 GitHub 上已经有正确 tag。不要再次推送，继续创建 Release 或验证 Release 状态。
- 如果 `REMOTE_TAG` 存在但不同于 `TARGET`，立刻停下。没有明确维护者决策前，不要 force-push、删除或重建公开 tag。

如果 SSH 或 HTTPS 推送持续超时，但只读检查证明远端 tag 仍然缺失，维护者可以用 GitHub Git API 创建 tag ref 作为兜底方案。这个兜底方案只应该创建一个新的 lightweight tag ref，并且指向本地 tag 对应的同一个 commit：

```bash
TAG=vX.Y.Z
TARGET=$(git rev-parse "${TAG}^{commit}")
gh api \
  --method POST \
  "repos/X-PG13/ainews-open/git/refs" \
  -f ref="refs/tags/${TAG}" \
  -f sha="${TARGET}"
```

API 调用后，先验证远端 tag，再创建或编辑 Release：

```bash
git ls-remote --tags origin "refs/tags/${TAG}"
gh api "repos/X-PG13/ainews-open/git/ref/tags/${TAG}" --jq '{ref,object}'
```

当 release checklist 只要求 tag 名称指向预期 release commit 时，API 创建的 lightweight tag ref 可以接受。如果 release 要求 signed tag object、annotated tag message，或 tag object 本身携带 provenance，就停下并改用正常的签名或 annotated tag 流程。

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
