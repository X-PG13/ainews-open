# 部署指南

[English](./deployment.md) · [简体中文](./deployment.zh-CN.md)

这份文档聚焦于两件事：

1. 从 clone 到跑通第一条可用 pipeline
2. 如何把 AI News Open 跑在 Docker、Compose、`systemd` 和 GitHub Actions 上

如果你只是第一次部署，建议先看更短的 [first-deploy.zh-CN.md](./first-deploy.zh-CN.md)。

变量级配置说明见 [configuration.zh-CN.md](./configuration.zh-CN.md)。

## 15 分钟本地跑通

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
cp .env.example .env
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --export
python -m ainews serve --port 8000
```

打开 `http://127.0.0.1:8000/`。

你会得到：

- 本地 SQLite 数据库：`data/`
- 日报导出目录：`output/`
- 运行中的管理台和 API：`8000` 端口

如果你要启用 LLM 中文翻译和日报，请补：

```env
AINEWS_LLM_BASE_URL=...
AINEWS_LLM_API_KEY=...
AINEWS_LLM_MODEL=...
```

然后重新运行：

```bash
python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --export
```

## Docker

构建：

```bash
docker build -t ainews-open:latest .
```

启动：

```bash
docker run --rm -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/output:/app/output" \
  --env-file .env \
  ainews-open:latest
```

如果你想只跑一次 pipeline：

```bash
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/output:/app/output" \
  --env-file .env \
  ainews-open:latest \
  python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --export
```

镜像当前已经包含：

- 内置 `HEALTHCHECK`，检查 `http://127.0.0.1:8000/health`
- 容器内默认 JSON 日志

## Docker Compose

仓库已自带 [compose.yaml](../compose.yaml)。

启动：

```bash
docker compose up --build
```

停止：

```bash
docker compose down
```

默认挂载：

- `./data -> /app/data`
- `./output -> /app/output`

## systemd

示例 unit：

```ini
[Unit]
Description=AI News Open API
After=network.target

[Service]
WorkingDirectory=/srv/ainews-open
Environment=AINEWS_HOME=/srv/ainews-open
ExecStart=/srv/ainews-open/.venv/bin/python -m ainews serve --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
User=ainews
Group=ainews

[Install]
WantedBy=multi-user.target
```

加载并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ainews-open
sudo systemctl status ainews-open
```

如果要做定时日报，可用 timer 或 cron 执行：

```bash
/srv/ainews-open/.venv/bin/python -m ainews run-pipeline --since-hours 48 --limit 30 --max-items 30 --use-llm --export --publish
```

## GitHub Actions

仓库当前已包含这些工作流：

- [ci.yml](../.github/workflows/ci.yml)：矩阵测试、coverage、build
- [smoke.yml](../.github/workflows/smoke.yml)：安装后启动 API 并验证 `/health`
- [release.yml](../.github/workflows/release.yml)：tag 发布、checksum、SBOM、provenance
- [pypi-publish.yml](../.github/workflows/pypi-publish.yml)：PyPI trusted publishing
- [daily-digest.yml](../.github/workflows/daily-digest.yml)：定时生成日报 artifact
- [demo-pages.yml](../.github/workflows/demo-pages.yml)：发布 GitHub Pages demo
- [codeql.yml](../.github/workflows/codeql.yml)：安全扫描

推荐 secrets：

- `AINEWS_LLM_BASE_URL`
- `AINEWS_LLM_API_KEY`
- `AINEWS_LLM_MODEL`
- `AINEWS_TELEGRAM_BOT_TOKEN`
- `AINEWS_TELEGRAM_CHAT_ID`
- `AINEWS_FEISHU_WEBHOOK`
- `AINEWS_WECHAT_APP_ID`
- `AINEWS_WECHAT_APP_SECRET`

## 数据目录

默认路径：

- 数据库：`data/ainews.db`
- 日报导出：`output/`
- 静态站点导出：`output/site/`

真实部署里请确保这些目录可持久化、可备份。

## 正文抽取重试策略

生产环境里，正文抽取重试状态本身就应该视为运维面的一部分。

自动行为：

- `pending`：会进入正常抽取队列
- `throttled`：到达退避时间后自动重试
- `temporary_error`：到达退避时间后自动重试
- `blocked`：重试间隔会更长
- `permanent_error`：不会自动回到重试队列

管理接口 `/admin/articles` 现在支持这些重试过滤参数：

- `extraction_status`
- `extraction_error_category`
- `due_only`

手动重试方式：

```bash
python -m ainews retry-extractions --status throttled --due-only --limit 20
```

```bash
python -m ainews retry-extractions --status blocked --limit 5
```

```bash
curl -X POST http://127.0.0.1:8000/admin/extract/retry \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-token" \
  -d '{"extraction_status":"throttled","due_only":true,"limit":20}'
