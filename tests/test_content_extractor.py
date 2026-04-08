import unittest
from pathlib import Path
from unittest.mock import patch

from ainews.content_extractor import ArticleContentExtractor

HTML_SAMPLE = """
<html>
  <head><title>Sample AI Story</title></head>
  <body>
    <header>site nav</header>
    <article>
      <h1>Sample AI Story</h1>
      <p>Artificial intelligence is changing enterprise software.</p>
      <p>Open models, new chips, and agent systems are driving new adoption across industries.</p>
      <p>Teams are now rebuilding internal workflows around generative AI products and tooling.</p>
      <p>Investors continue to track infrastructure, model serving, and application layer growth.</p>
    </article>
    <footer>footer links</footer>
  </body>
</html>
"""

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "extraction"


def _fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


class ContentExtractorTestCase(unittest.TestCase):
    def test_extracts_main_article_text(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(HTML_SAMPLE)

        self.assertEqual(content.title, "Sample AI Story")
        self.assertIn("Artificial intelligence is changing enterprise software.", content.text)
        self.assertNotIn("site nav", content.text)

    def test_prefers_36kr_article_container_and_drops_site_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("36kr.html"), url="https://36kr.com/p/123456789"
        )

        self.assertIn("国内 AI 创业公司正在重新评估模型部署与推理成本", content.text)
        self.assertNotIn("推荐阅读", content.text)
        self.assertNotIn("点赞 收藏 分享", content.text)

    def test_prefers_ithome_paragraph_container_and_drops_breadcrumb(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("ithome.html"), url="https://www.ithome.com/0/123/456.htm"
        )

        self.assertIn("国内外厂商正在密集发布新的 AI 终端与模型服务", content.text)
        self.assertNotIn("首页 > 科技", content.text)
        self.assertNotIn("相关推荐 热门标签", content.text)

    def test_extracts_international_openai_article_fixture(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("openai-article.html"), url="https://openai.com/index/enterprise-model/"
        )

        self.assertEqual(content.title, "OpenAI launches a new enterprise reasoning model")
        self.assertIn("OpenAI released a new model for enterprise deployment.", content.text)
        self.assertNotIn("site nav", content.text)

    def test_prefers_tmtpost_article_and_drops_editor_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("tmtpost.html"), url="https://www.tmtpost.com/7944857.html"
        )

        self.assertIn("AI 原生安全公司今天发布了新的代理防护平台", content.text)
        self.assertIn("AI 安全不再只是模型问题", content.text)
        self.assertNotIn("相关推荐", content.text)
        self.assertNotIn("责任编辑", content.text)
        self.assertNotIn("来源：钛媒体", content.text)

    def test_prefers_huggingface_blog_content_and_drops_author_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("huggingface-blog.html"), url="https://huggingface.co/blog/gemma4"
        )

        self.assertIn("The Gemma 4 family of multimodal models is now available", content.text)
        self.assertIn("developers can move from experimentation to deployment", content.text)
        self.assertNotIn("Back to Articles", content.text)
        self.assertNotIn("Follow", content.text)
        self.assertNotIn("Table of Contents", content.text)

    def test_prefers_google_ai_blog_body_and_drops_audio_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("google-ai-blog.html"),
            url="https://blog.google/innovation-and-ai/technology/developers-tools/introducing-flex-and-priority-inference/",
        )

        self.assertIn("Today, we are adding Flex and Priority inference to the Gemini API", content.text)
        self.assertIn("AI features move from demos into workflows", content.text)
        self.assertNotIn("Listen to article", content.text)
        self.assertNotIn("Voice", content.text)
        self.assertNotIn("POSTED IN", content.text)

    def test_prefers_deepmind_blog_body_and_drops_audio_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("deepmind-blog.html"),
            url="https://deepmind.google/blog/gemma-4-byte-for-byte-the-most-capable-open-models/",
        )

        self.assertIn("Today, we are introducing Gemma 4", content.text)
        self.assertIn("enterprises increasingly want to evaluate model quality", content.text)
        self.assertNotIn("Listen to article", content.text)
        self.assertNotIn("Voice", content.text)
        self.assertNotIn("POSTED IN", content.text)

    def test_prefers_theverge_entry_body_and_drops_author_card(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("theverge-article.html"),
            url="https://www.theverge.com/ai-artificial-intelligence/908114/anthropic-project-glasswing-cybersecurity",
        )

        self.assertIn("Anthropic is debuting a new AI model", content.text)
        self.assertIn("AI vendors are increasingly packaging models as operational products", content.text)
        self.assertNotIn("Posts from this author", content.text)
        self.assertNotIn("Follow", content.text)

    def test_rejects_google_news_aggregate_fixture(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)

        with self.assertRaisesRegex(ValueError, "too short"):
            extractor.extract_from_html(
                _fixture("google-news-aggregate.html"),
                url="https://news.google.com/rss/articles/demo?oc=5",
            )

    def test_fallback_parser_extracts_text_without_regex_block_stripping(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        with patch("ainews.content_extractor.BeautifulSoup", None):
            content = extractor.extract_from_html(
                _fixture("36kr.html"), url="https://36kr.com/p/123456789"
            )

        self.assertIn("国内 AI 创业公司正在重新评估模型部署与推理成本", content.text)
        self.assertNotIn("推荐阅读", content.text)
        self.assertNotIn("点赞 收藏 分享", content.text)

    def test_fallback_parser_extracts_huggingface_blog_fixture(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        with patch("ainews.content_extractor.BeautifulSoup", None):
            content = extractor.extract_from_html(
                _fixture("huggingface-blog.html"), url="https://huggingface.co/blog/gemma4"
            )

        self.assertIn("The Gemma 4 family of multimodal models is now available", content.text)
        self.assertNotIn("Back to Articles", content.text)
        self.assertNotIn("Follow", content.text)


if __name__ == "__main__":
    unittest.main()
