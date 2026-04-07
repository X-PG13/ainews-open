from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key in (
            "event",
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "target",
            "region",
            "since_hours",
            "limit",
            "published",
            "errors",
            "updated",
            "requested",
            "stored_total",
            "generation_mode",
            "schema_version",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, level: str = "INFO", log_format: str = "text", force: bool = False) -> None:
    root = logging.getLogger()
    target_level = getattr(logging, level.upper(), logging.INFO)

    if force or not root.handlers:
        handler = logging.StreamHandler()
        if log_format == "json":
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                    "%Y-%m-%dT%H:%M:%S%z",
                )
            )
        root.handlers = [handler]

    root.setLevel(target_level)
