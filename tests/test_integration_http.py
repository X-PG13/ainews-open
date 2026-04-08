import json
import tempfile
import threading
import unittest
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from ainews.config import Settings
from ainews.llm import OpenAICompatibleLLMClient
from ainews.publisher import DigestPublisher


@dataclass
class RequestRecord:
    method: str
    path: str
    headers: Dict[str, str]
    body: object


class LocalJsonServer:
    def __init__(
        self,
        routes: Dict[
            Tuple[str, str],
            Callable[[RequestRecord], Tuple[int, Dict[str, object], Optional[str]]],
        ],
    ):
        self.routes = routes
        self.requests: list[RequestRecord] = []
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.base_url = ""

    def __enter__(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self._handle()

            def do_POST(self) -> None:
                self._handle()

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw_body = self.rfile.read(length) if length else b""
                try:
                    parsed_body: object = json.loads(raw_body.decode("utf-8")) if raw_body else {}
                except json.JSONDecodeError:
                    parsed_body = raw_body.decode("utf-8", errors="replace")

                record = RequestRecord(
                    method=self.command,
                    path=self.path,
                    headers={key: value for key, value in self.headers.items()},
                    body=parsed_body,
                )
                owner.requests.append(record)
                route = owner.routes.get((self.command, self.path))
                if route is None:
                    status, payload, content_type = 404, {"error": "not found"}, "application/json"
                else:
                    status, payload, content_type = route(record)

                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type or "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args) -> None:  # pragma: no cover
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self._server.server_port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)


def _settings(temp_dir: str, **overrides) -> Settings:
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


def _sample_publish_payload() -> dict:
    return {
        "region": "all",
        "since_hours": 48,
        "articles": [
            {
                "display_title_zh": "OpenAI 发布企业级推理模型",
                "compact_summary_zh": "新模型强化了推理、平台工具和企业部署能力。",
                "source_name": "OpenAI News",
                "published_at": "2026-04-07T08:00:00+00:00",
                "url": "https://example.com/openai-model",
            }
        ],
        "digest": {
            "title": "2026-04-08 AI Daily Digest",
            "overview": "A compact bilingual AI digest for operators.",
            "highlights": [
                "OpenAI ships a new enterprise reasoning model",
                "Teams are rebuilding workflows around agents",
            ],
            "sections": [
                {
                    "title": "Global",
                    "items": [
                        "OpenAI improved enterprise deployment tooling.",
                        "Teams are treating AI as an operational workflow layer.",
                    ],
                }
            ],
            "closing": "Review before publishing.",
        },
        "body_markdown": "# Digest",
    }


class HttpIntegrationTestCase(unittest.TestCase):
    def test_openai_compatible_llm_client_enriches_over_real_http(self) -> None:
        def completions_handler(record: RequestRecord) -> Tuple[int, Dict[str, object], Optional[str]]:
            self.assertEqual(record.headers["Authorization"], "Bearer test-token")
            body = record.body
            self.assertEqual(body["model"], "demo-model")
            self.assertEqual(body["messages"][0]["role"], "system")
            self.assertIn("article_context", body["messages"][1]["content"])
            return (
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "title_zh": "OpenAI 推出企业推理模型",
                                        "summary_zh": "OpenAI 发布了新的企业级推理模型。",
                                        "importance_zh": "这会影响企业部署和成本结构。",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                None,
            )

        with tempfile.TemporaryDirectory() as temp_dir, LocalJsonServer(
            {("POST", "/v1/chat/completions"): completions_handler}
        ) as server:
            client = OpenAICompatibleLLMClient(
                _settings(
                    temp_dir,
                    llm_base_url=f"{server.base_url}/v1",
                    llm_api_key="test-token",
                    llm_model="demo-model",
                )
            )

            result = client.enrich_article(
                {
                    "title": "OpenAI launches an enterprise reasoning model",
                    "summary": "A release update.",
                    "extracted_text": "The release includes better reasoning and enterprise tooling.",
                    "url": "https://example.com/openai-model",
                }
            )

        self.assertEqual(result.title_zh, "OpenAI 推出企业推理模型")
        self.assertIn("企业级推理模型", result.summary_zh)

    def test_openai_compatible_llm_client_generates_digest_over_real_http(self) -> None:
        def completions_handler(record: RequestRecord) -> Tuple[int, Dict[str, object], Optional[str]]:
            body = record.body
            self.assertIn("title, overview, highlights, sections, closing", body["messages"][1]["content"])
            return (
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "title": "2026-04-08 中文 AI 日报",
                                        "overview": "最近 24 小时内的 AI 新闻要点。",
                                        "highlights": ["OpenAI 发布企业模型", "国内厂商推进端侧 AI"],
                                        "sections": [
                                            {
                                                "title": "国际动态",
                                                "items": [
                                                    "OpenAI 加强企业级模型部署能力。",
                                                    "海外团队继续优化推理成本。",
                                                ],
                                            }
                                        ],
                                        "closing": "以上内容建议发布前人工复核。",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                None,
            )

        with tempfile.TemporaryDirectory() as temp_dir, LocalJsonServer(
            {("POST", "/v1/chat/completions"): completions_handler}
        ) as server:
            client = OpenAICompatibleLLMClient(
                _settings(
                    temp_dir,
                    llm_base_url=f"{server.base_url}/v1",
                    llm_api_key="test-token",
                    llm_model="demo-model",
                )
            )

            result = client.generate_digest(
                [
                    {
                        "region": "international",
                        "display_title_zh": "OpenAI 发布企业模型",
                        "display_summary_zh": "OpenAI 发布了新的企业级推理模型。",
                        "display_brief_zh": "企业部署能力继续增强。",
                        "source_name": "OpenAI News",
                        "published_at": "2026-04-08T08:00:00+00:00",
                    }
                ],
                region="all",
                since_hours=24,
            )

        self.assertEqual(result.title, "2026-04-08 中文 AI 日报")
        self.assertEqual(result.sections[0]["title"], "国际动态")

    def test_feishu_publish_uses_real_http_webhook_round_trip(self) -> None:
        def webhook_handler(record: RequestRecord) -> Tuple[int, Dict[str, object], Optional[str]]:
            self.assertEqual(record.body["msg_type"], "interactive")
            self.assertIn("header", record.body["card"])
            return 200, {"code": 0, "msg": "success", "data": {}}, None

        with tempfile.TemporaryDirectory() as temp_dir, LocalJsonServer(
            {("POST", "/feishu"): webhook_handler}
        ) as server:
            publisher = DigestPublisher(
                _settings(
                    temp_dir,
                    feishu_webhook=f"{server.base_url}/feishu",
                    feishu_message_type="card",
                )
            )

            result = publisher.publish(_sample_publish_payload(), targets=["feishu"])

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["targets"][0]["status"], "ok")
        self.assertEqual(result["targets"][0]["message"], "sent feishu card message")


if __name__ == "__main__":
    unittest.main()
