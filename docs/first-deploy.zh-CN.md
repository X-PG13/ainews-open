# 首次部署指南

[English](./first-deploy.md) · [简体中文](./first-deploy.zh-CN.md)

这份文档面向第一次部署 AI News Open 的维护者，目标不是讲全，而是让你尽快从 `git clone` 走到“服务可用”。

## 目标

达到下面这个状态：

- `/health` 正常返回
- 浏览器里能打开管理台
- 跑一条 pipeline 后，`output/` 里能看到日报导出
- 你知道自己场景下哪些环境变量是必须配置的

## 10 分钟本地部署路径

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
cp .env.example .env
python -m ainews run-pipeline --since-hours 48 --limit 20 --max-items 20 --export
python -m ainews serve --port 8000
```

然后打开：

```text
http://127.0.0.1:8000/
```

此时你应该已经得到：

- 本地数据库：`data/ainews.db`
- 日报导出目录：`output/`
- 运行中的 API 和管理台：`8000` 端口

## 最小配置模板

### 本地体验

只需要复制 `.env.example`，保留默认值即可。

### 启用 LLM 生成日报

增加：

```env
AINEWS_LLM_BASE_URL=...
AINEWS_LLM_API_KEY=...
AINEWS_LLM_MODEL=...
```

### 发布到 Telegram

增加：

```env
AINEWS_PUBLISH_TARGETS=telegram
AINEWS_TELEGRAM_BOT_TOKEN=...
AINEWS_TELEGRAM_CHAT_ID=...
```

### 发布到飞书

增加：

```env
AINEWS_PUBLISH_TARGETS=feishu
AINEWS_FEISHU_WEBHOOK=...
```

### 发布到微信公众号

最少需要：

```env
AINEWS_PUBLISH_TARGETS=wechat
AINEWS_WECHAT_APP_ID=...
AINEWS_WECHAT_APP_SECRET=...
AINEWS_WECHAT_THUMB_MEDIA_ID=...
```

## 第一次上生产前的检查清单

正式对外前，建议至少确认：

1. 已设置 `AINEWS_ADMIN_TOKEN`
2. 已设置 `AINEWS_LOG_FORMAT=json`
3. `data/` 和 `output/` 已挂载到持久化存储
4. `/health` 返回 `ready: true`
5. 至少手动跑过一次 `run-pipeline`
6. 先打通一个发布目标，再逐步打开多个渠道

## 服务启动后建议立刻执行的命令

```bash
python -m ainews list-sources
python -m ainews stats
python -m ainews run-pipeline --since-hours 48 --limit 20 --max-items 20 --export
python -m ainews publish --target static_site --persist --export
```

## 出问题时先看哪里

- [troubleshooting.md](./troubleshooting.md)
- [configuration.md](./configuration.md)
- API 响应头里的 `X-Request-ID`

## 下一步

第一次部署跑通后，再继续看：

- [deployment.md](./deployment.md)：Docker、Compose、`systemd`、GitHub Actions
- [use-cases.zh-CN.md](./use-cases.zh-CN.md)：不同使用场景下的推荐落地方式
