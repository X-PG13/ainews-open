# Configuration Matrix

## Core Runtime

| Variable | Required | Default | Target | Purpose |
| --- | --- | --- | --- | --- |
| `AINEWS_HOME` | No | current working directory | all | Base directory used for `.env`, SQLite, output, and relative paths. |
| `AINEWS_DATABASE_URL` | No | `sqlite:///data/ainews.db` | all | SQLite database location. |
| `AINEWS_SOURCES_FILE` | No | packaged default registry | all | Custom source registry path. |
| `AINEWS_REQUEST_TIMEOUT` | No | `15` | all | HTTP timeout in seconds. |
| `AINEWS_DEFAULT_LOOKBACK_HOURS` | No | `48` | all | Default lookback window for digest and list commands. |
| `AINEWS_MAX_ARTICLES_PER_SOURCE` | No | `40` | all | Cap per source during ingest. |
| `AINEWS_ALLOWED_ORIGINS` | No | `*` | API | CORS allow list. |
| `AINEWS_ADMIN_TOKEN` | Recommended | empty | API/admin | Admin token checked on protected routes. |

## Logging And Operations

| Variable | Required | Default | Target | Purpose |
| --- | --- | --- | --- | --- |
| `AINEWS_LOG_LEVEL` | No | `INFO` | all | Root log level. |
| `AINEWS_LOG_FORMAT` | No | `text` | all | `text` or `json` structured logs. |
| `AINEWS_OUTPUT_DIR` | No | `output` | digest/export | Markdown and JSON export directory. |
| `AINEWS_STATIC_SITE_DIR` | No | `output/site` | static publish | Static site output directory. |
| `AINEWS_STATIC_SITE_BASE_URL` | No | empty | static publish | Canonical base URL inserted into static publish responses. |

## Extraction And LLM

| Variable | Required | Default | Target | Purpose |
| --- | --- | --- | --- | --- |
| `AINEWS_EXTRACTION_TEXT_LIMIT` | No | `12000` | extraction | Max stored extracted text length. |
| `AINEWS_LLM_ARTICLE_CONTEXT_CHARS` | No | `6000` | enrichment | Context sent to the LLM per article. |
| `AINEWS_LLM_PROVIDER` | No | `openai_compatible` | enrichment/digest | LLM provider mode. |
| `AINEWS_LLM_BASE_URL` | Conditional | empty | enrichment/digest | OpenAI-compatible API base URL. |
| `AINEWS_LLM_API_KEY` | Conditional | empty | enrichment/digest | Provider API key. |
| `AINEWS_LLM_MODEL` | Conditional | empty | enrichment/digest | Model name used for enrichment and digest generation. |
| `AINEWS_LLM_TIMEOUT` | No | `60` | enrichment/digest | LLM request timeout in seconds. |
| `AINEWS_LLM_TEMPERATURE` | No | `0.2` | enrichment/digest | LLM temperature. |
| `AINEWS_LLM_DIGEST_MAX_ARTICLES` | No | `12` | digest | Max articles included in generated digests. |

## Publishing Targets

| Variable | Required | Default | Target | Purpose |
| --- | --- | --- | --- | --- |
| `AINEWS_PUBLISH_TARGETS` | No | empty | publish | Comma-separated default publish targets. |
| `AINEWS_TELEGRAM_BOT_TOKEN` | Conditional | empty | Telegram | Bot token for `sendMessage`. |
| `AINEWS_TELEGRAM_CHAT_ID` | Conditional | empty | Telegram | Chat or channel id. |
| `AINEWS_TELEGRAM_DISABLE_NOTIFICATION` | No | `false` | Telegram | Send messages silently. |
| `AINEWS_FEISHU_WEBHOOK` | Conditional | empty | Feishu | Incoming webhook URL. |
| `AINEWS_FEISHU_SECRET` | No | empty | Feishu | Optional webhook secret for signatures. |
| `AINEWS_FEISHU_MESSAGE_TYPE` | No | `text` | Feishu | `text` or `card`. |
| `AINEWS_WECHAT_ACCESS_TOKEN` | Conditional | empty | WeChat | Pre-fetched access token override. |
| `AINEWS_WECHAT_APP_ID` | Conditional | empty | WeChat | App id used when fetching tokens. |
| `AINEWS_WECHAT_APP_SECRET` | Conditional | empty | WeChat | App secret used when fetching tokens. |
| `AINEWS_WECHAT_THUMB_MEDIA_ID` | No | empty | WeChat | Existing thumb media id. |
| `AINEWS_WECHAT_THUMB_IMAGE_PATH` | No | empty | WeChat | Local image path for auto-upload. |
| `AINEWS_WECHAT_THUMB_IMAGE_URL` | No | empty | WeChat | Remote image URL for auto-upload. |
| `AINEWS_WECHAT_THUMB_UPLOAD_TYPE` | No | `thumb` | WeChat | Upload type for cover assets. |
| `AINEWS_WECHAT_AUTHOR` | No | empty | WeChat | Author field for articles. |
| `AINEWS_WECHAT_CONTENT_SOURCE_URL` | No | empty | WeChat | Original source URL field. |
| `AINEWS_WECHAT_NEED_OPEN_COMMENT` | No | `0` | WeChat | Whether comments are enabled. |
| `AINEWS_WECHAT_ONLY_FANS_CAN_COMMENT` | No | `0` | WeChat | Comment scope. |
| `AINEWS_WECHAT_PUBLISH_AFTER_DRAFT` | No | `false` | WeChat | Submit draft immediately after draft creation. |

## Practical Profiles

- Local demo: `AINEWS_LOG_FORMAT=text`, no publish targets, no LLM required.
- Operator API: set `AINEWS_ADMIN_TOKEN`, `AINEWS_LOG_FORMAT=json`, and `AINEWS_PUBLISH_TARGETS`.
- LLM digest pipeline: configure the `AINEWS_LLM_*` group plus at least one publish target or export directory.
- WeChat publishing: prefer `AINEWS_WECHAT_APP_ID` + `AINEWS_WECHAT_APP_SECRET` over a long-lived access token.
