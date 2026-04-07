import tempfile
import unittest
from pathlib import Path

from ainews.config import Settings
from ainews.publisher import DigestPublisher


def make_settings(temp_dir: str, **overrides) -> Settings:
    values = {
        "database_path": Path(temp_dir) / "ainews.db",
        "sources_file": Path(temp_dir) / "sources.json",
        "output_dir": Path(temp_dir) / "output",
        "static_site_dir": Path(temp_dir) / "site",
    }
    values.update(overrides)
    settings = Settings(**values)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.static_site_dir.mkdir(parents=True, exist_ok=True)
    return settings


def sample_payload() -> dict:
    return {
        "region": "all",
        "since_hours": 48,
        "articles": [
            {
                "title": "OpenAI 发布新模型",
                "display_title_zh": "OpenAI 发布新模型",
                "compact_summary_zh": "模型能力、推理成本和企业落地路径都发生了变化。",
                "source_name": "OpenAI News",
                "published_at": "2026-04-07T08:00:00+00:00",
                "url": "https://example.com/openai-model",
            }
        ],
        "digest": {
            "title": "2026-04-07 全网 AI 新闻日报",
            "overview": "最近 48 小时共收录 12 条 AI 新闻。",
            "highlights": ["OpenAI 发布新模型", "国内厂商加速端侧 AI 布局"],
            "sections": [
                {
                    "title": "国际动态",
                    "items": [
                        "OpenAI 发布新模型，进一步提升企业部署能力。",
                        "多家国外公司开始压缩推理成本并优化产品交付。",
                    ],
                }
            ],
            "closing": "以上内容建议发布前人工复核。",
        },
        "body_markdown": "# Digest",
    }


