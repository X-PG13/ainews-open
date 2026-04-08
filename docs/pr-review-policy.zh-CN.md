# PR 审核约定

[English](./pr-review-policy.md) · [简体中文](./pr-review-policy.zh-CN.md)

这个仓库用 `CODEOWNERS` 和分支保护来保持协作清晰，同时避免把单维护者工作流锁死。

## 审核基线

- 只要改动涉及行为、契约、workflow、部署或治理文件，就走 PR。
- 合并前保持 `main` 所要求的检查全绿，以 GitHub 保护分支规则为准。
- 使用 PR 模板，把验证方式写清楚。
- 合并前解决 review conversation。

## 审核重点

- 范围：一个 PR 只解决一个边界清晰的问题，不夹带无关重构。
- 行为：任何用户侧或运维侧变化都要在摘要里说清楚。
- 安全：不能暴露密钥、私有地址或内部路径。
- 契约：涉及配置、CLI、API、导出结构、数据库 schema 时，要同步更新文档。
- 验证：测试和手工验证要和改动类型匹配。

## 按改动类型的额外要求

- 新闻源 registry 改动：说明来源理由，并保持 source id 稳定。
- 正文抽取逻辑改动：补或更新 HTML fixture 和回归测试。
- API 或控制台改动：同时补 API 测试和面向运维的文档。
- Release 或 workflow 改动：操作流程变更时，更新发版文档或 checklist。

## CODEOWNERS 用法

- `CODEOWNERS` 为核心代码、文档、workflow 和 release 资产定义默认 owner。
- PR 涉及这些路径时，GitHub 会自动建议对应 owner。
- 当前是单维护者模式，所以 `CODEOWNERS` 先用于明确责任和 review 路由，不强制开启 mandatory code-owner approval，避免把发版流程锁死。

## 单维护者规则

- 在有第二位维护者加入之前，仓库保持 `main` 的 required status checks 和 conversation resolution。
- 当前不强制 `1` 个审批，是因为严格保护下单维护者无法自己满足 mandatory review gate。
- 未来如果有第二位维护者，再把 branch protection 升级成 code-owner review 和至少一个 approval。
