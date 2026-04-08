# 配置矩阵

[English](./configuration.md) · [简体中文](./configuration.zh-CN.md)

## 核心运行时

| 变量 | 是否必填 | 默认值 | 场景 | 作用 |
| --- | --- | --- | --- | --- |
| `AINEWS_HOME` | 否 | 当前命令目录 | 全部 | `.env`、SQLite、输出目录和相对路径的基准目录。 |
| `AINEWS_DATABASE_URL` | 否 | `sqlite:///data/ainews.db` | 全部 | SQLite 数据库位置。 |
| `AINEWS_SOURCES_FILE` | 否 | 内置默认源 | 全部 | 自定义新闻源文件路径。 |
| `AINEWS_REQUEST_TIMEOUT` | 否 | `15` | 全部 | HTTP 超时时间，单位秒。 |
| `AINEWS_DEFAULT_LOOKBACK_HOURS` | 否 | `48` | 全部 | digest 和列表命令的默认回看窗口。 |
| `AINEWS_MAX_ARTICLES_PER_SOURCE` | 否 | `40` | 全部 | 每个源的默认抓取上限。 |
| `AINEWS_ALLOWED_ORIGINS` | 否 | `*` | API | CORS 白名单。 |
| `AINEWS_ADMIN_TOKEN` | 建议 | 空 | API/后台 | 管理接口鉴权 token。 |

## 日志与运维

| 变量 | 是否必填 | 默认值 | 场景 | 作用 |
| --- | --- | --- | --- | --- |
| `AINEWS_LOG_LEVEL` | 否 | `INFO` | 全部 | 日志级别。 |
| `AINEWS_LOG_FORMAT` | 否 | `text` | 全部 | `text` 或 `json` 结构化日志。 |
| `AINEWS_OUTPUT_DIR` | 否 | `output` | 导出 | Markdown / JSON 导出目录。 |
| `AINEWS_STATIC_SITE_DIR` | 否 | `output/site` | 静态站点 | 静态站点输出目录。 |
| `AINEWS_STATIC_SITE_BASE_URL` | 否 | 空 | 静态站点 | 静态站点对外访问基地址。 |
| `AINEWS_SOURCE_COOLDOWN_FAILURE_THRESHOLD` | 否 | `2` | 抽取运维 | 同一来源连续触发 `429/403/challenge` 多少次后进入冷却。 |
| `AINEWS_SOURCE_RECOVERY_SUCCESS_THRESHOLD` | 否 | `2` | 抽取运维 | 来源连续成功多少次后，自动清掉旧的冷却与确认痕迹。 |
| `AINEWS_SOURCE_THROTTLE_COOLDOWN_MINUTES` | 否 | `120` | 抽取运维 | 来源被限流时的基础冷却窗口。 |
| `AINEWS_SOURCE_BLOCKED_COOLDOWN_MINUTES` | 否 | `720` | 抽取运维 | 来源被封锁时的基础冷却窗口。 |
| `AINEWS_SOURCE_RUNTIME_RETENTION_DAYS` | 否 | `45` | 抽取运维 | `source_events` 和 `source_alerts` 在线保留多久后进入归档裁剪。 |
| `AINEWS_ALERT_TARGETS` | 否 | 空 | 运维告警 | 告警目标列表，逗号分隔，例如 `telegram,feishu`。 |
| `AINEWS_ALERT_COOLDOWN_MINUTES` | 否 | `30` | 运维告警 | 同一活动告警指纹的最短重复发送间隔。 |
| `AINEWS_ALERT_TELEGRAM_CHAT_ID` | 否 | 空 | 运维告警 | 告警专用 Telegram 目标，不填时回退到 `AINEWS_TELEGRAM_CHAT_ID`。 |
| `AINEWS_ALERT_FEISHU_WEBHOOK` | 否 | 空 | 运维告警 | 告警专用飞书 webhook，不填时回退到 `AINEWS_FEISHU_WEBHOOK`。 |
| `AINEWS_ALERT_FEISHU_SECRET` | 否 | 空 | 运维告警 | 告警专用飞书签名 secret。 |

## 正文抽取与 LLM