class PublisherTestCase(unittest.TestCase):
    def test_feishu_card_falls_back_to_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            calls = []

            def fake_post(url, payload, **kwargs):
                calls.append(payload)
                if payload["msg_type"] == "interactive":
                    return {"code": 9499, "msg": "Bad Request"}
                return {"code": 0, "msg": "success", "data": {}}

            settings = make_settings(
                temp_dir,
                feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/demo",
                feishu_message_type="card",
            )
            publisher = DigestPublisher(settings, json_post=fake_post)

            result = publisher.publish(sample_payload(), targets=["feishu"])

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0]["msg_type"], "interactive")
            self.assertEqual(calls[1]["msg_type"], "text")

    def test_static_site_publish_writes_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            publisher = DigestPublisher(make_settings(temp_dir))

            result = publisher.publish(sample_payload(), targets=["static_site"])

            self.assertEqual(result["status"], "ok")
            files = result["targets"][0]["files"]
            self.assertTrue(files)
            for path in files:
                self.assertTrue(Path(path).exists())

    def test_telegram_publish_splits_long_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            calls = []

            def fake_post(url, payload, **kwargs):
                calls.append((url, payload))
                return {"ok": True, "result": {"message_id": len(calls)}}

            settings = make_settings(
                temp_dir,
                telegram_bot_token="telegram-token",
                telegram_chat_id="@ai_digest",
            )
            publisher = DigestPublisher(settings, json_post=fake_post)
            payload = sample_payload()
            payload["digest"]["sections"][0]["items"] = ["A" * 4200, "B" * 4200]

            result = publisher.publish(payload, targets=["telegram"])

            self.assertEqual(result["status"], "ok")
            self.assertGreater(len(calls), 1)
            self.assertIn("sendMessage", calls[0][0])

    def test_wechat_publish_creates_draft_and_submit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            post_calls = []
            get_calls = []

            def fake_post(url, payload, **kwargs):
                post_calls.append((url, payload))
                if "draft/add" in url:
                    return {"errcode": 0, "media_id": "MEDIA123"}
                if "freepublish/submit" in url:
                    return {"errcode": 0, "publish_id": "PUBLISH123"}
                raise AssertionError(f"unexpected url {url}")

            def fake_get(url, **kwargs):
                get_calls.append(url)
                return {"access_token": "ACCESS123", "expires_in": 7200}

            settings = make_settings(
                temp_dir,
                wechat_app_id="wx-app-id",
                wechat_app_secret="wx-app-secret",
                wechat_thumb_media_id="thumb-media-id",
                wechat_author="AI News Open",
            )
            publisher = DigestPublisher(settings, json_post=fake_post, json_get=fake_get)

            result = publisher.publish(sample_payload(), targets=["wechat"], wechat_submit=True)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(get_calls), 1)
            self.assertIn("client_credential", get_calls[0])
            self.assertEqual(len(post_calls), 2)
            self.assertIn("draft/add", post_calls[0][0])
            self.assertIn("freepublish/submit", post_calls[1][0])
            self.assertEqual(post_calls[0][1]["articles"][0]["thumb_media_id"], "thumb-media-id")

    def test_wechat_publish_auto_uploads_thumb_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            thumb_path = Path(temp_dir) / "cover.jpg"
            thumb_path.write_bytes(b"\xff\xd8\xff" + (b"\x00" * 100))

            post_calls = []
            multipart_calls = []

            def fake_post(url, payload, **kwargs):
                post_calls.append((url, payload))
                return {"errcode": 0, "media_id": "DRAFT123"}

            def fake_get(url, **kwargs):
                return {"access_token": "ACCESS123", "expires_in": 7200}

            def fake_multipart(url, files, **kwargs):
                multipart_calls.append((url, files))
                return {
                    "errcode": 0,
                    "media_id": "THUMB123",
                    "url": "https://example.com/thumb.jpg",
                }

            settings = make_settings(
                temp_dir,
                wechat_app_id="wx-app-id",
                wechat_app_secret="wx-app-secret",
                wechat_thumb_image_path=str(thumb_path),
                wechat_thumb_upload_type="thumb",
                wechat_author="AI News Open",
            )
            publisher = DigestPublisher(
                settings,
                json_post=fake_post,
                json_get=fake_get,
                multipart_post=fake_multipart,
            )

            result = publisher.publish(sample_payload(), targets=["wechat"], wechat_submit=False)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(multipart_calls), 1)
            self.assertIn("type=thumb", multipart_calls[0][0])
            self.assertIn("cover.jpg", multipart_calls[0][1]["media"][0])
            self.assertEqual(post_calls[0][1]["articles"][0]["thumb_media_id"], "THUMB123")

    def test_refresh_wechat_publication_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            post_calls = []
            get_calls = []

            def fake_post(url, payload, **kwargs):
                post_calls.append((url, payload))
                return {
                    "publish_id": "PUBLISH123",
                    "publish_status": 0,
                    "article_id": "ARTICLE123",
                    "article_detail": {
                        "count": 1,
                        "item": [{"idx": 1, "article_url": "https://mp.weixin.qq.com/s/demo"}],
                    },
                }

            def fake_get(url, **kwargs):
                get_calls.append(url)
                return {"access_token": "ACCESS123", "expires_in": 7200}

            settings = make_settings(
                temp_dir,
                wechat_app_id="wx-app-id",
                wechat_app_secret="wx-app-secret",
            )
            publisher = DigestPublisher(settings, json_post=fake_post, json_get=fake_get)

            result = publisher.refresh_publication(
                {
                    "target": "wechat",
                    "external_id": "PUBLISH123",
                    "response_payload": {"publish": {"publish_id": "PUBLISH123"}},
                }
            )

            self.assertEqual(result.status, "ok")
            self.assertEqual(result.external_id, "PUBLISH123")
            self.assertEqual(len(get_calls), 1)
            self.assertEqual(post_calls[0][1]["publish_id"], "PUBLISH123")
            self.assertEqual(result.response["status_query"]["publish_status"], 0)


if __name__ == "__main__":
    unittest.main()
