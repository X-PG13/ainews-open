# Release Recovery Notes

[English](./release-recovery.md) · [简体中文](./release-recovery.zh-CN.md)

Use these notes when a release or PR closeout action may have changed GitHub state, but the local command failed, timed out, or left local refs inconsistent. This page covers the GitHub release channel only. PyPI recovery stays separate.

## Recovery Rules

- Verify remote state before retrying any mutating command.
- Treat `git fetch`, `git merge --ff-only`, `git status`, `git ls-remote`, `gh pr view`, `gh release view`, `gh run list`, and GitHub API `GET` requests as safe to rerun.
- If a `git push`, `gh api` `POST`, `PUT`, or `DELETE` times out, assume it may have succeeded until a read-only check proves otherwise.
- Do not move or recreate a public tag unless the tag points to the wrong commit and the maintainer explicitly accepts the compatibility risk.
- Keep PyPI recovery out of this flow. If PyPI is disabled or deferred, leave it in its own milestone.

## Network Access and Proxy Fallback (Optional)

- If GitHub API or git commands repeatedly time out because the local network path is unstable, maintainers can temporarily use the local HTTP proxy for the command first.
- Example:

```bash
export HTTPS_PROXY=http://127.0.0.1:7897
export HTTP_PROXY=http://127.0.0.1:7897

# Compatibility aliases for tools that only honor lowercase env vars
export https_proxy=$HTTPS_PROXY
export http_proxy=$HTTP_PROXY

gh pr view --state all --limit 10

unset HTTPS_PROXY HTTP_PROXY https_proxy http_proxy
```

Once the command succeeds, continue with the normal read-only verification flow and remove the proxy once the network is stable again.

## Quick Reference

Start here when a release closeout step times out or leaves local state unclear.

