import tempfile
import unittest
from pathlib import Path

from ainews.alerting import AlertNotifier
from ainews.config import Settings
from ainews.repository import ArticleRepository


class AlertNotifierTestCase(unittest.TestCase):
    def test_dedupes_active_alerts_and_sends_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            calls = []

            def fake_post(url, payload, **kwargs):
                calls.append((url, payload))
                return {"ok": True, "result": {"message_id": len(calls)}}

            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                alert_targets="telegram",
                telegram_bot_token="telegram-token",
                alert_telegram_chat_id="@alerts",
            )
            repository = ArticleRepository(settings.database_path)
            notifier = AlertNotifier(settings, repository, json_post=fake_post)

            first = notifier.notify_rule(
                "pipeline_status",
                active=True,
                title="pipeline status is partial_error",
                message="extract=partial_error",
                fingerprint="partial_error|extract",
            )
            second = notifier.notify_rule(
                "pipeline_status",
                active=True,
                title="pipeline status is partial_error",
                message="extract=partial_error",
                fingerprint="partial_error|extract",
            )
            recovery = notifier.notify_rule(
                "pipeline_status",
                active=False,
                title="pipeline status is ok",
                message="pipeline recovered",
            )

            self.assertEqual(first["status"], "sent")
            self.assertEqual(second["status"], "deduped")
            self.assertEqual(recovery["status"], "recovered")
            self.assertEqual(len(calls), 2)
            state = repository.get_alert_state("pipeline_status")
            self.assertFalse(state["is_active"])
            self.assertEqual(state["delivery_count"], 2)

    def test_feishu_alert_uses_alert_specific_webhook(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            calls = []

            def fake_post(url, payload, **kwargs):
                calls.append((url, payload))
                return {"code": 0, "msg": "success"}

            settings = Settings(
                database_path=Path(temp_dir) / "ainews.db",
                sources_file=Path(temp_dir) / "sources.json",
                alert_targets="feishu",
                alert_feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/alert-demo",
            )
            repository = ArticleRepository(settings.database_path)
            notifier = AlertNotifier(settings, repository, json_post=fake_post)

            result = notifier.notify_rule(
                "health_status",
                active=True,
                title="service health is degraded",
                message="source_cooldowns_active",
                fingerprint="degraded|source_cooldowns_active",
            )

            self.assertEqual(result["status"], "sent")
            self.assertEqual(len(calls), 1)
            self.assertIn("feishu.cn", calls[0][0])
            self.assertEqual(calls[0][1]["msg_type"], "text")


if __name__ == "__main__":
    unittest.main()
