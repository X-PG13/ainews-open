# 维护者初始化清单

[English](./maintainer-bootstrap.md) · [简体中文](./maintainer-bootstrap.zh-CN.md)

这份文档记录维护者第一次启用 GitHub Pages 和 PyPI 发布时需要完成的一次性仓库设置，避免每次都靠猜 GitHub / PyPI 的界面选项。

## 这份文档覆盖什么

- 通过 [demo-pages.yml](../.github/workflows/demo-pages.yml) 发布 GitHub Pages demo
- 通过 [pypi-publish.yml](../.github/workflows/pypi-publish.yml) 启用 PyPI trusted publishing
- 这两条 workflow 依赖的仓库变量和 environment 名称

## 当前仓库使用的固定值

如果你 fork 或改名了仓库，先把下面这些值替换成你自己的，再去配置外部服务：

- GitHub owner：`X-PG13`
- GitHub 仓库名：`ainews-open`
- 默认分支：`main`
- PyPI 项目名：`ainews-open`
- GitHub Pages artifact 路径：`docs/demo/`
- PyPI workflow 文件：`.github/workflows/pypi-publish.yml`
- GitHub Pages workflow 文件：`.github/workflows/demo-pages.yml`

## GitHub Pages 一次性设置

1. 打开 GitHub 仓库 `Settings` -> `Pages`。
2. 在 `Build and deployment` 下，把 `Source` 设为 `GitHub Actions`。
3. 保留 [demo-pages.yml](../.github/workflows/demo-pages.yml) 作为发布 workflow。它会上传 `docs/demo/`，并通过 `github-pages` environment 部署。
4. 第一次可以从 `Actions` -> `Demo Pages` -> `Run workflow` 手动触发，也可以直接往 `main` 推送一笔涉及 `docs/demo/` 的改动。
5. 第一次成功部署后，去 `Settings` -> `Environments` 确认 `github-pages` environment 已经出现在 Pages 部署任务对应的环境列表里。
6. 如果你想把 Pages 部署限制在默认分支上，可以给 `github-pages` 加 deployment protection rule，这也符合 GitHub 对 Pages workflow 的推荐做法。
7. 最后确认 `Settings` -> `Pages` 里已经显示站点 URL，并且 demo 页面能正常打开。

注意：

- GitHub Pages 一旦发布，对公网就是可访问的；即使仓库是私有仓库，在支持的套餐下站点本身仍然是公开的。
- 如果之后要绑自定义域名，请在 `Settings` -> `Pages` 里配置；单独提交一个 `CNAME` 文件并不够。

## PyPI Trusted Publishing 一次性设置

1. 打开 GitHub 仓库 `Settings` -> `Environments` -> `New environment`。
2. 新建一个名字必须精确为 `pypi` 的 environment。
3. 如果你希望发布前有人审批，可以在 `pypi` 上额外加 required reviewers 或 wait timer。
4. 打开 GitHub 仓库 `Settings` -> `Secrets and variables` -> `Actions` -> `Variables`。
5. 新增一个 repository variable：`AINEWS_ENABLE_PYPI_PUBLISH=true`。这样发布 GitHub Release 时才会自动触发 PyPI 上传。
6. 在 PyPI 里，按你的场景走其中一种：
   - 已有项目：进入 `ainews-open` 项目页，然后点 `Manage` -> `Publishing` -> `Add a publisher`
   - 还没有项目：进入你自己的 PyPI 账号 `Publishing` 页面，为 `ainews-open` 新增一个 pending publisher
7. 在 PyPI 的 GitHub Actions publisher 表单里，填下面这些值：
   - Owner：`X-PG13`
   - Repository name：`ainews-open`
   - Workflow filename：`.github/workflows/pypi-publish.yml`
   - Environment name：`pypi`
   - 如果是 pending publisher，再填 Project name：`ainews-open`
8. 保存 publisher。这里不需要单独配置 PyPI API token secret，因为 [pypi-publish.yml](../.github/workflows/pypi-publish.yml) 走的是 OIDC trusted publishing，只需要 `id-token: write`。

## 完成设置后的首次验证

- GitHub Pages：
  - 手动跑一次 `Demo Pages`，确认成功部署到 `github-pages`
  - 打开 Pages URL，确认 demo 页面能渲染
- PyPI：
  - 手动触发一次 `Publish To PyPI`，或者在 `AINEWS_ENABLE_PYPI_PUBLISH=true` 后发布一个 GitHub Release
  - 确认 workflow 进入了 `pypi` environment，并且新版本已经出现在 PyPI 上

## 这几条 Workflow 之间的关系

- [release.yml](../.github/workflows/release.yml) 负责基于 tag 构建 GitHub Release 资产
- [pypi-publish.yml](../.github/workflows/pypi-publish.yml) 会在 GitHub Release 发布后把包发到 PyPI，或者由维护者手动触发
- [demo-pages.yml](../.github/workflows/demo-pages.yml) 会在 `main` 上的 demo 变更或手动触发时部署 `docs/demo/`

## 依赖升级策略

Dependabot PR 只作为升级通知，不视为可以直接合并的维护者提交。

维护者不应把 Dependabot PR 直接 merge 到 `main`。如果确认需要升级某个依赖或 GitHub Actions：

1. 先阅读 Dependabot PR，确认升级范围、release notes 和兼容性风险。
2. 从 `main` 新建一个由维护者提交的 review 分支。
3. 在这个分支上应用同样的依赖升级，并运行常规检查。
4. 开启并合并这个由维护者提交的 PR。
5. 人工 PR 合并后，关闭原来的 Dependabot PR。

这样可以保留依赖升级的可审查性，同时避免默认分支出现 bot-authored commits。

## 维护者快速自检

- `Settings` -> `Pages` 的 `Source` 已经是 `GitHub Actions`
- `Settings` -> `Environments` 里有 `github-pages` 和 `pypi`
- PyPI trusted publisher 指向 `.github/workflows/pypi-publish.yml`
- 如果想自动发 PyPI，`AINEWS_ENABLE_PYPI_PUBLISH=true` 已设置
- 最近一次 `Demo Pages` 和 `Publish To PyPI` workflow 都是绿色

## 参考资料

- [GitHub Docs: Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [GitHub Docs: Using custom workflows with GitHub Pages](https://docs.github.com/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [PyPI Docs: Adding a Trusted Publisher to an existing PyPI project](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [PyPI Docs: Creating a PyPI Project with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
