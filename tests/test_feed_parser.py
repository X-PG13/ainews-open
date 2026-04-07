import unittest

from ainews.feed_parser import parse_feed_document
from ainews.models import SourceDefinition

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Feed</title>
    <item>
      <title>OpenAI launches a new reasoning model</title>
      <link>https://example.com/news/openai?utm_source=newsletter</link>
      <description><![CDATA[<p>Detailed summary.</p>]]></description>
      <pubDate>Tue, 07 Apr 2026 08:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


class FeedParserTestCase(unittest.TestCase):
    def test_parse_rss_document(self) -> None:
        source = SourceDefinition(
            id="sample",
            name="Sample",
            url="https://example.com/feed",
            region="international",
            language="en",
            country="US",
            topic="news",
        )

        articles = parse_feed_document(RSS_SAMPLE, source)

        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article.title, "OpenAI launches a new reasoning model")
        self.assertEqual(article.summary, "Detailed summary.")
        self.assertEqual(article.canonical_url, "https://example.com/news/openai")

    def test_rejects_html_payload(self) -> None:
        source = SourceDefinition(
            id="sample",
            name="Sample",
            url="https://example.com/feed",
            region="international",
            language="en",
            country="US",
            topic="news",
        )

        with self.assertRaises(ValueError):
            parse_feed_document("<html><body>not a feed</body></html>", source)


if __name__ == "__main__":
    unittest.main()
