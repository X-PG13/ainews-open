# 社区分流规范

[English](./community-triage.md) · [简体中文](./community-triage.zh-CN.md)

这个仓库把 GitHub Issues 用于可执行、可跟踪的工作项，把 GitHub Discussions 用于提问、想法验证和社区知识沉淀。

## 适合开 GitHub Issue 的情况

- 可复现的 bug 和回归问题。
- 问题定义清楚、预期结果明确的功能请求。
- 边界明确的文档缺陷或运维流程缺口。
- 需要一路跟踪到完成的 release、打包、CI 或兼容性问题。

## 适合开 GitHub Discussion 的情况

- 安装、配置、发布链路或升级相关的使用问题。
- 还在明确问题边界、API 设计或流程取舍的早期想法。
- 部署经验、样例日报、效果截图等 showcase 内容。
- 不对应某个明确缺陷的社区流程或仓库协作问题。

## 建议的 Discussions 分类

- `Q&A`：使用帮助、排障建议、配置问题和运维操作问答。
- `Ideas`：还没收敛成可执行 issue 的能力提案、流程变更和 roadmap 探索。
- `Show and Tell`：Demo、截图、部署经验和线上使用反馈。
- `General`：治理、协作流程或其他不适合放进上面分类的话题。

## 维护者分诊规则

- 对于没有直接实施任务的使用问题或宽泛设计讨论，优先从 Issues 引导到 Discussions。
- 深入分诊前，先要求 bug 报告在最新受支持 release 或 `main` 上复现。
- 当 issue 还需要设计澄清、暂时不能直接实施时，使用 `discussion` 标签。
- 只有当 issue 已经清晰到其他贡献者可以接手时，才加 `good first issue` 或 `help wanted`。
- 范围明确后，再补 `source`、`extractor`、`publisher`、`docs`、`operations` 等领域标签。
- 私密漏洞不要在公开线程里讨论，统一引导到 `SECURITY.md` 和 GitHub Security Advisories。

## Issue 和 Discussion 之间如何切换

- 如果某个 Discussion 已经收敛成边界清晰的实施任务，就新开一个 Issue，并回链到原讨论。
- 如果某个 Issue 实际上是支持问题、早期想法或 showcase 内容，就关闭并引导到对应的 Discussion 分类。
- 最终可执行的决定保留在 Issue 里，这样 PR、milestone 和 release note 仍然有唯一的跟踪入口。
