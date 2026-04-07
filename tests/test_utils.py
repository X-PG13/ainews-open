import unittest

from ainews.utils import (
    canonicalize_url,
    extract_json_object,
    make_content_hash,
    make_dedup_key,
    matches_keywords,
    truncate_text,
)


class UtilsTestCase(unittest.TestCase):
    def test_canonicalize_url_removes_tracking_query(self) -> None:
        url = "https://example.com/news/item/?utm_source=x&gclid=abc&id=42#fragment"
        self.assertEqual(canonicalize_url(url), "https://example.com/news/item?id=42")

    def test_dedup_key_is_stable_for_punctuation_variants(self) -> None:
        left = make_dedup_key("OpenAI 发布新模型！")
        right = make_dedup_key("OpenAI 发布新模型")
        self.assertEqual(left, right)

    def test_content_hash_uses_summary(self) -> None:
        left = make_content_hash("AI update", "summary one")
        right = make_content_hash("AI update", "summary two")
        self.assertNotEqual(left, right)

    def test_ascii_keyword_uses_word_boundary_matching(self) -> None:
        self.assertTrue(matches_keywords("Latest AI model release", ["AI"]))
        self.assertFalse(matches_keywords("The company paid for servers", ["AI"]))

    def test_extract_json_object_accepts_code_fence(self) -> None:
        payload = extract_json_object('```json\n{"title":"AI日报"}\n```')
        self.assertEqual(payload["title"], "AI日报")

    def test_truncate_text_prefers_sentence_boundary(self) -> None:
        text = "第一句很重要。第二句继续展开。第三句还没结束。"
        self.assertEqual(truncate_text(text, 12), "第一句很重要。")


if __name__ == "__main__":
    unittest.main()
