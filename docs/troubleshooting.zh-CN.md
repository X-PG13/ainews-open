# 故障排查

[English](./troubleshooting.md) · [简体中文](./troubleshooting.zh-CN.md)

这份文档覆盖 AI News Open 最常见的运维问题。

## pipeline 跑了，但没有文章

先检查：

- 执行 `python -m ainews list-sources`，确认源能正常加载
- 执行 `python -m ainews ingest`，查看每个源的状态
- 检查当前环境是否有外网访问能力
- 检查 `include_keywords` / `exclude_keywords` 是否把文章过滤掉了

## 正文抽取提示 “extracted article text is too short”

这通常意味着：

- feed 条目存在
- 文章页面可以访问
- 但抽取器没有抓到足够多的正文内容

建议动作：

- 检查原始文章页面
- 在 [content_extractor.py](../src/ainews/content_extractor.py) 里新增或调整站点专用 selector
- 调整前先补 fixture 和回归测试

## 正文抽取为什么没有立刻重试

这通常是预期行为。

AI News Open 现在会把正文抽取失败分成：

- `throttled`
- `blocked`
- `temporary_error`
- `permanent_error`

默认重试策略：

- `throttled`：按退避时间自动重试
- `temporary_error`：按较短退避时间自动重试
- `blocked`：重试频率会明显更低，面向反爬或访问控制场景
- `permanent_error`：不会自动重试

建议先看：

- `python -m ainews stats`
- `curl http://127.0.0.1:8000/health`
- `curl -H "X-Admin-Token: your-secret-token" "http://127.0.0.1:8000/admin/articles?extraction_status=throttled&due_only=true"`

手动重试示例：

```bash
python -m ainews retry-extractions --status throttled --due-only --limit 20
```

```bash
python -m ainews retry-extractions --status blocked --limit 5
```

API 示例：

```json
{
  "extraction_status": "throttled",
  "due_only": true,
  "limit": 20
}
```

把这段 JSON 以 `POST` 方式发到 `/admin/extract/retry`，并带上 `X-Admin-Token`。

## 某个来源突然不再继续抽取，`/health` 里出现 `source_cooldowns_active`

这表示来源级保护逻辑已经把某个发布源打入冷却，通常原因是连续出现了
`429`、`403` 或 challenge/反爬页面。

建议先看：

- `python -m ainews list-sources --runtime`
- `curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/sources`
- `curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/source-alerts`
- 重点看 `cooldown_status`、`cooldown_until`、`consecutive_failures`、`last_http_status`
- 再看最近的来源级告警和恢复记录，确认这次冷却是否已经发出通知
- 再确认 `silenced_until`、`maintenance_mode`、`acknowledged_at`、`ack_note`，避免把静默或维护误判成告警失效

如果确认这个来源可以恢复，可以手动解除冷却：

```bash
python -m ainews reset-source-cooldowns --source venturebeat
```

或者解除全部活动冷却：

```bash
python -m ainews reset-source-cooldowns --all
```

API 示例：

```json
{"source_ids": ["venturebeat"], "active_only": false}
```

把这段 JSON 以 `POST` 方式发到 `/admin/sources/cooldowns/reset`，并带上 `X-Admin-Token`。

## 告警没有发出，或者感觉太吵

先检查：

- `AINEWS_ALERT_TARGETS` 是否设成了 `telegram`、`feishu` 或两者
- 告警专用目标是否真的配置了
- Telegram 告警需要 `AINEWS_TELEGRAM_BOT_TOKEN`，以及 `AINEWS_ALERT_TELEGRAM_CHAT_ID` 或 `AINEWS_TELEGRAM_CHAT_ID`
- 飞书告警需要 `AINEWS_ALERT_FEISHU_WEBHOOK` 或 `AINEWS_FEISHU_WEBHOOK`

当前预期行为：

- 同一活动告警会按规则和指纹去重
- 重发窗口由 `AINEWS_ALERT_COOLDOWN_MINUTES` 控制
- 故障恢复后，系统会补发恢复通知

如果你认为应该发新告警却没收到：

- 检查这次事件的指纹是否真的变化了
- 结合 `/health` 和 `/admin/operations` 确认系统是否仍处于失败态
- 查日志里的 `alert.target_error`

如果你觉得告警太吵：

