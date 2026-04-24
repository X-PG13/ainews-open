# 路线图

[English](./ROADMAP.md) · [简体中文](./ROADMAP.zh-CN.md)

这份路线图只跟踪当前维护者的优先级。已经发布的工作会进入 release note，那里才是历史记录。

## 当前状态

- 稳定版本线：`v1.2.x`
- 最新 release：`v1.2.48`
- 当前开启的 milestone：`v1.2.49`
- 当前唯一明确未完成的 release engineering 项：PyPI trusted publishing 初始化和首次发包

## 进行中：v1.2.49 维护事项

- 为 `ainews-open` 配置 PyPI trusted publisher。
- 在 trusted publisher 初始化完成后，完成第一次 PyPI 发布。
- 持续维护 release automation、checksum 校验、SBOM 生成和 provenance attestation。

## 计划中：v1.3 产品能力

- 提供基于示例 digest 和 API example 的公开 demo 站点。
- 增加面向运维的指标视图和失败历史视图。
- 补齐面向生产深度的 Docker Compose、systemd 和 GitHub Actions 部署方案。
- 继续增强多渠道发布前的最终预览能力。

## 持续推进的内容质量工作

- 继续扩展高价值 AI 媒体站点的 source-specific extraction 规则。
- 为更多中文和国际发布源补充回归夹具。
- 改进 digest 排序和编辑策展流程。
- 继续增强对 syndication-heavy feed 的重复检测能力。

## 最近已完成

- 已启用 GitHub Discussions，并补齐了 issue / discussion 分流规范。
- 已为公开 `v1.x` 契约定义支持窗口和弃用策略。
- 已为 release 产物补齐 checksum、SBOM、provenance 和 smoke 校验。
- 已补齐 GitHub Pages 和 PyPI 初始化所需的 maintainer bootstrap 文档。
- 已把治理、维护者、citation、架构和审核策略文档补进仓库基线。

## 社区与贡献者体验

- 继续把 `good first issue`、`help wanted`、`v1.x` 和 area labels 维护成稳定的分诊元数据。
- 随着时间推进，为 source、extractor 和 publisher 扩展补更多可执行示例。
- 保持 roadmap、milestone 和 release 文档同步，避免功能请求继续落到过时 backlog 上。