| 变量 | 是否必填 | 默认值 | 场景 | 作用 |
| --- | --- | --- | --- | --- |
| `AINEWS_EXTRACTION_TEXT_LIMIT` | 否 | `12000` | 抽取 | 单篇文章本地保留的最大正文长度。 |
| `AINEWS_LLM_ARTICLE_CONTEXT_CHARS` | 否 | `6000` | 翻译增强 | 送入 LLM 的最大正文上下文字符数。 |
| `AINEWS_LLM_PROVIDER` | 否 | `openai_compatible` | 翻译/日报 | LLM 提供方模式。 |
| `AINEWS_LLM_BASE_URL` | 条件必填 | 空 | 翻译/日报 | OpenAI-compatible API 地址。 |
| `AINEWS_LLM_API_KEY` | 条件必填 | 空 | 翻译/日报 | API key。 |
| `AINEWS_LLM_MODEL` | 条件必填 | 空 | 翻译/日报 | 模型名。 |
| `AINEWS_LLM_TIMEOUT` | 否 | `60` | 翻译/日报 | LLM 请求超时。 |
| `AINEWS_LLM_TEMPERATURE` | 否 | `0.2` | 翻译/日报 | 温度参数。 |
| `AINEWS_LLM_DIGEST_MAX_ARTICLES` | 否 | `12` | 日报 | 参与日报生成的最大文章数。 |

## 发布目标

| 变量 | 是否必填 | 默认值 | 场景 | 作用 |
| --- | --- | --- | --- | --- |
| `AINEWS_PUBLISH_TARGETS` | 否 | 空 | 发布 | 默认发布目标，逗号分隔。 |
| `AINEWS_TELEGRAM_BOT_TOKEN` | 条件必填 | 空 | Telegram | Bot token。 |
| `AINEWS_TELEGRAM_CHAT_ID` | 条件必填 | 空 | Telegram | Chat ID 或频道名。 |
| `AINEWS_TELEGRAM_DISABLE_NOTIFICATION` | 否 | `false` | Telegram | 是否静默推送。 |
| `AINEWS_FEISHU_WEBHOOK` | 条件必填 | 空 | 飞书 | 自定义机器人 webhook。 |
| `AINEWS_FEISHU_SECRET` | 否 | 空 | 飞书 | 可选签名秘钥。 |
| `AINEWS_FEISHU_MESSAGE_TYPE` | 否 | `text` | 飞书 | `text` 或 `card`。 |
| `AINEWS_WECHAT_ACCESS_TOKEN` | 条件必填 | 空 | 微信 | 直接指定 access token。 |
| `AINEWS_WECHAT_APP_ID` | 条件必填 | 空 | 微信 | 自动换 token 时使用的 AppID。 |
| `AINEWS_WECHAT_APP_SECRET` | 条件必填 | 空 | 微信 | 自动换 token 时使用的 AppSecret。 |
| `AINEWS_WECHAT_THUMB_MEDIA_ID` | 否 | 空 | 微信 | 已有封面素材 ID。 |
| `AINEWS_WECHAT_THUMB_IMAGE_PATH` | 否 | 空 | 微信 | 本地封面图路径。 |
| `AINEWS_WECHAT_THUMB_IMAGE_URL` | 否 | 空 | 微信 | 远程封面图 URL。 |
| `AINEWS_WECHAT_THUMB_UPLOAD_TYPE` | 否 | `thumb` | 微信 | 封面上传类型。 |
| `AINEWS_WECHAT_AUTHOR` | 否 | 空 | 微信 | 作者字段。 |
| `AINEWS_WECHAT_CONTENT_SOURCE_URL` | 否 | 空 | 微信 | 原文链接字段。 |
| `AINEWS_WECHAT_NEED_OPEN_COMMENT` | 否 | `0` | 微信 | 是否打开评论。 |
| `AINEWS_WECHAT_ONLY_FANS_CAN_COMMENT` | 否 | `0` | 微信 | 是否仅粉丝可评论。 |
| `AINEWS_WECHAT_PUBLISH_AFTER_DRAFT` | 否 | `false` | 微信 | 草稿创建后是否立即提交发布。 |

## 推荐配置模板

- 本地体验：`AINEWS_LOG_FORMAT=text`，不开发布目标，不配 LLM 也能跑。
- 运维 API：设置 `AINEWS_ADMIN_TOKEN`、`AINEWS_LOG_FORMAT=json`，并配置 `AINEWS_PUBLISH_TARGETS`。
- 抽取运维：优先把 `AINEWS_SOURCE_*` 一组配齐，用它控制来源冷却、自动恢复阈值和运行态历史保留窗口。
- LLM 日报流：配置一组 `AINEWS_LLM_*`，外加至少一个发布目标或导出目录。
- 微信发布：优先使用 `AINEWS_WECHAT_APP_ID + AINEWS_WECHAT_APP_SECRET`，不要长期依赖手填 access token。
