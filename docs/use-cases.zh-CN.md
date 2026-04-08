# 使用场景

[English](./use-cases.md) · [简体中文](./use-cases.zh-CN.md)

这份文档的目的不是重复功能列表，而是告诉你这个项目在真实场景里应该怎么用。

## 个人日报维护者

适合你只是想搭一套自己的 AI 新闻日报，不想一开始就接很多外部平台。

推荐配置：

- 本地 SQLite
- 先不开 LLM
- 用 `static_site` 导出结果，方便人工检查

推荐命令：

```bash
python -m ainews run-pipeline --since-hours 48 --limit 20 --max-items 20 --persist --export
python -m ainews publish --digest-id 1 --target static_site
```

为什么适合：

- 搭建成本最低
- 导出物最容易检查
- 第一天不需要任何渠道凭证

## 国际 AI 新闻中文编译流

适合内容团队把海外 AI 新闻翻成中文，再生成日报或进行人工编辑。

推荐配置：

- 配置 LLM
- 开启管理 token
- 以后台控制台作为主要操作面

推荐命令：

```bash
python -m ainews extract --since-hours 48 --limit 30
python -m ainews enrich --since-hours 48 --limit 30
python -m ainews print-digest --use-llm --persist
```

为什么适合：

- 先抓正文，再送入 LLM，质量更稳定
- 报告生成后仍可人工复核
- 后台支持置顶、隐藏、补备注等编辑动作

## 团队群播报工作流

适合每天把 AI 新闻日报同步推到 Telegram 或飞书群。

推荐配置：

- GitHub Actions 或服务器定时任务
- `telegram` 和/或 `feishu`
- 开启结构化日志

推荐命令：

```bash
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --persist --export --publish --target telegram
```

为什么适合：

- 一条命令覆盖抓取、正文、翻译、日报、导出和发布
- 已持久化的 digest 方便审计和追踪
- 默认幂等，不会对同一份 digest 重复外发

## 公众号运营流程

适合最终发布目标是微信公众号的场景。

推荐配置：

- 配好公众号 AppID / AppSecret
- 配好封面素材或自动上传封面
- 保留刷新发布状态的流程

推荐命令：

```bash
python -m ainews publish --use-llm --persist --target wechat --wechat-submit
python -m ainews refresh-publications --target wechat --limit 20
```

为什么适合：

- 草稿创建和提交发布可以在同一条流里完成
- 发布记录会持久化保留
- 后续可以继续轮询正式发布状态

## Demo 与对外展示

适合在还没接真实渠道前，先给贡献者、用户或团队看项目实际输出长什么样。

推荐素材：

- [docs/demo/index.html](./demo/index.html)
- [docs/demo/sample-digest.md](./demo/sample-digest.md)
- [docs/demo/sample-digest.en.md](./demo/sample-digest.en.md)
- [docs/demo/sample-health.json](./demo/sample-health.json)
- [docs/demo/sample-publications.json](./demo/sample-publications.json)