- 调大 `AINEWS_ALERT_COOLDOWN_MINUTES`
- 用 `AINEWS_ALERT_*` 单独配置告警目标，不要和业务发布目标混用
- 到 `/admin/sources` 看看到底是哪个来源在重复触发冷却或 blocked 失败
- 到 `/admin/source-alerts` 看同一个来源是不是在反复进入和退出冷却
- 如果这次问题已经有人处理，先确认告警，避免同一轮冷却重复刷活动告警
- 如果只是短时限流，先临时静默这个来源
- 如果要暂停该来源的默认抽取和来源级告警，直接切到维护模式
- 如果静默到期后来源问题还在，下一次运行态扫描会重新发活动告警
- 如果 SQLite 里的来源历史太多，可以用 `prune-source-runtime-history` 做归档裁剪

CLI 示例：

```bash
python -m ainews ack-source-alerts --source venturebeat --note "由值班同学接手"
python -m ainews snooze-source-alerts --source venturebeat --minutes 120
python -m ainews set-source-maintenance --source venturebeat
python -m ainews set-source-maintenance --source venturebeat --disable
python -m ainews prune-source-runtime-history --retention-days 45
```

## LLM 日报没有生成

先检查：

- `AINEWS_LLM_BASE_URL`
- `AINEWS_LLM_API_KEY`
- `AINEWS_LLM_MODEL`
- 命令或接口里是否真的带了 `--use-llm`

当前行为是：

- 如果 LLM 没配置或调用失败，系统会自动回退到规则模板 digest
- 这是预期降级行为，不是 crash

## Google News 文章在抽取时显示 `skipped`

这是 `news.google.com` 聚合壳页的预期行为。

- Google News 的 RSS 链接经常落到 Google 自己的壳页，而不是原始媒体正文页
- AI News Open 现在会把这类页面标记成 `skipped`，而不是 `error`
- 默认抽取队列不会反复重试这些条目，`/health` 也不会因此降级

如果你确实需要正文，应优先使用原始媒体链接，而不是 Google News 包装链接。

## 发布返回 `skipped`

这表示：

- 同一个已存档 digest 已经发到过同一个 target
- 且最近一次该 `digest_id + target` 的状态是 `ok` 或 `pending`

这就是默认的幂等保护。

如果你明确要再次推送：

```bash
python -m ainews publish --digest-id 1 --target static_site --force-republish
```

或通过 API：

```json
{"digest_id": 1, "targets": ["static_site"], "force_republish": true}
```

## 微信公众号在建草稿前就失败

常见原因：

- 没有 `AINEWS_WECHAT_ACCESS_TOKEN`
- 没有配置 `AINEWS_WECHAT_APP_ID` 或 `AINEWS_WECHAT_APP_SECRET`
- `AINEWS_WECHAT_THUMB_MEDIA_ID` 无效
- `AINEWS_WECHAT_THUMB_IMAGE_PATH` 不存在
- 上传封面图不是 JPG，或大于 `64KB`

## 静态站点文件没有生成

先检查：

- `AINEWS_OUTPUT_DIR`
- `AINEWS_STATIC_SITE_DIR`
- 命令里是否使用了 `--export` 或目标 `static_site`
- 输出目录是否有写权限

## 我需要更强的运维追踪能力

先检查：

- 把 `AINEWS_LOG_LEVEL` 设成 `INFO` 或 `DEBUG`
- 把 `AINEWS_LOG_FORMAT` 设成 `json`
- 用 API 响应头里的 `X-Request-ID` 对日志
- 查 `/health` 里的 `ready`、`degraded_reasons`、最近操作时长和失败分类
- 查 `/admin/operations` 里的 `ingest`、`extract`、`enrich`、`digest`、`publish`、`pipeline`
- 用 `/admin/articles` 的 `extraction_status`、`extraction_error_category`、`due_only` 过滤重试队列

## health 显示 `degraded`

这表示：

- 服务还活着
- 数据库和源配置可用
- 但已经观测到一个或多个运维级错误分类

典型原因：

- `article_extraction_errors`
- `llm_enrichment_errors`
- `publication_errors`
- `recent_pipeline_errors`

建议先看：

- `python -m ainews stats`
- `curl http://127.0.0.1:8000/health`
- `curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/operations`

## GitHub contributors 或统计不对

先检查：

- commit email 是否与 GitHub 已验证邮箱一致
- force push 或历史重写后，GitHub 统计是否还在重算

## 如何确认数据库迁移状态

执行：

```bash
python -m ainews stats
```

或：

```bash
curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/stats
```

重点看：

- `schema_version`
- 文章数
- digest 数
- publication 数
