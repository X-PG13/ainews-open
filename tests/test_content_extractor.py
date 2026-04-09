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

    def test_prefers_newyorker_column_body_and_drops_author_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("newyorker-column.html"),
            url="https://www.newyorker.com/news/columnists/why-ai-governance-became-product-work",
        )

        self.assertIn("AI governance has quietly become product work", content.text)
        self.assertIn("review queues, approval steps, and rollback design", content.text)
        self.assertNotIn("Listen to this story", content.text)
        self.assertNotIn("About the author", content.text)
        self.assertNotIn("Most Popular", content.text)

    def test_prefers_fortune_column_body_and_drops_promo_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("fortune-column.html"),
            url="https://fortune.com/2026/04/09/ai-oversight-moving-from-policy-to-operations/",
        )

        self.assertIn("AI oversight is moving from policy memos into day-to-day operations", content.text)
        self.assertIn("observability, controlled rollback, and explicit review ownership", content.text)
        self.assertNotIn("Subscribe to Fortune Daily", content.text)
        self.assertNotIn("Read more from Fortune", content.text)
        self.assertNotIn("Most Popular", content.text)

    def test_prefers_inc_column_body_and_drops_premium_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("inc-column.html"),
            url="https://www.inc.com/2026/04/09/founders-forced-to-operationalize-ai-risk.html",
        )

        self.assertIn("founders are being forced to operationalize AI risk", content.text)
        self.assertIn("approval paths, auditability, and fallback logic", content.text)
        self.assertNotIn("Inc. Premium", content.text)
        self.assertNotIn("Recommended Reading", content.text)
        self.assertNotIn("Subscribe to the newsletter", content.text)

    def test_prefers_bloomberg_paywall_body_and_drops_terminal_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("bloomberg-paywall.html"),
            url="https://www.bloomberg.com/news/articles/2026-04-09/ai-governance-shifts-into-operations",
        )

        self.assertIn("AI governance is moving out of policy decks and into operating routines", content.text)
        self.assertIn("workflow review points, rollback ownership, and incident drills", content.text)
        self.assertNotIn("Before it's here, it's on the Bloomberg Terminal.", content.text)
        self.assertNotIn("Read next", content.text)
        self.assertNotIn("Sign up for the New Economy Daily", content.text)

    def test_prefers_wsj_paywall_body_and_drops_subscription_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("wsj-paywall.html"),
            url="https://www.wsj.com/tech/ai/companies-turn-ai-oversight-into-daily-operations-12345678",
        )

        self.assertIn("Companies are treating AI oversight as a daily operating system problem", content.text)
        self.assertIn("procurement checks, approval queues, and post-incident review", content.text)
        self.assertNotIn("Continue reading your article with a WSJ subscription", content.text)
        self.assertNotIn("Listen to article", content.text)
        self.assertNotIn("Recommended Videos", content.text)

    def test_prefers_economist_body_and_drops_subscriber_audio_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("economist-paywall.html"),
            url="https://www.economist.com/business/2026/04/09/why-ai-operations-now-look-like-risk-management",
        )

        self.assertIn("AI operations now resemble risk management more than experimental prototyping", content.text)
        self.assertIn("deployment controls, auditable approval paths, and fallback procedures", content.text)
        self.assertNotIn("Subscribers only", content.text)
        self.assertNotIn("Listen to this episode", content.text)
        self.assertNotIn("Read more from this section", content.text)

    def test_prefers_cnn_explainer_body_and_drops_newsletter_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("cnn-explainer.html"),
            url="https://www.cnn.com/2026/04/09/tech/ai-explainer-operations-guide/index.html",
        )

        self.assertIn("AI oversight is becoming a repeatable operating procedure", content.text)
        self.assertIn("review queues, rollback drills, and named escalation owners", content.text)
        self.assertNotIn("Watch this interactive", content.text)
        self.assertNotIn("Read more from CNN", content.text)
        self.assertNotIn("Sign up for our newsletter", content.text)

    def test_prefers_nytimes_explainer_body_and_drops_audio_and_ad_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("nytimes-explainer.html"),
            url="https://www.nytimes.com/2026/04/09/technology/ai-explainer-why-operations-now-matter.html",
        )

        self.assertIn("AI systems now demand operating discipline after launch", content.text)
        self.assertIn("approval chains, fallback procedures, and post-incident review", content.text)
        self.assertNotIn("Listen to this article", content.text)
        self.assertNotIn("More on A.I.", content.text)
        self.assertNotIn("Advertisement", content.text)

    def test_prefers_washingtonpost_guide_body_and_drops_gift_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("washingtonpost-guide.html"),
            url="https://www.washingtonpost.com/technology/2026/04/09/ai-operations-guide/",
        )

        self.assertIn("AI deployment teams are building guidebooks instead of one-off launch plans", content.text)
        self.assertIn("documenting failure thresholds, human review, and rollback ownership", content.text)
        self.assertNotIn("Try 1 month for $1", content.text)
        self.assertNotIn("Listen", content.text)
        self.assertNotIn("Read more from The Post", content.text)

    def test_prefers_vox_roundup_body_and_drops_recirculation_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("vox-roundup.html"),
            url="https://www.vox.com/technology/2026/04/09/ai-what-to-know-this-week",
        )

        self.assertIn("AI teams are increasingly judged on the quality of their operating routines", content.text)
        self.assertIn("observability reviews, rollback drills, and named escalation paths", content.text)
        self.assertNotIn("Most Popular", content.text)
        self.assertNotIn("Sign up for the newsletter", content.text)
        self.assertNotIn("Read More Vox coverage", content.text)

    def test_prefers_time_roundup_body_and_drops_audio_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("time-roundup.html"),
            url="https://time.com/7270012/ai-what-to-know-enterprise-operations/",
        )

        self.assertIn("AI adoption now depends less on model novelty and more on operating discipline", content.text)
        self.assertIn("approval queues, fallback plans, and incident ownership", content.text)
        self.assertNotIn("Listen to the story", content.text)
        self.assertNotIn("What to read next", content.text)
        self.assertNotIn("Subscribe to the Time newsletter", content.text)

    def test_prefers_nbcnews_roundup_body_and_drops_related_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("nbcnews-roundup.html"),
            url="https://www.nbcnews.com/tech/ai/what-to-know-about-ai-operations-rcna123456",
        )

        self.assertIn("AI operators are spending more time on supervision than on launch-day demos", content.text)
        self.assertIn("documented guardrails, human review, and clear rollback thresholds", content.text)
        self.assertNotIn("Watch more from NBC News", content.text)
        self.assertNotIn("Sign up for our newsletters", content.text)
        self.assertNotIn("Related coverage", content.text)

    def test_prefers_fastcompany_interview_body_and_drops_newsletter_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("fastcompany-interview.html"),
            url="https://www.fastcompany.com/2026/04/09/ai-operations-interview",
        )

        self.assertIn("Interviewers increasingly ask AI operators how they handle failure after launch", content.text)
        self.assertIn("approval ladders, rollback drills, and incident notes", content.text)
        self.assertNotIn("Listen to the interview", content.text)
        self.assertNotIn("Read more from Fast Company", content.text)
        self.assertNotIn("Sign up for the newsletter", content.text)

    def test_prefers_businessinsider_qa_body_and_drops_promo_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("businessinsider-qa.html"),
            url="https://www.businessinsider.com/ai-ops-qa-why-governance-became-an-operations-problem-2026-4",
        )

        self.assertIn("Q: What changed once companies moved AI tools into regular workflows?", content.text)
        self.assertIn("A: Teams started tracking review ownership, exception paths, and rollback triggers.", content.text)
        self.assertNotIn("Read next", content.text)
        self.assertNotIn("Get Business Insider intelligence in your inbox", content.text)
        self.assertNotIn("Listen to the conversation", content.text)

    def test_prefers_ieee_spectrum_transcript_body_and_drops_audio_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("ieee-spectrum-transcript.html"),
            url="https://spectrum.ieee.org/ai-operations-transcript",
        )

        self.assertIn("Q: Why are companies treating AI operations as a governance problem now?", content.text)
        self.assertIn("A: Because production systems need documented fallback plans and accountable human review.", content.text)
        self.assertNotIn("Listen to this episode", content.text)
        self.assertNotIn("More from IEEE Spectrum", content.text)
        self.assertNotIn("Subscribe to our newsletters", content.text)

    def test_prefers_theatlantic_longform_body_and_drops_audio_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("theatlantic-longform.html"),
            url="https://www.theatlantic.com/technology/archive/2026/04/why-ai-operations-became-governance/123456/",
        )

        self.assertIn("AI operations has become the place where governance claims are tested", content.text)
        self.assertIn("review queues, rollback drills, and ownership boundaries", content.text)
        self.assertNotIn("Listen to the article", content.text)
        self.assertNotIn("Read more from The Atlantic", content.text)
        self.assertNotIn("Sign up for The Atlantic Daily", content.text)

    def test_prefers_foreignpolicy_longform_body_and_drops_subscription_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("foreignpolicy-longform.html"),
            url="https://foreignpolicy.com/2026/04/09/ai-operations-governance-analysis/",
        )

        self.assertIn("AI strategy is increasingly judged by how systems are supervised after launch", content.text)
        self.assertIn("approval paths, incident review, and controlled rollback", content.text)
        self.assertNotIn("Subscribe to Foreign Policy", content.text)
        self.assertNotIn("Read More", content.text)
        self.assertNotIn("Listen to the conversation", content.text)

    def test_prefers_newstatesman_longform_body_and_drops_audio_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("newstatesman-longform.html"),
            url="https://www.newstatesman.com/technology/2026/04/how-ai-operations-became-a-political-economy-question",
        )

        self.assertIn("Longform analysis of AI now spends more time on operating discipline than on model spectacle", content.text)
        self.assertIn("fallback planning, escalation rules, and post-incident accountability", content.text)
        self.assertNotIn("Listen to this piece", content.text)
        self.assertNotIn("Continue reading with a subscription", content.text)
        self.assertNotIn("Recommended", content.text)

    def test_prefers_brookings_policy_memo_body_and_drops_briefing_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("brookings-policy-memo.html"),
            url="https://www.brookings.edu/articles/2026/04/09/ai-governance-needs-operators-not-just-policies/",
        )

        self.assertIn("Policy teams are learning that AI governance only works when operators own the control points", content.text)
        self.assertIn("approval ladders, rollback drills, and escalation playbooks", content.text)
        self.assertNotIn("Sign up for Brookings newsletters", content.text)
        self.assertNotIn("Related Content", content.text)
        self.assertNotIn("Listen to this policy brief", content.text)

    def test_prefers_rand_research_note_body_and_drops_audio_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("rand-research-note.html"),
            url="https://www.rand.org/pubs/research_reports/2026/ai-operations-under-pressure.html",
        )

        self.assertIn("Research teams studying enterprise AI deployments now focus on how systems fail after launch", content.text)
        self.assertIn("review queues, monitored rollback paths, and incident rehearsal", content.text)
        self.assertNotIn("Listen to the article", content.text)
        self.assertNotIn("Related RAND research", content.text)
        self.assertNotIn("Get RAND insights in your inbox", content.text)

    def test_prefers_restofworld_feature_body_and_drops_pullquote_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("restofworld-feature.html"),
            url="https://restofworld.org/2026/ai-operators-are-doing-the-unseen-work-of-governance/",
        )

        self.assertIn("Magazine-style features about AI now spend more time on the invisible operating labor after launch", content.text)
        self.assertIn("runbooks, exception handling, and who gets paged when a model starts drifting", content.text)
        self.assertNotIn("Listen to the story", content.text)
        self.assertNotIn("Read more from Rest of World", content.text)
        self.assertNotIn("The system is only as trustworthy as the people rehearsing the fallback path.", content.text)

    def test_prefers_mckinsey_whitepaper_body_and_drops_report_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("mckinsey-whitepaper.html"),
            url="https://www.mckinsey.com/capabilities/quantumblack/our-insights/2026/04/ai-operations-benchmark",
        )

        self.assertIn("Executives reviewing AI programs now ask for evidence that operating controls survive real incident pressure", content.text)
        self.assertIn("approval checkpoints, rollback ownership, and escalation paths", content.text)
        self.assertNotIn("Listen to the article", content.text)
        self.assertNotIn("Explore more insights", content.text)
        self.assertNotIn("Download the full report", content.text)

    def test_prefers_cloud_google_benchmark_body_and_drops_methodology_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("cloud-google-benchmark.html"),
            url="https://cloud.google.com/blog/products/ai-machine-learning/ai-inference-benchmark-operations-guide",
        )

        self.assertIn("Benchmark writeups now matter less for raw throughput than for the operating discipline around rollout", content.text)
        self.assertIn("fallback controls, rollback sequencing, and clear human escalation", content.text)
        self.assertNotIn("Benchmark methodology", content.text)
        self.assertNotIn("Related products", content.text)
        self.assertNotIn("Listen to this benchmark note", content.text)

    def test_prefers_databricks_case_study_body_and_drops_video_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("databricks-case-study.html"),
            url="https://www.databricks.com/resources/case-studies/ai-ops-governance-at-scale",
        )

        self.assertIn("Enterprise case studies now emphasize the operating work required after AI launch", content.text)
        self.assertIn("named owners, incident review, and the safeguards that keep models useful during drift", content.text)
        self.assertNotIn("Watch the customer story", content.text)
        self.assertNotIn("Read related resources", content.text)
        self.assertNotIn("Sign up for Databricks updates", content.text)

    def test_prefers_techpolicy_press_recap_body_and_drops_event_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("techpolicypress-recap.html"),
            url="https://www.techpolicy.press/2026/04/09/what-the-ai-governance-summit-revealed-about-operations/",
        )

        self.assertIn("Conference recaps are increasingly about the operational systems behind AI promises", content.text)
        self.assertIn("incident review, escalation ownership, and fallback discipline", content.text)
        self.assertNotIn("Event recap hub", content.text)
        self.assertNotIn("Related posts", content.text)
        self.assertNotIn("Listen to the session recap", content.text)

    def test_prefers_a16z_event_takeaways_body_and_drops_session_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("a16z-event-takeaways.html"),
            url="https://a16z.com/2026/04/09/ai-infrastructure-event-takeaways/",
        )

        self.assertIn("Event takeaway posts now spend less time on stagecraft and more on the systems that keep AI products reliable", content.text)
        self.assertIn("review checkpoints, rollback readiness, and how teams practice failure before customers see it", content.text)
        self.assertNotIn("Watch the full session", content.text)
        self.assertNotIn("More from a16z", content.text)
        self.assertNotIn("Subscribe for future updates", content.text)

    def test_prefers_ted_transcript_summary_body_and_drops_transcript_nav_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("ted-transcript-summary.html"),
            url="https://www.ted.com/talks/2026/ai_operators_and_the_hidden_work_of_reliability/transcript",
        )

        self.assertIn("Transcript-summary pages are useful only when the editorial framing survives the transcript scaffolding", content.text)
        self.assertIn("what matters after launch is who reviews exceptions and how teams recover when models drift", content.text)
        self.assertNotIn("Transcript navigation", content.text)
        self.assertNotIn("More TED talks on AI", content.text)
        self.assertNotIn("Listen to the episode", content.text)

    def test_prefers_aws_best_practices_body_and_drops_checklist_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("aws-best-practices-guide.html"),
            url="https://aws.amazon.com/architecture/2026/04/ai-operations-best-practices/",
        )

        self.assertIn("Best-practices guides are increasingly explicit about what AI teams must rehearse before launch", content.text)
        self.assertIn("approval checkpoints, rollback exercises, and fallback ownership", content.text)
        self.assertNotIn("Best practices checklist", content.text)
        self.assertNotIn("Related AWS guidance", content.text)
        self.assertNotIn("Watch the walkthrough", content.text)

    def test_prefers_anthropic_troubleshooting_body_and_drops_help_nav_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("anthropic-troubleshooting.html"),
            url="https://docs.anthropic.com/en/docs/troubleshooting/ai-operations-incident-response",
        )

        self.assertIn("Troubleshooting docs become more useful when they explain how operators should respond after a model misbehaves in production", content.text)
        self.assertIn("retry boundaries, human escalation, and how to recover without compounding the incident", content.text)
        self.assertNotIn("Troubleshooting menu", content.text)
        self.assertNotIn("Related topics", content.text)
        self.assertNotIn("Need more help?", content.text)

    def test_prefers_microsoft_faq_body_and_drops_resource_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("microsoft-faq-guide.html"),
            url="https://learn.microsoft.com/en-us/azure/ai-services/faq/operational-governance",
        )

        self.assertIn("FAQ pages are valuable when they answer the operational questions teams ask after the first outage or rollback", content.text)
        self.assertIn("who approves risky changes, how recovery is triggered, and what gets documented for review", content.text)
        self.assertNotIn("Additional resources", content.text)
        self.assertNotIn("Feedback", content.text)
        self.assertNotIn("Training available", content.text)

    def test_prefers_cohere_api_reference_body_and_drops_nav_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("cohere-api-reference.html"),
            url="https://docs.cohere.com/reference/ai-operations-recovery-playbook",
        )

        self.assertIn(
            "API reference pages are only useful when operators can map endpoints to real recovery behavior",
            content.text,
        )
        self.assertIn("retry limits, escalation paths, and safe fallback defaults", content.text)
        self.assertNotIn("API reference menu", content.text)
        self.assertNotIn("Related endpoints", content.text)
        self.assertNotIn("Need help with integration?", content.text)

    def test_prefers_nvidia_reference_body_and_drops_checklist_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("nvidia-reference-guide.html"),
            url="https://developer.nvidia.com/blog/ai-operations-reference-guide",
        )

        self.assertIn(
            "Reference guides for AI infrastructure now double as operating manuals for teams under load",
            content.text,
        )
        self.assertIn("rollback thresholds, observable failure modes", content.text)
        self.assertIn("who owns", content.text)
        self.assertNotIn("Performance checklist", content.text)
        self.assertNotIn("Related NVIDIA guides", content.text)
        self.assertNotIn("Watch the walkthrough", content.text)

    def test_prefers_vercel_changelog_body_and_drops_update_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("vercel-changelog-update.html"),
            url="https://vercel.com/changelog/ai-operations-reliability-updates",
        )

        self.assertIn(
            "Product updates are more credible when changelog entries explain what changed in operations",
            content.text,
        )
        self.assertIn("deployment sequencing, incident ownership", content.text)
        self.assertIn("how teams should verify", content.text)
        self.assertNotIn("Read the changelog", content.text)
        self.assertNotIn("Related updates", content.text)
        self.assertNotIn("Watch the launch clip", content.text)

    def test_prefers_langchain_migration_guide_body_and_drops_nav_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("langchain-migration-guide.html"),
            url="https://docs.langchain.com/docs/migration/ai-operations-observability",
        )

        self.assertIn("Migration guides are useful only when they explain how operators move production systems", content.text)
        self.assertIn("losing observability", content.text)
        self.assertIn("cutover steps, fallback plans", content.text)
        self.assertIn("which dashboards must stay", content.text)
        self.assertIn("comparable", content.text)
        self.assertNotIn("Migration guide menu", content.text)
        self.assertNotIn("Related migration steps", content.text)
        self.assertNotIn("Was this page helpful?", content.text)

    def test_prefers_atlassian_deprecation_notice_body_and_drops_banner_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("atlassian-deprecation-notice.html"),
            url="https://developer.atlassian.com/platform/ai/deprecations/incident-response-api",
        )

        self.assertIn("Deprecation notices matter when they tell operators what breaks", content.text)
        self.assertIn("how to", content.text)
        self.assertIn("migrate safely", content.text)
        self.assertIn("shutdown dates, compatibility windows", content.text)
        self.assertIn("which ownership checks must be", content.text)
        self.assertIn("updated", content.text)
        self.assertNotIn("Deprecation timeline", content.text)
        self.assertNotIn("Related Atlassian docs", content.text)
        self.assertNotIn("Was this helpful?", content.text)

    def test_prefers_supabase_upgrade_guide_body_and_drops_cta_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("supabase-upgrade-guide.html"),
            url="https://supabase.com/docs/guides/upgrade/ai-operations-rollout",
        )

        self.assertIn("Upgrade guides are strongest when they tell teams how to move production traffic", content.text)
        self.assertIn("hiding new", content.text)
        self.assertIn("failure modes", content.text)
        self.assertIn("verification steps, rollback handles", content.text)
        self.assertIn("how incident review should", content.text)
        self.assertIn("change", content.text)
        self.assertNotIn("Watch the migration walkthrough", content.text)
        self.assertNotIn("Related upgrade guides", content.text)
        self.assertNotIn("Start building", content.text)

    def test_prefers_openai_deprecation_faq_body_and_drops_sidebar_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("openai-deprecation-faq.html"),
            url="https://platform.openai.com/docs/deprecations/faq/ai-operations-endpoint-retirement",
        )

        self.assertIn("Deprecation FAQs are useful when they answer what changes for operators", content.text)
        self.assertIn("which runbooks must", content.text)
        self.assertIn("change", content.text)
        self.assertIn("how compatibility windows affect production traffic", content.text)
        self.assertNotIn("Service retirement banner", content.text)
        self.assertNotIn("Related answers", content.text)
        self.assertNotIn("Was this helpful?", content.text)

    def test_prefers_pinecone_migration_checklist_body_and_drops_checklist_nav_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("pinecone-migration-checklist.html"),
            url="https://docs.pinecone.io/guides/migration/ai-operations-checklist",
        )

        self.assertIn("Migration checklists are most valuable when they tell teams what must be verified", content.text)
        self.assertIn("before traffic", content.text)
        self.assertIn("shifts", content.text)
        self.assertIn("rollback handles stay available", content.text)
        self.assertIn("incident checkpoints", content.text)
        self.assertNotIn("Step navigation", content.text)
        self.assertNotIn("Related Pinecone guides", content.text)
        self.assertNotIn("Need more help?", content.text)

    def test_prefers_vllm_version_notice_body_and_drops_version_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("vllm-version-notice.html"),
            url="https://docs.vllm.ai/en/latest/notes/versioned/ai-operations-upgrade-notice.html",
        )

        self.assertIn("Versioned docs notices matter when they explain what changed between supported releases", content.text)
        self.assertIn("operator expectations", content.text)
        self.assertIn("fallback procedures and benchmark comparability", content.text)
        self.assertNotIn("Version notice", content.text)
        self.assertNotIn("Related versioned pages", content.text)
        self.assertNotIn("Edit on GitHub", content.text)

    def test_prefers_llamaindex_compatibility_matrix_body_and_drops_matrix_nav_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("llamaindex-compatibility-matrix.html"),
            url="https://docs.llamaindex.ai/en/stable/getting_started/compatibility/ai-operations-matrix",
        )

        self.assertIn("Compatibility matrices are useful when they tell operators which model providers", content.text)
        self.assertIn("fallback behavior changes", content.text)
        self.assertIn("upgrade combinations remain safe", content.text)
        self.assertIn("rollback limits should", content.text)
        self.assertIn("influence release planning", content.text)
        self.assertNotIn("Compatibility matrix", content.text)
        self.assertNotIn("Matrix navigation", content.text)
        self.assertNotIn("Related LlamaIndex docs", content.text)

    def test_prefers_together_support_policy_body_and_drops_support_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("together-support-policy.html"),
            url="https://docs.together.ai/docs/support-policy/ai-inference-ops",
        )

        self.assertIn("Support policies are useful when they spell out what service levels apply", content.text)
        self.assertIn("which model versions receive security fixes", content.text)
        self.assertIn("migrations before support", content.text)
        self.assertIn("windows close", content.text)
        self.assertIn("rollback expectations", content.text)
        self.assertNotIn("Support policy", content.text)
        self.assertNotIn("Related Together docs", content.text)
        self.assertNotIn("Need more help?", content.text)

    def test_prefers_fireworks_release_channel_note_body_and_drops_channel_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("fireworks-release-channel-note.html"),
            url="https://docs.fireworks.ai/guides/release-channels/enterprise-ai-ops",
        )

        self.assertIn("Release-channel notes matter when they explain which preview and stable tracks", content.text)
        self.assertIn("rollout timing affects benchmark parity", content.text)
        self.assertIn("rollback triggers, incident ownership", content.text)
        self.assertIn("stable channel changes", content.text)
        self.assertNotIn("Release channels", content.text)
        self.assertNotIn("Related Fireworks guides", content.text)
        self.assertNotIn("Edit this page", content.text)

    def test_prefers_openai_status_incident_update_body_and_drops_status_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("openai-status-incident-update.html"),
            url="https://status.openai.com/incidents/inference-latency-event",
        )

        self.assertIn("Incident updates are useful when they explain which mitigation steps restored service", content.text)
        self.assertIn("shifted away from the failing path", content.text)
        self.assertIn("rollback path is still", content.text)
        self.assertIn("active", content.text)
        self.assertNotIn("Affected components", content.text)
        self.assertNotIn("Status update banner", content.text)
        self.assertNotIn("Subscribe to updates", content.text)

    def test_prefers_pinecone_postmortem_body_and_drops_postmortem_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("pinecone-postmortem.html"),
            url="https://status.pinecone.io/incidents/vector-index-write-degradation-postmortem",
        )

        self.assertIn("Postmortems are valuable when they explain the technical trigger", content.text)
        self.assertIn("operational safeguards that", content.text)
        self.assertIn("failed", content.text)
        self.assertIn("rollback boundaries", content.text)
        self.assertIn("instrumentation changes", content.text)
        self.assertNotIn("Postmortem metadata", content.text)
        self.assertNotIn("Related incidents", content.text)
        self.assertNotIn("Subscribe to incident updates", content.text)

    def test_prefers_together_outage_rca_body_and_drops_incident_nav_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(
            _fixture("together-outage-rca.html"),
            url="https://status.together.ai/incidents/model-gateway-saturation-rca",
        )

        self.assertIn("Outage RCAs matter when they show how an overload propagated through the serving stack", content.text)
        self.assertIn("emergency controls reduced customer impact", content.text)
        self.assertIn("recovery checks teams", content.text)
        self.assertIn("must repeat before removing temporary safeguards", content.text)
        self.assertNotIn("Impact summary", content.text)
        self.assertNotIn("Related incidents", content.text)
        self.assertNotIn("Incident navigation", content.text)

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
