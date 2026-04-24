# 支持生命周期

[English](./support-lifecycle.md) · [简体中文](./support-lifecycle.zh-CN.md)

这份文档定义 AI News Open 公开版本的支持窗口和弃用策略。

## 支持状态

AI News Open 对当前稳定 major 线使用三种发布状态。

- `Active support`：当前 major 线里最新发布的 minor。维护者会在这里接收 bug 修复、文档更新、安全指导和常规兼容性澄清。
- `Maintenance support`：当前 major 线里紧邻最新版本的上一个 minor。维护者仍会处理升级指导、回归问题和安全指导，但回补修复是 best-effort，新修复默认优先落在最新 minor。
- `Unsupported`：比“上一个 minor”更老的版本，以及所有历史 `0.x` 版本。

## 按 Minor 推进的支持窗口

支持窗口随着 minor 版本向前滚动。

以 `v1.x` 为例：

- 当 `1.2.x` 是最新发布的 minor 时，`1.2.x` 属于 `Active support`
- `1.1.x` 属于 `Maintenance support`
- `1.0.x` 及更老版本属于 `Unsupported`

当 `1.3.0` 发布后：

- `1.3.x` 变成 `Active support`
- `1.2.x` 变成 `Maintenance support`
- `1.1.x` 及更老版本变成 `Unsupported`

这样可以让支持策略可预测，同时避免对单维护者仓库承诺长期 backport 分支。

## 各支持状态下维护者实际支持什么

### Active Support

- bug 修复和行为回归
- 文档修正和运维指导
- 安全指导和发版后跟进
- 面向公共契约的兼容性澄清

### Maintenance Support

- 升级到最新 minor 的指导
- 安全指导
- 严重回归问题的酌情处理

`Maintenance support` 不承诺回补修复。如果修复只落在最新 minor，推荐路径就是升级。

### Unsupported

- 历史版本仍可作为参考
- 维护者可以视情况回答问题，但不再隐含兼容性保证
- 新修复不应再针对这些版本回补

## 弃用策略

弃用策略适用于 [compatibility.md](./compatibility.md) 里定义的公共契约，包括文档化的环境变量、CLI flag、HTTP 路由和导出的 JSON 字段。

规则：

- 第一次引入弃用时，要在 `CHANGELOG.md` 里明确记录
- 相关文档里要给出替代方案或迁移说明
- 在可行情况下，弃用后的旧契约应持续接受到当前 major 线结束
- 默认只在下一个 major 版本做硬删除

对当前 `v1.x` 线，默认策略是：

- 可以在某个 minor 版本里引入弃用声明
- 除非出现安全或稳定性问题，否则被弃用的公共契约会一直保留到 `v1.x` 结束
- 真正移除应等待 `v2.0.0`

## 例外路径

如果某个已弃用行为因为安全、稳定性或外部平台变化而不能继续保留：

1. 在 `CHANGELOG.md` 里说明原因
2. 发布迁移说明或 fallback 行为
3. 在可行时保留兼容桥接
4. 在 release note 里明确写出停用旧行为的运维影响

## 相关文档

- [SUPPORT.md](../SUPPORT.md)
- [Compatibility Contract](./compatibility.md)
- [Release Checklist](./release-checklist.md)