```

推荐运维闭环：

1. 先看 `/health` 和 `/admin/operations`
2. 再用 `/admin/articles` 过滤出已到重试时间的失败条目
3. 优先重试已到窗口的条目
4. `blocked` 或 `permanent_error` 先人工判断站点行为，再决定是否手动重试

## 来源级冷却策略

正文抽取现在还带一层来源级保护。

当同一个来源连续出现这些保护型失败时：

- `429`
- `403`
- challenge / 反爬页面

AI News Open 会把这个来源打入冷却窗口。冷却期间：

- 默认抽取队列会跳过这个来源的文章
- `/health` 会出现 `source_cooldowns_active`
- `/admin/sources` 和控制台会展示受影响来源以及冷却截止时间
- `/admin/source-alerts` 和控制台会展示最近的来源级告警与恢复历史
- 维护者可以直接确认告警、临时静默告警，或把来源切到维护模式
- 当来源连续成功达到恢复阈值后，系统会自动清掉旧的冷却和确认痕迹
- 如果静默窗口到期后问题还在，来源会在下一次运行态扫描时重新具备发送活动告警的资格

手动解除冷却示例：

```bash
python -m ainews reset-source-cooldowns --source venturebeat
```

```bash
python -m ainews reset-source-cooldowns --all
```

Source Ops 示例：

```bash
python -m ainews ack-source-alerts --source venturebeat --note "已确认限流问题"
```

```bash
python -m ainews snooze-source-alerts --source venturebeat --minutes 60
```

```bash
python -m ainews set-source-maintenance --source venturebeat
```

```bash
python -m ainews prune-source-runtime-history --retention-days 45
```

相关环境变量：

- `AINEWS_SOURCE_COOLDOWN_FAILURE_THRESHOLD`
- `AINEWS_SOURCE_RECOVERY_SUCCESS_THRESHOLD`
- `AINEWS_SOURCE_THROTTLE_COOLDOWN_MINUTES`
- `AINEWS_SOURCE_BLOCKED_COOLDOWN_MINUTES`
- `AINEWS_SOURCE_RUNTIME_RETENTION_DAYS`

## 告警策略

AI News Open 现在可以把关键运维事件发到 Telegram 和飞书。

当前支持的触发条件：

- `/health` 从 `ok` 进入 `degraded`
- 出现活动中的 `source_cooldowns_active`
- 发布失败
- pipeline 进入 `partial_error` 或 `error`

当前行为：

- 告警会按规则和指纹做去重，不会每次任务都刷屏
- 同一类活动告警会遵守最小重复发送间隔
- 当系统恢复正常时，会补发恢复通知

相关环境变量：

- `AINEWS_ALERT_TARGETS`
- `AINEWS_ALERT_COOLDOWN_MINUTES`
- `AINEWS_ALERT_TELEGRAM_CHAT_ID`
- `AINEWS_ALERT_FEISHU_WEBHOOK`
- `AINEWS_ALERT_FEISHU_SECRET`

最小 Telegram 告警配置：

```env
AINEWS_ALERT_TARGETS=telegram
AINEWS_TELEGRAM_BOT_TOKEN=...
AINEWS_ALERT_TELEGRAM_CHAT_ID=@ainews_ops
```

最小飞书告警配置：

```env
AINEWS_ALERT_TARGETS=feishu
AINEWS_ALERT_FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/...
AINEWS_ALERT_FEISHU_SECRET=...
```

运维建议：

- 来源级冷却、最近成功率、失败分类分布、最近操作摘要，优先看 `/admin/sources`
- 来源级告警激活和恢复通知历史，优先看 `/admin/source-alerts`
- 已确认的来源告警，在同一次冷却事件里不会再重复发活动告警
- 处于静默窗口或维护模式的来源，会暂停来源级告警投递；维护模式还会暂停默认抽取队列
- 静默到期后，如果来源仍处于未解决状态，下一次运行态扫描会重新发活动告警
- `prune-source-runtime-history` 默认会先把旧的 `source_events` / `source_alerts` 归档，再从在线表里裁掉
- 告警是通知入口，不是排障终点；收到告警后优先结合 `/health` 和 `/admin/operations` 看上下文

## 升级前检查

升级前建议先做：

1. 备份 `data/ainews.db`
2. 如果你把导出文件当长期产物，也备份 `output/`
3. 阅读 [database-migrations.md](./database-migrations.md)
4. 阅读 [CHANGELOG.md](../CHANGELOG.md)
