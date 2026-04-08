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

## LLM 日报没有生成

先检查：

- `AINEWS_LLM_BASE_URL`
- `AINEWS_LLM_API_KEY`
- `AINEWS_LLM_MODEL`
- 命令或接口里是否真的带了 `--use-llm`

当前行为是：

- 如果 LLM 没配置或调用失败，系统会自动回退到规则模板 digest
- 这是预期降级行为，不是 crash

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
