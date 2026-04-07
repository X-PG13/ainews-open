import json
import unittest
from unittest.mock import patch

from ainews.http import fetch_binary, fetch_json, fetch_text, post_json, post_multipart


class FakeHeaders:
    def __init__(self, *, charset="utf-8", content_type="application/json"):
        self._charset = charset
        self._content_type = content_type

    def get_content_charset(self):
        return self._charset

    def get_content_type(self):
        return self._content_type


class FakeResponse:
    def __init__(self, body, *, charset="utf-8", content_type="application/json", url="https://example.com/file"):
        self._body = body
        self.headers = FakeHeaders(charset=charset, content_type=content_type)
        self.url = url

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class HttpHelpersTestCase(unittest.TestCase):
    def test_fetch_text_decodes_response(self) -> None:
        with patch("ainews.http.urlopen", return_value=FakeResponse("你好".encode("utf-8"))):
            text = fetch_text("https://example.com/feed", timeout=10, user_agent="test-agent")

        self.assertEqual(text, "你好")

    def test_fetch_json_and_post_json_send_expected_request_shape(self) -> None:
        requests = []

        def fake_urlopen(request, timeout=0):
            requests.append(request)
            return FakeResponse(json.dumps({"ok": True}).encode("utf-8"))

        with patch("ainews.http.urlopen", side_effect=fake_urlopen):
            self.assertEqual(
                fetch_json("https://example.com/api", timeout=10, user_agent="test-agent"),
                {"ok": True},
            )
            self.assertEqual(
                post_json(
                    "https://example.com/api",
                    {"hello": "world"},
                    timeout=10,
                    user_agent="test-agent",
                ),
                {"ok": True},
            )

        self.assertEqual(requests[0].get_method(), "GET")
        self.assertEqual(requests[1].get_method(), "POST")
        self.assertIn(b'"hello": "world"', requests[1].data)

    def test_fetch_binary_and_post_multipart_cover_file_helpers(self) -> None:
        requests = []

        def fake_urlopen(request, timeout=0):
            requests.append(request)
            if request.full_url.endswith("/image"):
                return FakeResponse(
                    b"binary-data",
                    content_type="image/jpeg",
                    url="https://example.com/image",
                )
            return FakeResponse(json.dumps({"ok": True}).encode("utf-8"))

        with patch("ainews.http.urlopen", side_effect=fake_urlopen):
            downloaded = fetch_binary("https://example.com/image", timeout=10, user_agent="test-agent")
            response = post_multipart(
                "https://example.com/upload",
                files={"media": ("cover.jpg", b"jpg-bytes", "image/jpeg")},
                fields={"type": "thumb"},
                timeout=10,
                user_agent="test-agent",
            )

        self.assertEqual(downloaded.filename, "image.jpg")
        self.assertEqual(downloaded.content_type, "image/jpeg")
        self.assertEqual(response, {"ok": True})
        self.assertEqual(requests[1].get_method(), "POST")
        self.assertIn(b'filename="cover.jpg"', requests[1].data)
        self.assertIn(b'name="type"', requests[1].data)


if __name__ == "__main__":
    unittest.main()
