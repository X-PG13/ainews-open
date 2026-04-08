import io
import unittest
from pathlib import Path
from unittest.mock import patch

from ainews.google_news import GoogleNewsResolutionError, GoogleNewsURLResolver, is_google_news_url

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "google_news"


def _fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


class _Headers:
    @staticmethod
    def get_content_charset() -> str:
        return "utf-8"


class _FakeUrlopenResponse:
    def __init__(self, body: str) -> None:
        self._buffer = io.BytesIO(body.encode("utf-8"))
        self.headers = _Headers()

    def read(self) -> bytes:
        return self._buffer.read()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class GoogleNewsResolverTestCase(unittest.TestCase):
    def test_is_google_news_url_matches_wrapper_paths(self) -> None:
        self.assertTrue(is_google_news_url("https://news.google.com/rss/articles/demo?oc=5"))
        self.assertTrue(is_google_news_url("https://news.google.com/read/demo"))
        self.assertFalse(is_google_news_url("https://news.google.com/home"))
        self.assertFalse(is_google_news_url("https://example.com/rss/articles/demo"))

    def test_resolves_english_google_news_wrapper(self) -> None:
        resolver = GoogleNewsURLResolver(timeout=10, user_agent="test-agent")
        with patch(
            "ainews.google_news.fetch_text",
            return_value=_fixture("anthropic-wrapper.html"),
        ), patch(
            "ainews.google_news.urlopen",
            return_value=_FakeUrlopenResponse(_fixture("anthropic-batchexecute.txt")),
        ):
            resolved = resolver.resolve("https://news.google.com/rss/articles/demo?oc=5")

        self.assertEqual(resolved, "https://www.anthropic.com/glasswing")

    def test_resolves_chinese_google_news_wrapper(self) -> None:
        resolver = GoogleNewsURLResolver(timeout=10, user_agent="test-agent")
        with patch(
            "ainews.google_news.fetch_text",
            return_value=_fixture("spp-wrapper.html"),
        ), patch(
            "ainews.google_news.urlopen",
            return_value=_FakeUrlopenResponse(_fixture("spp-batchexecute.txt")),
        ):
            resolved = resolver.resolve("https://news.google.com/rss/articles/demo-cn?oc=5")

        self.assertEqual(
            resolved,
            "https://www.spp.gov.cn/spp/llyj/202604/t20260408_725499.shtml",
        )

    def test_raises_when_wrapper_tokens_are_missing(self) -> None:
        resolver = GoogleNewsURLResolver(timeout=10, user_agent="test-agent")
        with patch("ainews.google_news.fetch_text", return_value="<html><body>missing</body></html>"):
            with self.assertRaises(GoogleNewsResolutionError):
                resolver.resolve("https://news.google.com/rss/articles/demo?oc=5")


if __name__ == "__main__":
    unittest.main()
