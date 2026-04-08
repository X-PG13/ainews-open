from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from datetime import timedelta
from typing import Callable, Dict, Iterable, List, Optional

from .config import Settings
from .http import post_json
from .repository import ArticleRepository
from .utils import clean_text, utc_now

logger = logging.getLogger("ainews.alerting")


class AlertNotifier:
    def __init__(
        self,
        settings: Settings,
        repository: ArticleRepository,
        *,
        json_post: Callable[..., Dict[str, object]] = post_json,
    ):
        self.settings = settings
        self.repository = repository
        self.json_post = json_post

    def notify_rule(
        self,
        alert_key: str,
        *,
        active: bool,
        title: str,
        message: str,
        fingerprint: str = "",
        severity: str = "warning",
        cooldown_minutes: Optional[int] = None,
        recovery_title: Optional[str] = None,
        recovery_message: Optional[str] = None,
    ) -> Dict[str, object]:
        state = self.repository.get_alert_state(alert_key)
        targets = self._targets()
        if not targets:
            return {"status": "disabled", "alert_key": alert_key, "sent": False}

        if active:
            should_send = self._should_send_active(
                state,
                fingerprint=fingerprint,
                cooldown_minutes=cooldown_minutes,
            )
            if not should_send:
                self.repository.save_alert_state(
                    alert_key=alert_key,
                    is_active=True,
                    fingerprint=fingerprint or clean_text(str((state or {}).get("fingerprint", ""))),
                    last_status="active",
                    last_title=title,
                    last_message=message,
                )
                return {"status": "deduped", "alert_key": alert_key, "sent": False}

            sent, targets_result = self._send(
                title=title,
                message=message,
                severity=severity,
                recovery=False,
                targets=targets,
            )
            self.repository.save_alert_state(
                alert_key=alert_key,
                is_active=True,
                fingerprint=fingerprint,
                last_status="active" if sent else "delivery_error",
                last_title=title,
                last_message=message,
                sent_at=utc_now().isoformat() if sent else "",
                increment_delivery=sent,
            )
            return {
                "status": "sent" if sent else "delivery_error",
                "alert_key": alert_key,
                "sent": sent,
                "targets": targets_result,
            }

        if state and bool(state.get("is_active")):
            sent, targets_result = self._send(
                title=recovery_title or f"{title} recovered",
                message=recovery_message or message,
                severity="info",
                recovery=True,
                targets=targets,
            )
            self.repository.save_alert_state(
                alert_key=alert_key,
                is_active=False,
                fingerprint="",
                last_status="recovered" if sent else "recovery_delivery_error",
                last_title=recovery_title or f"{title} recovered",
                last_message=recovery_message or message,
                recovered_at=utc_now().isoformat() if sent else "",
                increment_delivery=sent,
            )
            return {
                "status": "recovered" if sent else "recovery_delivery_error",
                "alert_key": alert_key,
                "sent": sent,
                "targets": targets_result,
            }

        return {"status": "idle", "alert_key": alert_key, "sent": False}

    def _should_send_active(
        self,
        state: Optional[dict],
        *,
        fingerprint: str,
        cooldown_minutes: Optional[int],
    ) -> bool:
        if not state or not bool(state.get("is_active")):
            return True
        if fingerprint and fingerprint != clean_text(str(state.get("fingerprint", ""))):
            return True
        last_sent_at = clean_text(str(state.get("last_sent_at", "")))
        if not last_sent_at:
            return True
        cooldown = max(1, int(cooldown_minutes or self.settings.alert_cooldown_minutes))
        return last_sent_at <= (utc_now() - timedelta(minutes=cooldown)).isoformat()

    def _send(
        self,
        *,
        title: str,
        message: str,
        severity: str,
        recovery: bool,
        targets: Iterable[str],
    ) -> tuple[bool, List[dict]]:
        sent_any = False
        results: List[dict] = []
        text = self._render_text(title=title, message=message, severity=severity, recovery=recovery)
        for target in targets:
            try:
                if target == "telegram":
                    response = self._send_telegram(text)
                elif target == "feishu":
                    response = self._send_feishu(text)
                else:
                    raise ValueError(f"unsupported alert target: {target}")
                sent_any = True
                results.append({"target": target, "status": "ok", "response": response})
            except Exception as exc:  # pragma: no cover - exercised through unit tests
                logger.warning(
                    "alert target delivery failed",
                    extra={
                        "event": "alert.target_error",
                        "target": target,
                    },
                )
                results.append({"target": target, "status": "error", "message": str(exc)})
        return sent_any, results

    def _send_telegram(self, text: str) -> Dict[str, object]:
        token = clean_text(self.settings.telegram_bot_token)
        chat_id = clean_text(self.settings.alert_telegram_chat_id or self.settings.telegram_chat_id)
        if not token or not chat_id:
            raise ValueError("telegram alert channel is not configured")
        response = self.json_post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_notification": False,
            },
            timeout=self.settings.request_timeout,
            user_agent=self.settings.user_agent,
        )
        if not response.get("ok", False):
            raise ValueError(str(response.get("description") or "telegram alert failed"))
        return response

    def _send_feishu(self, text: str) -> Dict[str, object]:
        webhook = clean_text(self.settings.alert_feishu_webhook or self.settings.feishu_webhook)
        if not webhook:
            raise ValueError("feishu alert webhook is not configured")
        payload = {
            "msg_type": "text",
            "content": {"text": text[:18000]},
        }
        secret = clean_text(self.settings.alert_feishu_secret or self.settings.feishu_secret)
        if secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self._sign_feishu(timestamp, secret)
        response = self.json_post(
            webhook,
            payload,
            timeout=self.settings.request_timeout,
            user_agent=self.settings.user_agent,
        )
        if int(response.get("code", -1)) != 0:
            raise ValueError(str(response.get("msg") or "feishu alert failed"))
        return response

    def _targets(self) -> List[str]:
        values: List[str] = []
        aliases = {"telegram": "telegram", "feishu": "feishu"}
        for item in str(self.settings.alert_targets or "").split(","):
            value = clean_text(item).lower().replace("-", "_")
            if not value:
                continue
            normalized = aliases.get(value)
            if normalized and normalized not in values:
                values.append(normalized)
        return values

    @staticmethod
    def _render_text(
        *,
        title: str,
        message: str,
        severity: str,
        recovery: bool,
    ) -> str:
        prefix = "RECOVERY" if recovery else severity.upper()
        return f"[AI News Open][{prefix}] {clean_text(title)}\n\n{clean_text(message)}".strip()

    @staticmethod
    def _sign_feishu(timestamp: str, secret: str) -> str:
        key = f"{timestamp}\n{secret}".encode("utf-8")
        digest = hmac.new(key, digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")
