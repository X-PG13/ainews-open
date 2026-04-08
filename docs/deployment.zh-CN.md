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

## 升级前检查

升级前建议先做：

1. 备份 `data/ainews.db`
2. 如果你把导出文件当长期产物，也备份 `output/`
3. 阅读 [database-migrations.md](./database-migrations.md)
4. 阅读 [CHANGELOG.md](../CHANGELOG.md)
