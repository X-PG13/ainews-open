import unittest

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

HTML_36KR = """
<html>
  <head><title>36Kr AI Story</title></head>
  <body>
    <div class="kr-layout-main clearfloat">
      <div class="article-share">share tools</div>
      <div class="recommend-list">推荐阅读</div>
      <div class="common-width content articleDetailContent kr-rich-text-wrapper">
        <p>国内 AI 创业公司正在重新评估模型部署与推理成本，以便找到更健康的商业化路径。</p>
        <p>多家企业表示，随着推理芯片与推理框架能力提升，过去无法上线的大模型场景开始进入生产环境。</p>
        <p>投资人更关注那些拥有行业数据、工作流入口和长期续费能力的产品型团队，而不是单次项目制收入。</p>
        <p>团队也在把 Agent、检索增强生成与企业知识库结合，尝试提升复杂任务的自动化完成率。</p>
      </div>
      <div class="entry-operate">点赞 收藏 分享</div>
    </div>
  </body>
</html>
"""

HTML_ITHOME = """
<html>
  <head><title>IT之家 AI Story</title></head>
  <body>
    <div class="content-breadcrumb">首页 > 科技</div>
    <div id="paragraph">
      <p>IT之家 4 月 7 日消息，国内外厂商正在密集发布新的 AI 终端与模型服务，市场竞争显著加速。</p>
      <p>供应链人士表示，端侧模型与云侧推理的协同将成为下一阶段产品体验优化的关键环节。</p>
      <p>多家开发团队已经将语音理解、视觉识别和知识问答整合为统一的智能助手产品形态。</p>
      <p>企业用户则更关心可靠性、审计能力以及与现有业务系统的集成成本，而不仅仅是模型参数规模。</p>
    </div>
    <div class="news_tags">相关推荐 热门标签</div>
  </body>
</html>
"""


class ContentExtractorTestCase(unittest.TestCase):
    def test_extracts_main_article_text(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(HTML_SAMPLE)

        self.assertEqual(content.title, "Sample AI Story")
        self.assertIn("Artificial intelligence is changing enterprise software.", content.text)
        self.assertNotIn("site nav", content.text)

    def test_prefers_36kr_article_container_and_drops_site_noise(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(HTML_36KR, url="https://36kr.com/p/123456789")

        self.assertIn("国内 AI 创业公司正在重新评估模型部署与推理成本", content.text)
        self.assertNotIn("推荐阅读", content.text)
        self.assertNotIn("点赞 收藏 分享", content.text)

    def test_prefers_ithome_paragraph_container_and_drops_breadcrumb(self) -> None:
        extractor = ArticleContentExtractor(timeout=10, user_agent="test-agent", text_limit=5000)
        content = extractor.extract_from_html(HTML_ITHOME, url="https://www.ithome.com/0/123/456.htm")

        self.assertIn("国内外厂商正在密集发布新的 AI 终端与模型服务", content.text)
        self.assertNotIn("首页 > 科技", content.text)
        self.assertNotIn("相关推荐 热门标签", content.text)


if __name__ == "__main__":
    unittest.main()
