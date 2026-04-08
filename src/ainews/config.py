from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__

PACKAGE_ROOT = Path(__file__).resolve().parent


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass
class Settings:
    database_path: Path
    sources_file: Path
    base_dir: Path = field(default_factory=lambda: Path(".").resolve())
    output_dir: Path = field(default_factory=lambda: Path("output").resolve())
    static_site_dir: Path = field(default_factory=lambda: Path("output/site").resolve())
    request_timeout: int = 15
    default_lookback_hours: int = 48
    max_articles_per_source: int = 40
    allowed_origins: str = "*"
    admin_token: str = ""
    user_agent: str = f"ainews-open/{__version__} (open-source AI news toolkit)"
    log_level: str = "INFO"
    log_format: str = "text"
    extraction_text_limit: int = 12000
    source_cooldown_failure_threshold: int = 2
    source_throttle_cooldown_minutes: int = 120
    source_blocked_cooldown_minutes: int = 720
    alert_targets: str = ""
    alert_cooldown_minutes: int = 30
    alert_telegram_chat_id: str = ""
    alert_feishu_webhook: str = ""
    alert_feishu_secret: str = ""
    llm_article_context_chars: int = 6000
    llm_provider: str = "openai_compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: int = 60
    llm_temperature: float = 0.2
    llm_digest_max_articles: int = 12
    publish_targets: str = ""
    static_site_base_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_disable_notification: bool = False
    feishu_webhook: str = ""
    feishu_secret: str = ""
    feishu_message_type: str = "text"
    wechat_access_token: str = ""
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_thumb_media_id: str = ""
    wechat_thumb_image_path: str = ""
    wechat_thumb_image_url: str = ""
    wechat_thumb_upload_type: str = "thumb"
    wechat_author: str = ""
    wechat_content_source_url: str = ""
    wechat_need_open_comment: int = 0
    wechat_only_fans_can_comment: int = 0
    wechat_publish_after_draft: bool = False


