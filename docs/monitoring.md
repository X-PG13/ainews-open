# Monitoring

[English](./monitoring.md) · [简体中文](./monitoring.zh-CN.md)

AI News Open exposes a Prometheus-compatible `/metrics` endpoint, a ready-to-run Docker Compose monitoring profile, and a scheduled housekeeping workflow for pruning old source runtime history.

## Metrics Endpoint

Start the API and scrape:

```text
http://127.0.0.1:8000/metrics
```

The endpoint does not require the admin token. It returns Prometheus text exposition.

Core metrics:

- `ainews_pipeline_runs_total{status=...}`: completed pipeline runs since process start
- `ainews_extract_failures_total{category=...}`: extraction failures grouped by error category, summed across live and archived source runtime history
- `ainews_source_cooldowns_active`: current number of active source cooldowns
- `ainews_source_recoveries_total`: recovered source cooldown incidents, summed across live and archived source runtime history
- `ainews_alert_sends_total`: successful alert deliveries and recoveries
- `ainews_operation_runs_total{name=...,status=...}`: completed operations since process start

## Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: ainews-open
    metrics_path: /metrics
    static_configs:
      - targets:
          - 127.0.0.1:8000
```

If AI News Open is behind a reverse proxy, scrape the published API address instead.

## Ready-To-Run Docker Compose Monitoring

The repository ships monitoring assets under `deploy/`:

- `deploy/prometheus/prometheus.yml`
- `deploy/prometheus/rules.yml`
- `deploy/grafana/ainews-dashboard.json`

Start the API, Prometheus, and Grafana together:

```bash
docker compose --profile monitoring up --build
```

Default local URLs:

- AI News Open API: `http://127.0.0.1:8000`
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

Grafana defaults to `admin / admin` in the local compose profile. Change those values before exposing the stack beyond a local machine.

## Suggested Grafana Panels

- Active source cooldowns: `ainews_source_cooldowns_active`
- Extraction failures by category:
  `sum by (category) (increase(ainews_extract_failures_total[6h]))`
- Pipeline run outcomes:
  `sum by (status) (increase(ainews_pipeline_runs_total[24h]))`
- Alert delivery volume:
  `increase(ainews_alert_sends_total[24h])`

## Example Alert Rules

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
          summary: AI News Open has active source cooldowns
          description: One or more sources are in cooldown for at least 15 minutes.

      - alert: AINewsPipelineErrors
        expr: increase(ainews_pipeline_runs_total{status=~"partial_error|error"}[30m]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: AI News Open pipeline reported errors
          description: A pipeline run finished with partial_error or error in the last 30 minutes.

      - alert: AINewsBlockedExtractionSpike
        expr: increase(ainews_extract_failures_total{category="blocked"}[30m]) >= 3
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: AI News Open is seeing blocked extraction failures
          description: Blocked extraction failures spiked in the last 30 minutes.
```

## Housekeeping Workflow

The repository includes [.github/workflows/housekeeping.yml](../.github/workflows/housekeeping.yml), which runs weekly and can also be triggered manually.

It executes:

```bash
python -m ainews prune-source-runtime-history --retention-days 45
```

Notes:

- the workflow is most useful on a self-hosted runner or any environment where `AINEWS_DATABASE_URL` points to persistent storage
- if you use GitHub-hosted runners with the default local SQLite path, the workflow only prunes that temporary runner filesystem
- set repository variables such as `AINEWS_DATABASE_URL` and `AINEWS_SOURCE_RUNTIME_RETENTION_DAYS` if you want the workflow to target a real persisted database
