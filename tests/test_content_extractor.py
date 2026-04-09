import unittest
from pathlib import Path
from unittest.mock import patch

from ainews.content_extractor import (
    ArticleContentExtractor,
    ExtractionBlockedError,
    ExtractionSkippedError,
)

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

    def test_prefers_jiqizhixin_article_body_and_drops_share_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("jiqizhixin.html"),
            url="https://www.jiqizhixin.com/articles/2026-04-09-ops-stack",
        )

        self.assertIn("大模型项目从试验进入生产", content.text)
        self.assertIn("是否足够可观测、可治理、可恢复", content.text)
        self.assertNotIn("分享 微信 微博 收藏", content.text)
        self.assertNotIn("原标题", content.text)

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

    def test_prefers_techcrunch_entry_content_and_drops_newsletter_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("techcrunch-article.html"),
            url="https://techcrunch.com/2026/04/07/i-cant-help-rooting-for-tiny-open-source-ai-model-maker-arcee/",
        )

        self.assertIn("Arcee is trying to build a credible open source model company", content.text)
        self.assertIn("infrastructure buyers still want more optionality", content.text)
        self.assertNotIn("Sign up for the TechCrunch AI newsletter", content.text)
        self.assertNotIn("Share this article", content.text)

    def test_prefers_arstechnica_article_content_and_drops_related_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("arstechnica-article.html"),
            url="https://arstechnica.com/ai/2026/04/why-ai-teams-are-rebuilding-their-observability-stacks/",
        )

        self.assertIn("teams deploying language models are replacing one-off dashboards", content.text)
        self.assertIn("instrumentation and rollback paths matter almost as much as model quality", content.text)
        self.assertNotIn("Related stories from Ars Technica", content.text)
        self.assertNotIn("Stay tuned", content.text)

    def test_prefers_mit_technology_review_body_and_drops_newsletter_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("technologyreview-article.html"),
            url="https://www.technologyreview.com/2026/04/09/1111111/ai-buyers-now-demand-observability-before-scale/",
        )

        self.assertIn("enterprise AI buyers increasingly want observability", content.text)
        self.assertIn("deployment workflows can survive outages, policy changes, and retrieval regressions", content.text)
        self.assertNotIn("Subscribe to The Algorithm", content.text)
        self.assertNotIn("More from MIT Technology Review", content.text)
        self.assertNotIn("Most Popular", content.text)

    def test_prefers_axios_story_body_and_drops_newsletter_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("axios-article.html"),
            url="https://www.axios.com/2026/04/09/ai-buyers-rollback-plans-before-rollouts",
        )

        self.assertIn("enterprise AI buyers increasingly ask vendors to prove rollback paths", content.text)
        self.assertIn("deployment workflows can survive outages, policy changes, and retrieval regressions", content.text)
        self.assertNotIn("Sign up for Axios AI+", content.text)
        self.assertNotIn("More from Axios", content.text)
        self.assertNotIn("Share this story", content.text)

    def test_prefers_apnews_story_body_and_drops_wire_footer_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("apnews-article.html"),
            url="https://apnews.com/article/ai-buyers-moving-past-pilot-theater-1234567890",
        )

        self.assertIn("enterprise AI teams are pushing vendors to prove they can run production systems", content.text)
        self.assertIn("rollback controls, evaluation logs, and human escalation paths", content.text)
        self.assertNotIn("Read more", content.text)
        self.assertNotIn("More stories", content.text)
        self.assertNotIn("The Associated Press is an independent global news organization", content.text)

    def test_prefers_apnews_live_updates_and_drops_timestamp_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("apnews-live-updates.html"),
            url="https://apnews.com/live/ai-regulation-operations-updates-2026-04-09",
        )

        self.assertIn("operators rolling out generative AI systems are being pressed", content.text)
        self.assertIn("incident playbooks, audit logs, and fallback controls", content.text)
        self.assertNotIn("9:41 a.m. EDT", content.text)
        self.assertNotIn("Read more", content.text)
        self.assertNotIn("More stories", content.text)

    def test_prefers_bbc_live_body_and_drops_live_meta_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("bbc-live.html"),
            url="https://www.bbc.com/news/live/technology-12345678",
        )

        self.assertIn("executives are asking AI teams to explain how live systems will be supervised", content.text)
        self.assertIn("document approval paths, alerting rules, and fallback procedures", content.text)
        self.assertNotIn("Live Reporting", content.text)
        self.assertNotIn("Posted at 10:42", content.text)
        self.assertNotIn("Top stories", content.text)

    def test_prefers_cnbc_article_body_and_drops_newsletter_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("cnbc-article.html"),
            url="https://www.cnbc.com/2026/04/09/ai-operating-discipline-becomes-board-topic.html",
        )

        self.assertIn("AI operating discipline is becoming a board-level topic", content.text)
        self.assertIn("measure reliability, control rollback windows, and explain model-driven failures", content.text)
        self.assertNotIn("Subscribe to CNBC PRO", content.text)
        self.assertNotIn("Related Tags", content.text)
        self.assertNotIn("Watch: Why AI spending is accelerating again", content.text)

    def test_prefers_ft_article_body_and_drops_recommended_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("ft-article.html"),
            url="https://www.ft.com/content/ai-governance-pressure-2026-04-09",
        )

        self.assertIn("enterprise buyers now evaluate AI vendors on governance and recoverability", content.text)
        self.assertIn("document fallback paths, human approvals, and incident playbooks", content.text)
        self.assertNotIn("Sign up to the FT Edit newsletter", content.text)
        self.assertNotIn("Recommended", content.text)
        self.assertNotIn("Read next", content.text)

    def test_prefers_semafor_briefing_body_and_drops_signal_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("semafor-briefing.html"),
            url="https://www.semafor.com/article/2026/04/09/ai-buyers-operating-like-reliability-teams",
        )

        self.assertIn("enterprise AI buyers are increasingly judging vendors on operational discipline", content.text)
        self.assertIn("rollback controls, evaluation history, and escalation paths", content.text)
        self.assertNotIn("Read the full signal", content.text)
        self.assertNotIn("View in browser", content.text)
        self.assertNotIn("More from Semafor", content.text)

    def test_prefers_morningbrew_digest_body_and_drops_newsletter_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("morningbrew-digest.html"),
            url="https://www.morningbrew.com/stories/2026/04/09/ai-deployment-discipline-becoming-mainstream",
        )

        self.assertIn("AI deployment discipline is becoming a mainstream concern", content.text)
        self.assertIn("kill switches, audit logs, and review queues", content.text)
        self.assertNotIn("Join millions of readers", content.text)
        self.assertNotIn("Read more from Morning Brew", content.text)
        self.assertNotIn("Was this forwarded to you?", content.text)

    def test_prefers_theinformation_briefing_body_and_drops_subscriber_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("theinformation-briefing.html"),
            url="https://www.theinformation.com/articles/ai-governance-and-operator-pressure",
        )

        self.assertIn("AI operators are facing more pressure to prove governance discipline", content.text)
        self.assertIn("document human approvals, fallback procedures, and review checkpoints", content.text)
        self.assertNotIn("Subscriber-only content", content.text)
        self.assertNotIn("Already a subscriber?", content.text)
        self.assertNotIn("Read more from The Information", content.text)

    def test_prefers_engadget_article_body_and_drops_multimedia_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("engadget-article.html"),
            url="https://www.engadget.com/ai-operators-now-care-about-rollback-readiness-090000123.html",
        )

        self.assertIn("AI operators are increasingly judged on how quickly they can unwind a problematic rollout", content.text)
        self.assertIn("circuit breakers, audit logs, and clear human escalation", content.text)
        self.assertNotIn("Watch: Demo of the latest AI gadget", content.text)
        self.assertNotIn("Listen to this article", content.text)
        self.assertNotIn("Recommended by Engadget", content.text)

    def test_prefers_forbes_article_body_and_drops_embed_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("forbes-article.html"),
            url="https://www.forbes.com/sites/2026/04/09/why-ai-governance-is-becoming-operational-work/",
        )

        self.assertIn("enterprise AI governance is becoming an operations problem", content.text)
        self.assertIn("observability, review queues, and rollback design", content.text)
        self.assertNotIn("Watch Forbes", content.text)
        self.assertNotIn("Listen to article", content.text)
        self.assertNotIn("More From Forbes", content.text)

    def test_prefers_zdnet_article_body_and_drops_podcast_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("zdnet-article.html"),
            url="https://www.zdnet.com/article/ai-platform-teams-rebuild-around-observability/",
        )

        self.assertIn("AI platform teams are rebuilding their deployment playbooks around observability", content.text)
        self.assertIn("documenting more explicit fallback paths and audit checkpoints", content.text)
        self.assertNotIn("Watch now", content.text)
        self.assertNotIn("ZDNET Recommends", content.text)
        self.assertNotIn("Editor's note:", content.text)

    def test_prefers_theguardian_liveblog_and_drops_live_feed_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("theguardian-liveblog.html"),
            url="https://www.theguardian.com/technology/live/2026/apr/09/ai-operations-live",
        )

        self.assertIn("enterprise AI programs are now judged on operational resilience", content.text)
        self.assertIn("rollback paths, human approvals, and incident review discipline", content.text)
        self.assertNotIn("Live feed", content.text)
        self.assertNotIn("11.05 AM BST", content.text)
        self.assertNotIn("Most viewed", content.text)

    def test_prefers_venturebeat_article_content_and_drops_related_story_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("venturebeat-article.html"),
            url="https://venturebeat.com/ai/open-source-ai-infrastructure-startups-keep-finding-enterprise-demand/",
        )

        self.assertIn("Enterprise infrastructure teams still want open model optionality", content.text)
        self.assertIn("Operators increasingly evaluate AI vendors on observability", content.text)
        self.assertNotIn("Subscribe to VB Daily", content.text)
        self.assertNotIn("Related stories", content.text)

    def test_prefers_wired_body_container_and_drops_recirculation_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("wired-article.html"),
            url="https://www.wired.com/story/ai-infrastructure-feature/",
        )

        self.assertIn("Wired reports that AI teams are rebuilding evaluation stacks", content.text)
        self.assertIn("observability, fallback paths, and governance", content.text)
        self.assertNotIn("Most Popular", content.text)

    def test_prefers_reuters_article_body_and_drops_standards_footer(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("reuters-blog.html"),
            url="https://www.reuters.com/world/us/enterprise-ai-operations-2026-04-08/",
        )

        self.assertIn("Reuters writes that enterprise buyers are shifting from pilot programs", content.text)
        self.assertIn("fit procurement, security review, and incident response processes", content.text)
        self.assertNotIn("Thomson Reuters Trust Principles", content.text)

    def test_prefers_substack_body_and_drops_subscription_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("substack-article.html"),
            url="https://latentops.substack.com/p/managed-ai-operations",
        )

        self.assertIn("the hardest work shifts from prompts to operating procedures", content.text)
        self.assertIn("deployment lessons matter as much as research announcements", content.text)
        self.assertNotIn("Subscribe now", content.text)
        self.assertNotIn("Leave a comment", content.text)

    def test_prefers_yahoo_syndication_body_and_drops_recirculation_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("yahoo-syndication.html"),
            url="https://finance.yahoo.com/news/ai-deployment-discipline-board-level-topic-090000123.html",
        )

        self.assertIn("Yahoo syndication pages increasingly surface reporting", content.text)
        self.assertIn("reliable AI products need observability and governance", content.text)
        self.assertNotIn("Recommended Stories", content.text)
        self.assertNotIn("Advertisement", content.text)

    def test_prefers_techcrunch_post_content_variant(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("techcrunch-variant.html"),
            url="https://techcrunch.com/2026/04/08/ai-infra-startups-follow-up/",
        )

        self.assertIn("AI infrastructure startups are increasingly selling cost controls", content.text)
        self.assertIn("routing, caching, and observability layers", content.text)
        self.assertNotIn("Sign up for the TechCrunch AI newsletter", content.text)

    def test_prefers_venturebeat_content_group_variant(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("venturebeat-variant.html"),
            url="https://venturebeat.com/ai/ai-operations-discipline/",
        )

        self.assertIn("AI operations teams are maturing from experimentation", content.text)
        self.assertIn("dashboards for latency, refusals, retrieval quality", content.text)
        self.assertNotIn("Related stories", content.text)

    def test_skips_google_news_aggregate_fixture(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)

        with self.assertRaisesRegex(ExtractionSkippedError, "aggregated Google News shell"):
            extractor.extract_from_html(
                _fixture("google-news-aggregate.html"),
                url="https://news.google.com/rss/articles/demo?oc=5",
            )

    def test_detects_access_challenge_page_as_blocked(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)

        with self.assertRaisesRegex(ExtractionBlockedError, "anti-bot challenge"):
            extractor.extract_from_html(
                """
                <html>
                  <head><title>Attention Required</title></head>
                  <body>
                    <h1>Verify you are human</h1>
                    <p>Please enable JavaScript and cookies to continue.</p>
                  </body>
                </html>
                """,
                url="https://venturebeat.com/ai/story",
            )

    def test_fetch_and_extract_resolves_google_news_wrapper_before_extracting(self) -> None:
        class StubResolver:
            def resolve(self, url: str) -> str:
                return "https://techcrunch.com/2026/04/07/arcee/"

        extractor = ArticleContentExtractor(
            timeout=10,
            user_agent="test-agent",
            text_limit=5000,
            google_news_resolver=StubResolver(),
        )

        with patch(
            "ainews.content_extractor.fetch_text",
            return_value=_fixture("techcrunch-article.html"),
        ):
            content = extractor.fetch_and_extract("https://news.google.com/rss/articles/demo?oc=5")

        self.assertEqual(content.resolved_url, "https://techcrunch.com/2026/04/07/arcee/")
        self.assertIn("Arcee is trying to build a credible open source model company", content.text)

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