def load_settings() -> Settings:
    base_dir = Path(os.getenv("AINEWS_HOME", os.getcwd())).resolve()
    _load_env_file(base_dir / ".env")

    database_url = os.getenv("AINEWS_DATABASE_URL", "sqlite:///data/ainews.db")
    sources_file_value = os.getenv("AINEWS_SOURCES_FILE", "")

    if database_url.startswith("sqlite:///"):
        database_fragment = database_url.replace("sqlite:///", "", 1)
        database_path = Path(database_fragment)
        if not database_path.is_absolute():
            database_path = base_dir / database_path
    else:
        database_path = Path(database_url)
        if not database_path.is_absolute():
            database_path = base_dir / database_path

    if sources_file_value:
        sources_file = Path(sources_file_value)
        if not sources_file.is_absolute():
            sources_file = base_dir / sources_file
    else:
        sources_file = PACKAGE_ROOT / "sources.default.json"

    output_dir = Path(os.getenv("AINEWS_OUTPUT_DIR", "output"))
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir

    static_site_dir = Path(os.getenv("AINEWS_STATIC_SITE_DIR", "output/site"))
    if not static_site_dir.is_absolute():
        static_site_dir = base_dir / static_site_dir

    database_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    static_site_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        base_dir=base_dir,
        database_path=database_path,
        sources_file=sources_file,
        output_dir=output_dir,
        static_site_dir=static_site_dir,
        request_timeout=int(os.getenv("AINEWS_REQUEST_TIMEOUT", "15")),
        default_lookback_hours=int(os.getenv("AINEWS_DEFAULT_LOOKBACK_HOURS", "48")),
        max_articles_per_source=int(os.getenv("AINEWS_MAX_ARTICLES_PER_SOURCE", "40")),
        allowed_origins=os.getenv("AINEWS_ALLOWED_ORIGINS", "*"),
        admin_token=os.getenv("AINEWS_ADMIN_TOKEN", ""),
        log_level=os.getenv("AINEWS_LOG_LEVEL", "INFO").strip().upper() or "INFO",
        log_format=os.getenv("AINEWS_LOG_FORMAT", "text").strip().lower() or "text",
        extraction_text_limit=int(os.getenv("AINEWS_EXTRACTION_TEXT_LIMIT", "12000")),
        source_cooldown_failure_threshold=int(
            os.getenv("AINEWS_SOURCE_COOLDOWN_FAILURE_THRESHOLD", "2")
        ),
        source_throttle_cooldown_minutes=int(
            os.getenv("AINEWS_SOURCE_THROTTLE_COOLDOWN_MINUTES", "120")
        ),
        source_blocked_cooldown_minutes=int(
            os.getenv("AINEWS_SOURCE_BLOCKED_COOLDOWN_MINUTES", "720")
        ),
        alert_targets=os.getenv("AINEWS_ALERT_TARGETS", ""),
        alert_cooldown_minutes=int(os.getenv("AINEWS_ALERT_COOLDOWN_MINUTES", "30")),
        alert_telegram_chat_id=os.getenv("AINEWS_ALERT_TELEGRAM_CHAT_ID", ""),
        alert_feishu_webhook=os.getenv("AINEWS_ALERT_FEISHU_WEBHOOK", ""),
        alert_feishu_secret=os.getenv("AINEWS_ALERT_FEISHU_SECRET", ""),
        llm_article_context_chars=int(os.getenv("AINEWS_LLM_ARTICLE_CONTEXT_CHARS", "6000")),
        llm_provider=os.getenv("AINEWS_LLM_PROVIDER", "openai_compatible"),
        llm_base_url=os.getenv("AINEWS_LLM_BASE_URL", "").rstrip("/"),
        llm_api_key=os.getenv("AINEWS_LLM_API_KEY", ""),
        llm_model=os.getenv("AINEWS_LLM_MODEL", ""),
        llm_timeout=int(os.getenv("AINEWS_LLM_TIMEOUT", "60")),
        llm_temperature=float(os.getenv("AINEWS_LLM_TEMPERATURE", "0.2")),
        llm_digest_max_articles=int(os.getenv("AINEWS_LLM_DIGEST_MAX_ARTICLES", "12")),
        publish_targets=os.getenv("AINEWS_PUBLISH_TARGETS", ""),
        static_site_base_url=os.getenv("AINEWS_STATIC_SITE_BASE_URL", "").rstrip("/"),
        telegram_bot_token=os.getenv("AINEWS_TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("AINEWS_TELEGRAM_CHAT_ID", ""),
        telegram_disable_notification=_env_flag("AINEWS_TELEGRAM_DISABLE_NOTIFICATION", False),
        feishu_webhook=os.getenv("AINEWS_FEISHU_WEBHOOK", ""),
        feishu_secret=os.getenv("AINEWS_FEISHU_SECRET", ""),
        feishu_message_type=os.getenv("AINEWS_FEISHU_MESSAGE_TYPE", "text").strip().lower()
        or "text",
        wechat_access_token=os.getenv("AINEWS_WECHAT_ACCESS_TOKEN", ""),
        wechat_app_id=os.getenv("AINEWS_WECHAT_APP_ID", ""),
        wechat_app_secret=os.getenv("AINEWS_WECHAT_APP_SECRET", ""),
        wechat_thumb_media_id=os.getenv("AINEWS_WECHAT_THUMB_MEDIA_ID", ""),
        wechat_thumb_image_path=os.getenv("AINEWS_WECHAT_THUMB_IMAGE_PATH", ""),
        wechat_thumb_image_url=os.getenv("AINEWS_WECHAT_THUMB_IMAGE_URL", ""),
        wechat_thumb_upload_type=os.getenv("AINEWS_WECHAT_THUMB_UPLOAD_TYPE", "thumb")
        .strip()
        .lower()
        or "thumb",
        wechat_author=os.getenv("AINEWS_WECHAT_AUTHOR", ""),
        wechat_content_source_url=os.getenv("AINEWS_WECHAT_CONTENT_SOURCE_URL", ""),
        wechat_need_open_comment=int(os.getenv("AINEWS_WECHAT_NEED_OPEN_COMMENT", "0")),
        wechat_only_fans_can_comment=int(os.getenv("AINEWS_WECHAT_ONLY_FANS_CAN_COMMENT", "0")),
        wechat_publish_after_draft=_env_flag("AINEWS_WECHAT_PUBLISH_AFTER_DRAFT", False),
    )
