# 监控接入

[English](./monitoring.md) · [简体中文](./monitoring.zh-CN.md)

AI News Open 现在提供 Prometheus 兼容的 `/metrics` 端点，以及一个定时执行的 housekeeping 工作流，用于裁剪旧的来源运行态历史。

## Metrics 端点

启动 API 后直接抓取：

```text
http://127.0.0.1:8000/metrics
```

这个端点不要求 admin token，返回的是 Prometheus 文本格式。

核心指标：

- `ainews_pipeline_runs_total{status=...}`：当前进程启动以来完成的 pipeline 次数
- `ainews_extract_failures_total{category=...}`：按错误类别聚合的正文抽取失败次数，统计 live 和 archive 两部分历史
- `ainews_source_cooldowns_active`：当前活动中的来源冷却数量
- `ainews_source_recoveries_total`：来源冷却恢复次数，统计 live 和 archive 两部分历史
- `ainews_alert_sends_total`：成功发送的告警和恢复通知总数
- `ainews_operation_runs_total{name=...,status=...}`：当前进程启动以来完成的操作次数

## Prometheus 抓取配置示例

```yaml
scrape_configs:
  - job_name: ainews-open
    metrics_path: /metrics
    static_configs:
      - targets:
          - 127.0.0.1:8000
```

如果 AI News Open 在反向代理后面，请把 `targets` 改成你的真实对外 API 地址。

## 推荐 Grafana 面板

- 活动中的来源冷却数：`ainews_source_cooldowns_active`
- 按类别统计抽取失败：
  `sum by (category) (increase(ainews_extract_failures_total[6h]))`
- Pipeline 运行结果：
  `sum by (status) (increase(ainews_pipeline_runs_total[24h]))`
- 告警发送量：
  `increase(ainews_alert_sends_total[24h])`

## 告警规则示例

```yaml
groups:
  - name: ainews-open
    rules:
      - alert: AINewsSourceCooldownsActive
        expr: ainews_source_cooldowns_active > 0
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: AI News Open 出现活动中的来源冷却
          description: 有一个或多个来源至少 15 分钟仍处于冷却状态。

      - alert: AINewsPipelineErrors
        expr: increase(ainews_pipeline_runs_total{status=~"partial_error|error"}[30m]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: AI News Open pipeline 出现错误
          description: 最近 30 分钟内至少有一次 pipeline 以 partial_error 或 error 结束。

      - alert: AINewsBlockedExtractionSpike
        expr: increase(ainews_extract_failures_total{category="blocked"}[30m]) >= 3
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: AI News Open blocked 抽取失败明显增多
          description: 最近 30 分钟内 blocked 类抽取失败明显抬升。
```

## Housekeeping 工作流

仓库已经带了 [.github/workflows/housekeeping.yml](../.github/workflows/housekeeping.yml)，默认每周跑一次，也可以手动触发。

它执行的是：

```bash
python -m ainews prune-source-runtime-history --retention-days 45
```

注意：

- 这个工作流最适合 self-hosted runner，或任何 `AINEWS_DATABASE_URL` 指向持久化存储的环境
- 如果你用的是 GitHub-hosted runner 且数据库还是默认本地 SQLite，这个工作流只会清理临时 runner 文件系统里的数据库
- 如果你希望它清理真实运行中的数据库，建议配置仓库变量，例如 `AINEWS_DATABASE_URL` 和 `AINEWS_SOURCE_RUNTIME_RETENTION_DAYS`
