# Maintainer Bootstrap

[English](./maintainer-bootstrap.md) · [简体中文](./maintainer-bootstrap.zh-CN.md)

This guide documents the one-time repository setup that maintainers need before GitHub Pages and PyPI publishing can run without guesswork.

## What This Covers

- GitHub Pages deployment for the sample demo via [demo-pages.yml](../.github/workflows/demo-pages.yml)
- Trusted PyPI publishing via [pypi-publish.yml](../.github/workflows/pypi-publish.yml)
- The repository variable and environment names that those workflows expect

## Repository Values Used By This Repository

If you fork or rename the repository, update these values before configuring external services:

- GitHub owner: `X-PG13`
- GitHub repository: `ainews-open`
- Default branch: `main`
- PyPI project name: `ainews-open`
- GitHub Pages artifact path: `docs/demo/`
- PyPI workflow file: `.github/workflows/pypi-publish.yml`
- GitHub Pages workflow file: `.github/workflows/demo-pages.yml`

## GitHub Pages One-Time Setup

1. Open GitHub repository `Settings` -> `Pages`.
2. Under `Build and deployment`, set `Source` to `GitHub Actions`.
3. Keep [demo-pages.yml](../.github/workflows/demo-pages.yml) as the publishing workflow. It uploads `docs/demo/` and deploys it with the `github-pages` environment.
4. Trigger the workflow once from `Actions` -> `Demo Pages` -> `Run workflow`, or push a change to `docs/demo/` on `main`.
5. After the first successful deploy, check `Settings` -> `Environments` and confirm the `github-pages` environment is now visible for the Pages deployment job.
6. Add a deployment protection rule on `github-pages` if you want to restrict deployments to the default branch, which matches GitHub's recommended setup for Pages workflows.
7. Verify that `Settings` -> `Pages` shows the published site URL and that the demo is reachable.

Notes:

- GitHub Pages sites are public on the internet once published, even when the repository itself is private on supported plans.
- If you later add a custom domain, configure it in `Settings` -> `Pages`; committing a `CNAME` file alone is not enough.

## PyPI Trusted Publishing One-Time Setup

1. Open GitHub repository `Settings` -> `Environments` -> `New environment`.
2. Create an environment named exactly `pypi`.
3. Optionally add required reviewers or wait timers to `pypi` if you want a manual approval gate before upload.
4. Open GitHub repository `Settings` -> `Secrets and variables` -> `Actions` -> `Variables`.
5. Add a repository variable named `AINEWS_ENABLE_PYPI_PUBLISH` with value `true` if you want release publication to trigger PyPI uploads automatically.
6. In PyPI, choose one of these setup paths:
   - Existing project: open the `ainews-open` project, then go to `Manage` -> `Publishing` -> `Add a publisher`.
   - Brand-new project: open your PyPI account `Publishing` page and add a pending publisher for project `ainews-open`.
7. In the PyPI publisher form for GitHub Actions, use these values:
   - Owner: `X-PG13`
   - Repository name: `ainews-open`
   - Workflow filename: `.github/workflows/pypi-publish.yml`
   - Environment name: `pypi`
   - Project name: `ainews-open` if you are creating a pending publisher
8. Save the publisher. No PyPI API token secret is needed because [pypi-publish.yml](../.github/workflows/pypi-publish.yml) uses OIDC trusted publishing with `id-token: write`.

## First Verification After Setup

- GitHub Pages:
  - Run `Demo Pages` once and confirm a successful deployment to `github-pages`.
  - Open the published Pages URL and confirm the demo renders.
- PyPI:
  - Run `Publish To PyPI` manually from `Actions`, or publish a GitHub Release after `AINEWS_ENABLE_PYPI_PUBLISH=true` is set.
  - Confirm the workflow enters the `pypi` environment and the release appears on PyPI.

## How These Workflows Fit Together

- [release.yml](../.github/workflows/release.yml) builds GitHub Release assets from tags.
- [pypi-publish.yml](../.github/workflows/pypi-publish.yml) publishes the built package to PyPI when a GitHub Release is published, or when maintainers dispatch it manually.
- [demo-pages.yml](../.github/workflows/demo-pages.yml) deploys the demo site from `docs/demo/` on `main` changes or manual dispatch.

## Maintainer Audit Checklist

- `Settings` -> `Pages` uses `GitHub Actions` as the source.
- `Settings` -> `Environments` contains `github-pages` and `pypi`.
- PyPI trusted publisher points to `.github/workflows/pypi-publish.yml`.
- `AINEWS_ENABLE_PYPI_PUBLISH=true` is set if automatic PyPI publication is desired.
- The latest `Demo Pages` and `Publish To PyPI` runs are green.

## References

- [GitHub Docs: Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [GitHub Docs: Using custom workflows with GitHub Pages](https://docs.github.com/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [PyPI Docs: Adding a Trusted Publisher to an existing PyPI project](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [PyPI Docs: Creating a PyPI Project with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
