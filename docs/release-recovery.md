# Release Recovery Notes

[English](./release-recovery.md) · [简体中文](./release-recovery.zh-CN.md)

Use these notes when a release or PR closeout action may have changed GitHub state, but the local command failed, timed out, or left local refs inconsistent. This page covers the GitHub release channel only. PyPI recovery stays separate.

## Recovery Rules

- Verify remote state before retrying any mutating command.
- Treat `git fetch`, `git merge --ff-only`, `git status`, `git ls-remote`, `gh pr view`, `gh release view`, `gh run list`, and GitHub API `GET` requests as safe to rerun.
- If a `git push`, `gh api` `POST`, `PUT`, or `DELETE` times out, assume it may have succeeded until a read-only check proves otherwise.
- Do not move or recreate a public tag unless the tag points to the wrong commit and the maintainer explicitly accepts the compatibility risk.
- Keep PyPI recovery out of this flow. If PyPI is disabled or deferred, leave it in its own milestone.

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

Use this flow when `git push origin "${TAG}"` or `git push origin "refs/tags/${TAG}"` times out before the GitHub Release is created. Do not retry the push immediately; first prove whether the remote tag already exists.

Verify the local tag target and remote state:

```bash
TAG=vX.Y.Z
EXPECTED_COMMIT=$(git rev-parse "${TAG}^{commit}")
git show --no-patch --decorate "${TAG}"
git ls-remote --tags origin "refs/tags/${TAG}"
gh api "repos/X-PG13/ainews-open/git/ref/tags/${TAG}" \
  --jq '{ref,object}'
```

Use these decisions:

- If the remote tag exists and points to `EXPECTED_COMMIT`, treat the push as successful. Fetch the tag, verify the release workflow, and continue with release asset checks.
- If the remote tag exists but points anywhere else, stop. Do not delete, move, or recreate the public tag without an explicit maintainer decision.
- If the remote tag is missing and the local tag points to the reviewed release commit, an API-created lightweight tag ref is acceptable for this repository because existing release tags are lightweight commit refs.
- If a signed or annotated tag is required for the release, stop instead of using the lightweight-ref fallback.

Create the missing lightweight tag ref only after the read-only checks prove it is absent:

```bash
gh api repos/X-PG13/ainews-open/git/refs \
  -f "ref=refs/tags/${TAG}" \
  -f "sha=${EXPECTED_COMMIT}"
```

Then verify the public tag before creating or editing the GitHub Release:

```bash
git ls-remote --tags origin "refs/tags/${TAG}"
gh api "repos/X-PG13/ainews-open/git/ref/tags/${TAG}" \
  --jq '{ref,object}'
gh release view "${TAG}" --json tagName,targetCommitish,isDraft,isPrerelease,url
```

If the API call times out, repeat the read-only verification commands before retrying. Never issue a second tag-creation request until the remote tag is proven missing.

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