| Symptom | First safe check | Detailed flow |
| --- | --- | --- |
| PR merge command timed out | `gh pr view 123 --json state,merged,mergeCommit` | [PR Merge Succeeded, Local Fast-Forward Failed](#pr-merge-succeeded-local-fast-forward-failed) |
| Local `main` cannot fast-forward after a merged PR | `git status --short --branch` and `git ls-remote origin refs/heads/main` | [PR Merge Succeeded, Local Fast-Forward Failed](#pr-merge-succeeded-local-fast-forward-failed) |
| Tag exists on GitHub but local fetch failed | `git ls-remote --tags origin "refs/tags/${TAG}"` | [Tag Created, Local Fetch Failed](#tag-created-local-fetch-failed) |
| Tag push timed out before Release creation | `git ls-remote --tags origin "refs/tags/${TAG}"` | [Tag Push Timed Out Before Release Creation](#tag-push-timed-out-before-release-creation) |
| Release workflow finished but assets need confirmation | `gh release view "${TAG}" --json assets,isDraft,isPrerelease,url` | [Release Workflow Succeeded, Asset Smoke Needs Verification](#release-workflow-succeeded-asset-smoke-needs-verification) |
| Workflow dispatch, issue update, or branch deletion timed out | Re-run the matching read-only command from the timeout table | [Network Timeout After A Remote Action](#network-timeout-after-a-remote-action) |

## Maintainer Status Snapshot

Use this read-only snapshot when you need to report current repository progress after a release, PR merge, or interrupted network command:

```bash
git status --short --branch
git rev-parse HEAD origin/main main
gh release view --json tagName,targetCommitish,isDraft,isPrerelease,publishedAt
gh api repos/X-PG13/ainews-open/git/ref/tags/vX.Y.Z --jq '{ref,sha:.object.sha,type:.object.type}'
gh run list --limit 10 --json databaseId,name,status,conclusion,headBranch,headSha,event,createdAt,updatedAt
gh api repos/X-PG13/ainews-open/milestones --jq '.[] | {number,title,state,open_issues,closed_issues}'
gh issue view 86 --json state,milestone,title
```

Read the snapshot in this order:

1. Local `main`, `origin/main`, and `HEAD` should point to the same commit before starting new work.
2. The latest GitHub Release should be published, not a draft, and not a prerelease unless that was intentional.
3. The release tag should point to the same commit as the release prep merge commit.
4. Release, artifact smoke, CI, Smoke, and CodeQL runs should be completed successfully for the release tag or commit.
5. The completed release milestone should have `0` open issues before it is closed.
6. Issue `#86` should remain in the `Deferred: PyPI` milestone unless the maintainer explicitly decides to work on PyPI.

## PR Merge Succeeded, Local Fast-Forward Failed

First confirm whether the PR actually merged:

```bash
PR=123
gh pr view "${PR}" --json state,merged,mergeCommit,headRefName,baseRefName,url
gh api "repos/X-PG13/ainews-open/pulls/${PR}" \
  --jq '{state,merged,merge_commit_sha,head:.head.ref,base:.base.ref}'
```

If `merged` is true, recover local `main` with a fast-forward only:

```bash
git fetch --prune origin main
git switch main
git merge --ff-only origin/main
git status --short --branch
```

If `git fetch` failed after damaging the local remote-tracking ref, verify the remote `main` commit before repairing the ref:

```bash
REMOTE_MAIN=$(git ls-remote origin refs/heads/main | awk '{print $1}')
git update-ref refs/remotes/origin/main "${REMOTE_MAIN}"
git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
git merge --ff-only origin/main
```

Do not create a local merge commit and do not push local `main` as a workaround. The goal is to mirror the already-merged GitHub state.

## Tag Created, Local Fetch Failed

First confirm the remote tag and release state:

```bash
TAG=vX.Y.Z
git ls-remote --tags origin "refs/tags/${TAG}"
gh release view "${TAG}" --json tagName,targetCommitish,isDraft,isPrerelease,url
```

If the tag exists remotely, fetch only that tag and verify its target:

```bash
git fetch origin "refs/tags/${TAG}:refs/tags/${TAG}"
git rev-parse "${TAG}^{commit}"
git show --no-patch --decorate "${TAG}"
```

If a local tag already exists, compare it before doing anything else:

```bash
git show-ref --tags "${TAG}"
git rev-parse "${TAG}^{commit}"
```

If the local and remote tag targets differ, stop. Do not delete, move, or recreate the public tag without an explicit maintainer decision.

## Tag Push Timed Out Before Release Creation

If `git push origin "${TAG}"` times out, do not push again until the remote tag state is known. Use this decision flow:

```bash
TAG=vX.Y.Z
TARGET=$(git rev-parse "${TAG}^{commit}")
REMOTE_TAG=$(git ls-remote --tags origin "refs/tags/${TAG}" | awk '{print $1}')
```

- If `REMOTE_TAG` is empty, the remote tag was not created. It is safe to retry `git push origin "${TAG}"`.
- If `REMOTE_TAG` equals `TARGET`, the tag already exists on GitHub. Do not push it again; continue with release creation or release verification.
- If `REMOTE_TAG` is present but differs from `TARGET`, stop. Do not force-push, delete, or recreate the public tag without an explicit maintainer decision.

When SSH or HTTPS pushes keep timing out but the read-only check proves the tag is still missing, maintainers may create the tag ref through the GitHub Git API as a fallback. This fallback should only create a new lightweight tag ref that points at the same commit as the local tag:

```bash
TAG=vX.Y.Z
TARGET=$(git rev-parse "${TAG}^{commit}")
gh api \
  --method POST \
  "repos/X-PG13/ainews-open/git/refs" \
  -f ref="refs/tags/${TAG}" \
  -f sha="${TARGET}"
```

After the API call, verify the remote tag before creating or editing the release:

```bash
git ls-remote --tags origin "refs/tags/${TAG}"
gh api "repos/X-PG13/ainews-open/git/ref/tags/${TAG}" --jq '{ref,object}'
```

API-created lightweight tag refs are acceptable when the release checklist only requires the tag name to point at the intended release commit. Stop and use the normal signed or annotated tag process instead if the release requires a signed tag object, annotated tag message, or provenance attached to the tag object itself.

## Release Workflow Succeeded, Asset Smoke Needs Verification

Confirm the release workflow, artifact smoke workflow, and published asset set:

```bash
TAG=vX.Y.Z
VERSION=${TAG#v}
gh run list --workflow release.yml --limit 10
gh run list --workflow release-artifact-smoke.yml --limit 10
gh release view "${TAG}" --json assets,isDraft,isPrerelease,isLatest,url
```

Download the expected assets into a scratch directory:

```bash
WORKDIR=$(mktemp -d)
gh release download "${TAG}" \
  --dir "${WORKDIR}" \
  --pattern "ainews_open-${VERSION}-py3-none-any.whl" \
  --pattern "ainews_open-${VERSION}.tar.gz" \
  --pattern "sha256sums.txt" \
  --pattern "${TAG}-sbom.json"
```

Run the checksum and install smoke checks:

```bash
(cd "${WORKDIR}" && sha256sum -c sha256sums.txt)
python -m pip install "${WORKDIR}/ainews_open-${VERSION}-py3-none-any.whl"
python -m ainews --help
```

For the full wheel, source archive, checksum, and SBOM path, use the [release artifact verification flow](./release-artifacts.md#copy-paste-verification-flow).

## Network Timeout After A Remote Action

When a mutating network call times out, read state first and retry only if the read proves the action did not happen.

| Interrupted action | Safe verification command |
| --- | --- |
| PR creation | `gh pr list --head review/example --state all` |
| PR merge | `gh pr view 123 --json state,merged,mergeCommit` |
| Review branch deletion | `git ls-remote --heads origin review/example` |
| Tag push | `git ls-remote --tags origin refs/tags/vX.Y.Z` |
| Release create or upload | `gh release view vX.Y.Z --json assets,isDraft,isPrerelease,url` |
| Workflow dispatch | `gh run list --workflow release-artifact-smoke.yml --limit 10` |
| Issue or milestone update | `gh issue view 123 --json state,milestone,closedAt` |

Retrying read-only commands is safe. Retrying `POST`, `PUT`, `DELETE`, or `git push` is only safe after the verification command shows the remote action is still missing.
