from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[assignment]

from .google_news import GoogleNewsResolutionError, GoogleNewsURLResolver, is_google_news_url
from .http import fetch_text
from .utils import clean_text

ARTICLE_HINTS = (
    "article",
    "content",
    "entry",
    "post",
    "story",
    "main",
    "body",
    "markdown",
)
DROP_HINTS = (
    "nav",
    "menu",
    "footer",
    "header",
    "comment",
    "related",
    "recommend",
    "share",
    "social",
    "toolbar",
    "breadcrumb",
    "subscribe",
    "popup",
    "banner",
    "sidebar",
)

DROP_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "header",
    "footer",
    "nav",
    "form",
    "aside",
    "iframe",
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
NOISE_LINE_PATTERNS = (
    re.compile(r"^(责任编辑|责编|编辑)[:：]"),
    re.compile(r"^(文章来源|本文来源|来源)[:：]"),
    re.compile(r"^本文(来自|转载自|由)"),
    re.compile(r"^(扫码|长按|点击).{0,12}(查看|关注|下载|阅读)"),
    re.compile(r"^(更多|相关阅读|延伸阅读|相关推荐|相关内容)"),
    re.compile(r"^(打开|下载)(APP|客户端)"),
    re.compile(r"^(微信|公众号|微博)[:：]"),
    re.compile(r"^分享至"),
)
NOISE_PHRASES = (
    "返回搜狐",
    "打开APP",
    "点击查看更多",
    "责任编辑",
    "相关推荐",
    "相关阅读",
)
HOST_SELECTORS = {
    "36kr.com": (
        ".common-width.content.articleDetailContent.kr-rich-text-wrapper",
        ".articleDetailContent.kr-rich-text-wrapper",
        ".kr-rich-text-wrapper",
        ".article-content",
    ),
    "ithome.com": (
        "#paragraph",
        ".news-content",
        ".post-content",
        ".content",
    ),
    "tmtpost.com": (
        "article",
        ".article__content",
        ".post-content",
        ".content",
    ),
    "jiqizhixin.com": (
        ".article__content",
        ".article-content",
        ".post-content",
    ),
    "huggingface.co": (
        ".blog-content.prose",
        ".blog-content",
    ),
    "blog.google": (
        ".article-container__content",
        ".uni-blog-article-container.article-container__content",
        ".uni-article-wrapper",
    ),
    "deepmind.google": (
        ".article-container__content",
        ".uni-blog-article-container.article-container__content",
        ".uni-article-wrapper",
    ),
    "theverge.com": (
        ".duet--layout--entry-body",
        ".duet--article--article-body-component",
    ),
    "techcrunch.com": (
        ".entry-content",
        ".wp-block-post-content",
        ".article-content",
    ),
    "venturebeat.com": (
        ".article-content",
        ".entry-content",
        ".article-content__content-group",
    ),
    "wired.com": (
        ".body__inner-container",
        ".article__body",
        ".ContentBodyWrapper",
    ),
    "reuters.com": (
        ".article-body__content__17Yit",
        ".article-body__content",
        "[data-testid='paragraph-0']",
    ),
    "arstechnica.com": (
        ".article-content",
        ".post-content",
        "article",
    ),
    "technologyreview.com": (
        ".content--body",
        ".article-body__content",
        ".article-body",
    ),
    "axios.com": (
        ".gtm-story-text",
        ".story-body",
        ".article-body",
    ),
    "apnews.com": (
        ".RichTextStoryBody",
        ".RichTextBody",
        ".Page-content",
    ),
    "bbc.com": (
        ".qa-story-body",
        ".lx-stream-post-body",
        ".ssrcss-11r1m41-RichTextComponentWrapper",
    ),
    "cnbc.com": (
        ".ArticleBody-articleBody",
        ".group",
        ".ArticleBodyWrapper",
    ),
    "ft.com": (
        ".article__content-body",
        ".n-content-body",
        ".article-body",
    ),
    "semafor.com": (
        ".article-content",
        ".story-body",
        ".article-body",
    ),
    "morningbrew.com": (
        ".article-body",
        ".post-content",
        ".content-body",
    ),
    "theinformation.com": (
        ".article__body",
        ".article-body",
        ".paywall-layout__body",
    ),
    "engadget.com": (
        ".article-text",
        ".article-body",
        ".body-text",
    ),
    "forbes.com": (
        ".article-body",
        ".body-container",
        ".article-content",
    ),
    "zdnet.com": (
        ".storyBody",
        ".article-body",
        ".c-ShortcodeContent",
    ),
    "newyorker.com": (
        ".body__inner-container",
        ".article__body",
        ".content-body",
    ),
    "fortune.com": (
        ".article-body",
        ".paywall",
        ".content-wrapper",
    ),
    "inc.com": (
        ".article-body",
        ".article-content",
        ".single-post-content",
    ),
    "bloomberg.com": (
        ".body-copy-v2",
        ".article-body",
        ".paywall-content",
    ),
    "wsj.com": (
        ".wsj-snippet-body",
        ".article-content",
        ".paywall",
    ),
    "economist.com": (
        ".article__body-text",
        ".layout-article-body",
        ".article-text",
    ),
    "cnn.com": (
        ".article__content",
        ".article__main",
        ".wysiwyg",
    ),
    "nytimes.com": (
        ".StoryBodyCompanionColumn",
        ".article-body",
        ".css-at9mc1",
    ),
    "washingtonpost.com": (
        ".article-body",
        ".story-body",
        ".article-body-content",
    ),
    "vox.com": (
        ".duet--article--article-body-component",
        ".c-entry-content",
        ".article-body",
    ),
    "time.com": (
        ".article-body__content",
        ".body-wrapper",
        ".article-content",
    ),
    "nbcnews.com": (
        ".article-body",
        ".article-body__content",
        ".article-content",
    ),
    "fastcompany.com": (
        ".article-body",
        ".prose",
        ".content-body",
    ),
    "businessinsider.com": (
        ".content-lock-content",
        ".article-body",
        ".post-content",
    ),
    "spectrum.ieee.org": (
        ".article-main__content",
        ".article-body",
        ".content-body",
    ),
    "theatlantic.com": (
        ".ArticleBody",
        ".article-body",
        ".ContentBody",
    ),
    "foreignpolicy.com": (
        ".post-content",
        ".article-content",
        ".entry-content",
    ),
    "newstatesman.com": (
        ".article__body",
        ".c-content-body",
        ".article-body",
    ),
    "brookings.edu": (
        ".post-body",
        ".article__content",
        ".wysiwyg",
    ),
    "rand.org": (
        ".article-content",
        ".content-body",
        ".rich-text",
    ),
    "restofworld.org": (
        ".article-body",
        ".story-content",
        ".content-body",
    ),
    "mckinsey.com": (
        ".content-body",
        ".article-body",
        ".wysiwyg",
    ),
    "cloud.google.com": (
        ".compliance-update",
        ".devsite-article-body",
        ".article-body",
        ".case-study-body",
    ),
    "databricks.com": (
        ".article-body",
        ".resource-body",
        ".content-body",
    ),
    "techpolicy.press": (
        ".entry-content",
        ".article-content",
        ".post-content",
    ),
    "a16z.com": (
        ".post-content",
        ".article-content",
        ".entry-content",
    ),
    "ted.com": (
        ".talk-body",
        ".transcript__body",
        ".article-body",
    ),
    "aws.amazon.com": (
        ".awsdocs-content",
        ".article-body",
        ".doc-content",
    ),
    "docs.anthropic.com": (
        ".security-bulletin",
        ".theme-doc-markdown",
        ".docs-content",
        ".article-body",
    ),
    "learn.microsoft.com": (
        ".content-body",
        ".article-body",
        ".main-content",
    ),
    "docs.cohere.com": (
        ".theme-doc-markdown",
        ".docs-content",
        ".reference-body",
    ),
    "docs.fireworks.ai": (
        ".theme-doc-markdown",
        ".docs-content",
        ".release-channel-note",
    ),
    "developer.nvidia.com": (
        ".article-body",
        ".doc-content",
        ".content-body",
    ),
    "vercel.com": (
        ".prose",
        ".content-body",
        ".article-body",
    ),
    "docs.langchain.com": (
        ".theme-doc-markdown",
        ".docs-content",
        ".migration-guide",
    ),
    "docs.llamaindex.ai": (
        ".theme-doc-markdown",
        ".docs-content",
        ".compatibility-matrix",
    ),
    "developer.atlassian.com": (
        ".doc-content",
        ".article-body",
        ".content-body",
    ),
    "supabase.com": (
        ".prose",
        ".content-body",
        ".docs-content",
    ),
    "openai.com": (
        ".content-body",
        ".article-body",
        ".prose",
    ),
    "anthropic.com": (
        ".content-body",
        ".article-body",
        ".prose",
    ),
    "platform.openai.com": (
        ".docs-body",
        ".prose",
        ".article-body",
    ),
    "trust.openai.com": (
        ".trust-center-advisory",
        ".advisory-body",
        ".content-body",
    ),
    "docs.pinecone.io": (
        ".theme-doc-markdown",
        ".docs-content",
        ".migration-checklist",
    ),
    "docs.together.ai": (
        ".docs-body",
        ".content-body",
        ".article-body",
    ),
    "status.openai.com": (
        ".incident-updates-container",
        ".update-body",
        ".incident-body",
    ),
    "status.pinecone.io": (
        ".postmortem-content",
        ".incident-body",
        ".update-body",
    ),
    "status.together.ai": (
        ".incident-detail",
        ".rca-body",
        ".update-body",
    ),
    "together.ai": (
        ".content-body",
        ".article-body",
        ".prose",
    ),
    "docs.vllm.ai": (
        ".md-content",
        ".content-body",
        ".document",
    ),
    "theguardian.com": (
        ".liveblog__body",
        ".content__article-body",
        ".article-body-commercial-selector",
    ),
    "substack.com": (
        ".body.markup",
        ".available-content",
        ".post-content",
    ),
    "yahoo.com": (
        "[data-test-locator='articleBody']",
        ".caas-body",
        ".article-body",
    ),
}
HOST_DROP_SELECTORS = {
    "36kr.com": (
        ".article-detail-item-pre",
        ".article-detail-item-next",
        ".statement",
        ".entry-operate",
        ".kr-loading-more-button",
        ".recommend-list",
        ".article-detail-tags",
        ".article-share",
    ),
    "ithome.com": (
        ".post-side-tools",
        ".related-posts",
        ".relation",
        ".news_pl",
        ".news_tags",
        ".comment-entry",
        ".comment-link",
        ".post-nav",
        ".content-breadcrumb",
        ".video-box",
    ),
    "jiqizhixin.com": (
        ".article__copyright",
        ".article__tags",
        ".related-posts",
        ".recommend-list",
        ".share-box",
        ".author-card",
        ".sidebar-recommend",
    ),
    "huggingface.co": (
        ".blog-content > .mb-4",
        ".blog-content > .not-prose",
    ),
    "blog.google": (
        ".audio-player-tts",
        ".uni-blog-article-tags",
        "uni-youtube-player-article",
        "uni-image-full-width",
        "uni-pull-quote",
    ),
    "deepmind.google": (
        ".audio-player-tts",
        ".uni-blog-article-tags",
        "uni-youtube-player-article",
        "uni-image-full-width",
        "uni-pull-quote",
    ),
    "theverge.com": (
        ".duet--ledes--standard-lede-bottom",
    ),
    "techcrunch.com": (
        ".newsletter-signup",
        ".social-share",
        ".article-tags",
        ".wp-block-jetpack-subscriptions",
        ".wp-block-tc23-shared-social-share",
    ),
    "venturebeat.com": (
        ".newsletter-signup",
        ".article-footer",
        ".more-stories",
        ".share-this",
        ".related-story-list",
    ),
    "wired.com": (
        ".summary__dek",
        ".recirc-list-wrapper",
        ".newsletter-promo",
        ".paywall-barrier",
    ),
    "reuters.com": (
        ".article-footer",
        ".recirc-list",
        ".related-news",
        ".article-topics",
    ),
    "arstechnica.com": (
        ".post-meta",
        ".video-block",
        ".related-stories",
        ".sidebar",
        ".newsletter-callout",
    ),
    "technologyreview.com": (
        ".inline-newsletter",
        ".article-callout",
        ".article-footer__related",
        ".most-popular",
        ".paywall-inline",
    ),
    "axios.com": (
        ".newsletter-card",
        ".story-share-tools",
        ".related-story-list",
        ".sidebar-list",
        ".story-footer",
    ),
    "apnews.com": (
        ".Page-promos",
        ".Page-footer",
        ".RelatedTopics-list",
        ".Carousel",
        ".ad-placeholder",
        ".Timestamp",
        ".UpdateTime",
    ),
    "bbc.com": (
        ".lx-stream-post__meta",
        ".lx-stream-post__header",
        ".lx-stream-post__footer",
        ".lx-share-tools",
        ".bbc-article-tags",
    ),
    "cnbc.com": (
        ".InlineNewsletter-inlineNewsletter",
        ".RelatedContent-relatedContent",
        ".SocialShare-socialShare",
        ".ArticleBody-extra",
        ".group[data-module='recirc']",
    ),
    "ft.com": (
        ".n-content-recommended",
        ".o-teaser-collection",
        ".newsletter-signup",
        ".article-footer",
        ".related-articles",
    ),
    "semafor.com": (
        ".signals-inline",
        ".article-recirculation",
        ".signup-card",
        ".article-footer",
        ".related-stories",
    ),
    "morningbrew.com": (
        ".inline-cta",
        ".newsletter-signup",
        ".related-brews",
        ".share-tools",
        ".post-footer",
    ),
    "theinformation.com": (
        ".subscription-callout",
        ".related-coverage",
        ".article-footer",
        ".signup-promo",
        ".story-meta",
    ),
    "engadget.com": (
        ".video-embed",
        ".podcast-player",
        ".newsletter-inline",
        ".engadget-share",
        ".read-more-links",
    ),
    "forbes.com": (
        ".embed-base",
        ".newsletter-box",
        ".article-share-wrap",
        ".related-articles",
        ".vestpocket",
    ),
    "zdnet.com": (
        ".c-shortcodePodcast",
        ".c-shortcodeVideo",
        ".newsletterSignup",
        ".relatedContent",
        ".adSlot",
    ),
    "newyorker.com": (
        ".contributors__bio",
        ".newsletter-promo",
        ".related-stories",
        ".podcast-unit",
        ".most-popular",
    ),
    "fortune.com": (
        ".inline-newsletter",
        ".most-popular",
        ".premium-upsell",
        ".related-content",
        ".article-footer",
    ),
    "inc.com": (
        ".inline-newsletter",
        ".author-bio",
        ".recommended-reading",
        ".premium-cta",
        ".article-share",
    ),
    "bloomberg.com": (
        ".terminal-promo",
        ".signup-banner",
        ".read-next",
        ".up-next",
        ".inline-newsletter",
    ),
    "wsj.com": (
        ".snippet-promotion",
        ".login-prompt",
        ".related-coverage",
        ".audio-player",
        ".article-share",
    ),
    "economist.com": (
        ".subscription-prompt",
        ".podcast-promo",
        ".related-reading",
        ".newsletter-signup",
        ".article-share",
    ),
    "cnn.com": (
        ".relateds",
        ".newsletter__container",
        ".video-resource",
        ".article__footer",
        ".zone--recommendations",
    ),
    "nytimes.com": (
        ".newsletter-promo",
        ".related-coverage",
        ".css-1bd8bfl",
        ".css-1r7ky0e",
        ".audio-control",
    ),
    "washingtonpost.com": (
        ".gift-prompt",
        ".newsletter-inline",
        ".related-story-list",
        ".audio-player",
        ".story-footer",
    ),
    "vox.com": (
        ".duet--recirculation--related-card-list",
        ".newsletter-signup",
        ".duet--media--embed",
        ".c-entry-box--compact",
        ".duet--article--inline-newsletter",
    ),
    "time.com": (
        ".newsletter-card",
        ".related-articles",
        ".inline-audio",
        ".what-to-read-next",
        ".article-footer",
    ),
    "nbcnews.com": (
        ".related-content",
        ".newsletter-inline",
        ".video-player",
        ".article-share",
        ".what-to-know",
    ),
    "fastcompany.com": (
        ".newsletter-inline",
        ".related-links",
        ".audio-player",
        ".author-bio",
        ".article-footer",
    ),
    "businessinsider.com": (
        ".signup-inline",
        ".read-more-list",
        ".audio-control",
        ".author-card",
        ".premium-upsell",
    ),
    "spectrum.ieee.org": (
        ".podcast-player",
        ".newsletter-signup",
        ".related-articles",
        ".author-card",
        ".article-footer",
    ),
    "theatlantic.com": (
        ".article-sidebar",
        ".newsletter-callout",
        ".listen-bar",
        ".author-note",
        ".related-content",
    ),
    "foreignpolicy.com": (
        ".subscription-banner",
        ".read-next",
        ".podcast-module",
        ".author-bio",
        ".related-coverage",
    ),
    "newstatesman.com": (
        ".newsletter-promo",
        ".audio-player",
        ".author-box",
        ".recommended-links",
        ".article-footer",
    ),
    "brookings.edu": (
        ".newsletter-signup",
        ".inline-promo",
        ".book-promo",
        ".author-bio",
        ".related-content",
    ),
    "rand.org": (
        ".newsletter-module",
        ".audio-player",
        ".related-resources",
        ".author-card",
        ".cta-banner",
    ),
    "restofworld.org": (
        ".pullquote",
        ".newsletter-callout",
        ".related-stories",
        ".audio-player",
        ".author-card",
    ),
    "mckinsey.com": (
        ".newsletter-signup",
        ".listen-module",
        ".related-insights",
        ".author-bio",
        ".download-prompt",
    ),
    "cloud.google.com": (
        ".compliance-sidebar",
        ".security-bulletin-nav",
        ".devsite-page-rating",
        ".newsletter-callout",
        ".benchmark-cta",
        ".related-products",
        ".audio-player",
    ),
    "databricks.com": (
        ".case-study-cta",
        ".related-resources",
        ".video-module",
        ".author-card",
        ".newsletter-signup",
    ),
    "techpolicy.press": (
        ".newsletter-signup",
        ".event-meta",
        ".related-posts",
        ".audio-player",
        ".author-bio",
    ),
    "a16z.com": (
        ".signup-module",
        ".podcast-player",
        ".related-insights",
        ".video-embed",
        ".author-card",
    ),
    "ted.com": (
        ".talk-sidebar",
        ".related-talks",
        ".cta-banner",
        ".audio-player",
        ".transcript-nav",
    ),
    "aws.amazon.com": (
        ".feedback-section",
        ".related-links",
        ".video-module",
        ".cta-banner",
        ".sidebar-nav",
    ),
    "docs.anthropic.com": (
        ".severity-badge",
        ".table-of-contents",
        ".docs-feedback",
        ".related-links",
        ".related-bulletins",
        ".contact-security",
        ".callout-banner",
        ".breadcrumbs",
    ),
    "learn.microsoft.com": (
        ".next-steps",
        ".feedback-section",
        ".training-banner",
        ".related-content",
        ".metadata-panel",
    ),
    "docs.cohere.com": (
        ".table-of-contents",
        ".feedback-widget",
        ".related-links",
        ".changelog-banner",
        ".breadcrumbs",
    ),
    "docs.fireworks.ai": (
        ".channel-nav",
        ".version-banner",
        ".related-guides",
        ".edit-page-link",
        ".breadcrumbs",
    ),
    "developer.nvidia.com": (
        ".sidebar-nav",
        ".related-resources",
        ".video-module",
        ".cta-banner",
        ".toc",
    ),
    "vercel.com": (
        ".related-updates",
        ".newsletter-callout",
        ".timeline-nav",
        ".video-embed",
        ".author-card",
    ),
    "docs.langchain.com": (
        ".table-of-contents",
        ".pagination-nav",
        ".related-links",
        ".feedback-widget",
        ".theme-doc-breadcrumbs",
    ),
    "docs.llamaindex.ai": (
        ".table-of-contents",
        ".matrix-nav",
        ".related-guides",
        ".feedback-widget",
        ".breadcrumbs",
    ),
    "developer.atlassian.com": (
        ".left-nav",
        ".deprecation-banner",
        ".related-resources",
        ".feedback-prompt",
        ".page-actions",
    ),
    "supabase.com": (
        ".steps-nav",
        ".video-callout",
        ".related-guides",
        ".cta-panel",
        ".sidebar-toc",
    ),
    "openai.com": (
        ".pricing-sidebar",
        ".tier-card-grid",
        ".related-updates",
        ".contact-sales-banner",
        ".pricing-nav",
    ),
    "anthropic.com": (
        ".service-tier-sidebar",
        ".tier-comparison-grid",
        ".related-announcements",
        ".contact-sales-banner",
        ".page-nav",
    ),
    "platform.openai.com": (
        ".faq-nav",
        ".deprecation-callout",
        ".related-answers",
        ".feedback-widget",
        ".docs-sidebar",
    ),
    "trust.openai.com": (
        ".trust-sidebar",
        ".severity-banner",
        ".related-advisories",
        ".subscribe-panel",
        ".breadcrumbs",
    ),
    "docs.pinecone.io": (
        ".table-of-contents",
        ".checklist-nav",
        ".related-guides",
        ".feedback-widget",
        ".breadcrumbs",
    ),
    "docs.together.ai": (
        ".policy-sidebar",
        ".support-banner",
        ".related-articles",
        ".feedback-widget",
        ".sidebar-toc",
    ),
    "status.openai.com": (
        ".incident-sidebar",
        ".affected-components",
        ".status-banner",
        ".subscribe-pane",
        ".incident-timeline-nav",
    ),
    "status.pinecone.io": (
        ".postmortem-meta",
        ".related-incidents",
        ".status-banner",
        ".subscribe-pane",
        ".component-list",
    ),
    "status.together.ai": (
        ".impact-summary",
        ".related-incidents",
        ".status-banner",
        ".subscribe-pane",
        ".incident-nav",
    ),
    "together.ai": (
        ".sku-sidebar",
        ".plan-comparison-grid",
        ".related-updates",
        ".contact-sales-banner",
        ".page-nav",
    ),
    "docs.vllm.ai": (
        ".version-warning",
        ".related-pages",
        ".page-nav",
        ".edit-link",
        ".sidebar-toc",
    ),
    "theguardian.com": (
        ".submeta",
        ".email-sign-up",
        ".related-content",
        ".liveblog-block__meta",
        ".sharecount",
        ".most-viewed-container",
        ".liveblog__key-events",
    ),
    "substack.com": (
        ".subscription-widget-wrap",
        ".subscribe-widget",
        ".comments-page",
        ".footer-wrap",
        ".pencraft",
    ),
    "yahoo.com": (
        ".caas-share-section",
        ".caas-readmore",
        ".caas-3p-blocked",
        ".caas-da",
        ".video-player-element",
        ".caas-vertical-video",
    ),
}
HOST_NOISE_LINE_PATTERNS = {
    "36kr.com": (
        re.compile(r"^本文由.+原创"),
        re.compile(r"^题图来自"),
    ),
    "ithome.com": (
        re.compile(r"^广告声明"),
    ),
    "jiqizhixin.com": (
        re.compile(r"^机器之心(报道|编辑部).*$"),
        re.compile(r"^原标题[:：].*$"),
    ),
    "huggingface.co": (
        re.compile(r"^Back to Articles$"),
        re.compile(r"^Published$"),
        re.compile(r"^Update on GitHub$"),
        re.compile(r"^Upvote$"),
        re.compile(r"^\+\d+$"),
        re.compile(r"^Table of Contents(?: .+)?$"),
    ),
    "blog.google": (
        re.compile(r"^Listen to article$"),
        re.compile(r"^This content is generated by Google AI\. Generative AI is experimental$"),
        re.compile(r"^\[\[duration\]\] minutes$"),
        re.compile(r"^Voice$"),
        re.compile(r"^Speed$"),
        re.compile(r"^(0\.75X|1X|1\.5X|2X)$"),
    ),
    "deepmind.google": (
        re.compile(r"^Listen to article$"),
        re.compile(r"^This content is generated by Google AI\. Generative AI is experimental$"),
        re.compile(r"^\[\[duration\]\] minutes$"),
        re.compile(r"^Voice$"),
        re.compile(r"^Speed$"),
        re.compile(r"^(0\.75X|1X|1\.5X|2X)$"),
    ),
    "techcrunch.com": (
        re.compile(r"^Sign up for .+ newsletters?$"),
    ),
    "venturebeat.com": (
        re.compile(r"^Subscribe to VB Daily$"),
        re.compile(r"^Join the event that brings together.+$"),
    ),
    "wired.com": (
        re.compile(r"^Most Popular$"),
        re.compile(r"^Read More$"),
        re.compile(r"^You can support our work by subscribing\.$"),
    ),
    "reuters.com": (
        re.compile(r"^Our Standards: The Thomson Reuters Trust Principles$"),
        re.compile(r"^Reporting by .+$"),
    ),
    "arstechnica.com": (
        re.compile(r"^Ars Technica may earn compensation.*$"),
        re.compile(r"^Stay tuned for.*$"),
    ),
    "technologyreview.com": (
        re.compile(r"^Subscribe to The Algorithm$"),
        re.compile(r"^Stay connected with MIT Technology Review.*$"),
        re.compile(r"^More from MIT Technology Review$"),
    ),
    "axios.com": (
        re.compile(r"^Sign up for Axios AI\+$"),
        re.compile(r"^By signing up, you agree to receive.*$"),
        re.compile(r"^More from Axios$"),
    ),
    "apnews.com": (
        re.compile(r"^The Associated Press is an independent global news organization.*$"),
        re.compile(r"^Read more$"),
        re.compile(r"^More stories$"),
        re.compile(r"^\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.)\s*[A-Z]{2,4}$"),
    ),
    "bbc.com": (
        re.compile(r"^Live Reporting$"),
        re.compile(r"^Posted at \d{1,2}:\d{2}$"),
        re.compile(r"^\d{1,2}:\d{2}$"),
        re.compile(r"^Top stories$"),
    ),
    "cnbc.com": (
        re.compile(r"^Watch:.*$"),
        re.compile(r"^Subscribe to CNBC PRO$"),
        re.compile(r"^Related Tags$"),
    ),
    "ft.com": (
        re.compile(r"^Sign up to the FT Edit newsletter$"),
        re.compile(r"^Recommended$"),
        re.compile(r"^Read next$"),
    ),
    "semafor.com": (
        re.compile(r"^View in browser$"),
        re.compile(r"^Read the full signal$"),
        re.compile(r"^More from Semafor$"),
    ),
    "morningbrew.com": (
        re.compile(r"^Join millions of readers.*$"),
        re.compile(r"^Was this forwarded to you\?$"),
        re.compile(r"^Read more from Morning Brew$"),
    ),
    "theinformation.com": (
        re.compile(r"^Subscriber-only content$"),
        re.compile(r"^Read more from The Information$"),
        re.compile(r"^Already a subscriber\?$"),
    ),
    "engadget.com": (
        re.compile(r"^Listen to this article$"),
        re.compile(r"^Watch:.*$"),
        re.compile(r"^Recommended by Engadget$"),
    ),
    "forbes.com": (
        re.compile(r"^Listen to article$"),
        re.compile(r"^More From Forbes$"),
        re.compile(r"^Watch Forbes.*$"),
    ),
    "zdnet.com": (
        re.compile(r"^ZDNET Recommends$"),
        re.compile(r"^Watch now$"),
        re.compile(r"^Editor's note:.*$"),
    ),
    "newyorker.com": (
        re.compile(r"^More from The New Yorker$"),
        re.compile(r"^Listen to this story$"),
        re.compile(r"^Most Popular$"),
    ),
    "fortune.com": (
        re.compile(r"^Subscribe to Fortune.*$"),
        re.compile(r"^Most Popular$"),
        re.compile(r"^Read more from Fortune$"),
    ),
    "inc.com": (
        re.compile(r"^Inc\. Premium$"),
        re.compile(r"^Recommended Reading$"),
        re.compile(r"^Subscribe to the newsletter$"),
    ),
    "bloomberg.com": (
        re.compile(r"^Before it's here, it's on the Bloomberg Terminal\.$"),
        re.compile(r"^Read next$"),
        re.compile(r"^Sign up for the New Economy Daily$"),
    ),
    "wsj.com": (
        re.compile(r"^Listen to article$"),
        re.compile(r"^Continue reading your article with a WSJ subscription$"),
        re.compile(r"^Recommended Videos$"),
    ),
    "economist.com": (
        re.compile(r"^Subscribers only$"),
        re.compile(r"^Listen to this episode$"),
        re.compile(r"^Read more from this section$"),
    ),
    "cnn.com": (
        re.compile(r"^Watch this interactive$"),
        re.compile(r"^Read more from CNN$"),
        re.compile(r"^Sign up for our newsletter$"),
    ),
    "nytimes.com": (
        re.compile(r"^Listen to this article$"),
        re.compile(r"^More on A\.I\.$"),
        re.compile(r"^Advertisement$"),
    ),
    "washingtonpost.com": (
        re.compile(r"^Listen$"),
        re.compile(r"^Try 1 month for \$1$"),
        re.compile(r"^Read more from The Post$"),
    ),
    "vox.com": (
        re.compile(r"^Most Popular$"),
        re.compile(r"^Sign up for the newsletter$"),
        re.compile(r"^Read More Vox coverage$"),
    ),
    "time.com": (
        re.compile(r"^Listen to the story$"),
        re.compile(r"^What to read next$"),
        re.compile(r"^Subscribe to the Time newsletter$"),
    ),
    "nbcnews.com": (
        re.compile(r"^Watch more from NBC News$"),
        re.compile(r"^Sign up for our newsletters$"),
        re.compile(r"^Related coverage$"),
    ),
    "fastcompany.com": (
        re.compile(r"^Listen to the interview$"),
        re.compile(r"^Read more from Fast Company$"),
        re.compile(r"^Sign up for the newsletter$"),
    ),
    "businessinsider.com": (
        re.compile(r"^Read next$"),
        re.compile(r"^Get Business Insider intelligence in your inbox$"),
        re.compile(r"^Listen to the conversation$"),
    ),
    "spectrum.ieee.org": (
        re.compile(r"^Listen to this episode$"),
        re.compile(r"^More from IEEE Spectrum$"),
        re.compile(r"^Subscribe to our newsletters$"),
    ),
    "theatlantic.com": (
        re.compile(r"^Listen to the article$"),
        re.compile(r"^Read more from The Atlantic$"),
        re.compile(r"^Sign up for The Atlantic Daily$"),
    ),
    "foreignpolicy.com": (
        re.compile(r"^Subscribe to Foreign Policy$"),
        re.compile(r"^Read More$"),
        re.compile(r"^Listen to the conversation$"),
    ),
    "newstatesman.com": (
        re.compile(r"^Listen to this piece$"),
        re.compile(r"^Continue reading with a subscription$"),
        re.compile(r"^Recommended$"),
    ),
    "brookings.edu": (
        re.compile(r"^Sign up for Brookings newsletters$"),
        re.compile(r"^Related Content$"),
        re.compile(r"^Listen to this policy brief$"),
    ),
    "rand.org": (
        re.compile(r"^Listen to the article$"),
        re.compile(r"^Related RAND research$"),
        re.compile(r"^Get RAND insights in your inbox$"),
    ),
    "restofworld.org": (
        re.compile(r"^Listen to the story$"),
        re.compile(r"^Read more from Rest of World$"),
        re.compile(r"^Sign up for our weekly newsletter$"),
    ),
    "mckinsey.com": (
        re.compile(r"^Listen to the article$"),
        re.compile(r"^Explore more insights$"),
        re.compile(r"^Download the full report$"),
    ),
    "cloud.google.com": (
        re.compile(r"^Compliance update$"),
        re.compile(r"^Security bulletin menu$"),
        re.compile(r"^Benchmark methodology$"),
        re.compile(r"^Related products$"),
        re.compile(r"^Related cloud controls$"),
        re.compile(r"^Listen to this benchmark note$"),
    ),
    "databricks.com": (
        re.compile(r"^Watch the customer story$"),
        re.compile(r"^Read related resources$"),
        re.compile(r"^Sign up for Databricks updates$"),
    ),
    "techpolicy.press": (
        re.compile(r"^Event recap hub$"),
        re.compile(r"^Related posts$"),
        re.compile(r"^Listen to the session recap$"),
    ),
    "a16z.com": (
        re.compile(r"^Watch the full session$"),
        re.compile(r"^More from a16z$"),
        re.compile(r"^Subscribe for future updates$"),
    ),
    "ted.com": (
        re.compile(r"^Transcript navigation$"),
        re.compile(r"^More TED talks on AI$"),
        re.compile(r"^Listen to the episode$"),
    ),
    "aws.amazon.com": (
        re.compile(r"^Best practices checklist$"),
        re.compile(r"^Related AWS guidance$"),
        re.compile(r"^Watch the walkthrough$"),
    ),
    "docs.anthropic.com": (
        re.compile(r"^Security bulletin$"),
        re.compile(r"^Severity level$"),
        re.compile(r"^Troubleshooting menu$"),
        re.compile(r"^Related topics$"),
        re.compile(r"^Related bulletins$"),
        re.compile(r"^Contact security$"),
        re.compile(r"^Need more help\?$"),
    ),
    "learn.microsoft.com": (
        re.compile(r"^Additional resources$"),
        re.compile(r"^Feedback$"),
        re.compile(r"^Training available$"),
    ),
    "docs.cohere.com": (
        re.compile(r"^API reference menu$"),
        re.compile(r"^Related endpoints$"),
        re.compile(r"^Need help with integration\?$"),
    ),
    "docs.fireworks.ai": (
        re.compile(r"^Release channels$"),
        re.compile(r"^Related Fireworks guides$"),
        re.compile(r"^Edit this page$"),
    ),
    "developer.nvidia.com": (
        re.compile(r"^Performance checklist$"),
        re.compile(r"^Related NVIDIA guides$"),
        re.compile(r"^Watch the walkthrough$"),
    ),
    "vercel.com": (
        re.compile(r"^Read the changelog$"),
        re.compile(r"^Related updates$"),
        re.compile(r"^Watch the launch clip$"),
    ),
    "docs.langchain.com": (
        re.compile(r"^Migration guide menu$"),
        re.compile(r"^Related migration steps$"),
        re.compile(r"^Was this page helpful\?$"),
    ),
    "docs.llamaindex.ai": (
        re.compile(r"^Compatibility matrix$"),
        re.compile(r"^Related LlamaIndex docs$"),
        re.compile(r"^Was this page helpful\?$"),
    ),
    "developer.atlassian.com": (
        re.compile(r"^Deprecation timeline$"),
        re.compile(r"^Related Atlassian docs$"),
        re.compile(r"^Was this helpful\?$"),
    ),
    "supabase.com": (
        re.compile(r"^Watch the migration walkthrough$"),
        re.compile(r"^Related upgrade guides$"),
        re.compile(r"^Start building$"),
    ),
    "openai.com": (
        re.compile(r"^Pricing update navigation$"),
        re.compile(r"^Service tier grid$"),
        re.compile(r"^Related pricing updates$"),
        re.compile(r"^Talk to sales$"),
    ),
    "anthropic.com": (
        re.compile(r"^Service tier notice$"),
        re.compile(r"^Tier comparison$"),
        re.compile(r"^Related product announcements$"),
        re.compile(r"^Contact sales$"),
    ),
    "platform.openai.com": (
        re.compile(r"^Deprecation FAQ$"),
        re.compile(r"^Related answers$"),
        re.compile(r"^Was this helpful\?$"),
    ),
    "trust.openai.com": (
        re.compile(r"^Trust center advisory$"),
        re.compile(r"^Related advisories$"),
        re.compile(r"^Subscribe for trust updates$"),
        re.compile(r"^Severity: .*"),
    ),
    "docs.pinecone.io": (
        re.compile(r"^Migration checklist$"),
        re.compile(r"^Related Pinecone guides$"),
        re.compile(r"^Need more help\?$"),
    ),
    "docs.together.ai": (
        re.compile(r"^Support policy$"),
        re.compile(r"^Related Together docs$"),
        re.compile(r"^Need more help\?$"),
    ),
    "status.openai.com": (
        re.compile(r"^Affected components$"),
        re.compile(r"^Subscribe to updates$"),
        re.compile(r"^Status update banner$"),
        re.compile(r"^Incident timeline$"),
    ),
    "status.pinecone.io": (
        re.compile(r"^Postmortem metadata$"),
        re.compile(r"^Related incidents$"),
        re.compile(r"^Subscribe to incident updates$"),
        re.compile(r"^Affected services$"),
    ),
    "status.together.ai": (
        re.compile(r"^Impact summary$"),
        re.compile(r"^Related incidents$"),
        re.compile(r"^Subscribe to updates$"),
        re.compile(r"^Incident navigation$"),
    ),
    "together.ai": (
        re.compile(r"^SKU change overview$"),
        re.compile(r"^Plan comparison$"),
        re.compile(r"^Related product updates$"),
        re.compile(r"^Talk to sales$"),
    ),
    "docs.vllm.ai": (
        re.compile(r"^Version notice$"),
        re.compile(r"^Related versioned pages$"),
        re.compile(r"^Edit on GitHub$"),
    ),
    "theguardian.com": (
        re.compile(r"^Live feed$"),
        re.compile(r"^\d{1,2}\.\d{2}\s*(?:AM|PM)\s*[A-Z]{2,4}$"),
        re.compile(r"^Most viewed$"),
    ),
    "substack.com": (
        re.compile(r"^Thanks for reading.*$"),
        re.compile(r"^Subscribe (?:now|for free).*$"),
        re.compile(r"^Share this post$"),
        re.compile(r"^Leave a comment$"),
    ),
    "yahoo.com": (
        re.compile(r"^Recommended Stories$"),
        re.compile(r"^Advertisement$"),
        re.compile(r"^Read more:.*$"),
    ),
}
FALLBACK_HOST_RULES = {
    "36kr.com": (
        {"tags": {"div", "section"}, "class_tokens": {"common-width", "content", "articledetailcontent", "kr-rich-text-wrapper"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
    ),
    "ithome.com": (
        {"tags": {"div", "section"}, "id_tokens": {"paragraph"}},
        {"tags": {"div", "section"}, "class_tokens": {"news-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
    ),
    "tmtpost.com": (
        {"tags": {"article"}},
        {"tags": {"div", "section"}, "class_tokens": {"article__content"}},
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
    ),
    "jiqizhixin.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article__content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
    ),
    "huggingface.co": (
        {"tags": {"div"}, "class_tokens": {"blog-content", "prose"}},
        {"tags": {"div"}, "class_tokens": {"blog-content"}},
    ),
    "blog.google": (
        {"tags": {"div"}, "class_tokens": {"article-container__content"}},
        {"tags": {"div"}, "class_tokens": {"uni-content", "uni-blog-article-container", "article-container__content"}},
    ),
    "deepmind.google": (
        {"tags": {"div"}, "class_tokens": {"article-container__content"}},
        {"tags": {"div"}, "class_tokens": {"uni-content", "uni-blog-article-container", "article-container__content"}},
    ),
    "theverge.com": (
        {"tags": {"div"}, "class_tokens": {"duet--layout--entry-body"}},
        {"tags": {"div"}, "class_tokens": {"duet--article--article-body-component"}},
    ),
    "techcrunch.com": (
        {"tags": {"div", "section"}, "class_tokens": {"entry-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"wp-block-post-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
    ),
    "venturebeat.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"entry-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content__content-group"}},
    ),
    "wired.com": (
        {"tags": {"div", "section"}, "class_tokens": {"body__inner-container"}},
        {"tags": {"div", "section"}, "class_tokens": {"article__body"}},
        {"tags": {"div", "section"}, "class_tokens": {"contentbodywrapper"}},
    ),
    "reuters.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body__content__17yit"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body__content"}},
        {"tags": {"div", "section"}, "id_tokens": {"paragraph-0"}},
    ),
    "arstechnica.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
        {"tags": {"article"}},
    ),
    "technologyreview.com": (
        {"tags": {"div", "section"}, "class_tokens": {"content--body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body__content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "axios.com": (
        {"tags": {"div", "section"}, "class_tokens": {"gtm-story-text"}},
        {"tags": {"div", "section"}, "class_tokens": {"story-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "apnews.com": (
        {"tags": {"div", "section"}, "class_tokens": {"richtextstorybody"}},
        {"tags": {"div", "section"}, "class_tokens": {"richtextbody"}},
        {"tags": {"div", "section"}, "class_tokens": {"page-content"}},
    ),
    "bbc.com": (
        {"tags": {"div", "section"}, "class_tokens": {"qa-story-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"lx-stream-post-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"ssrcss-11r1m41-richtextcomponentwrapper"}},
    ),
    "cnbc.com": (
        {"tags": {"div", "section"}, "class_tokens": {"articlebody-articlebody"}},
        {"tags": {"div", "section"}, "class_tokens": {"group"}},
        {"tags": {"div", "section"}, "class_tokens": {"articlebodywrapper"}},
    ),
    "ft.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article__content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"n-content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "semafor.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"story-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "morningbrew.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "theinformation.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article__body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"paywall-layout__body"}},
    ),
    "engadget.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-text"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"body-text"}},
    ),
    "forbes.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"body-container"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
    ),
    "zdnet.com": (
        {"tags": {"div", "section"}, "class_tokens": {"storybody"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"c-shortcodecontent"}},
    ),
    "newyorker.com": (
        {"tags": {"div", "section"}, "class_tokens": {"body__inner-container"}},
        {"tags": {"div", "section"}, "class_tokens": {"article__body"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "fortune.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"paywall"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-wrapper"}},
    ),
    "inc.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"single-post-content"}},
    ),
    "bloomberg.com": (
        {"tags": {"div", "section"}, "class_tokens": {"body-copy-v2"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"paywall-content"}},
    ),
    "wsj.com": (
        {"tags": {"div", "section"}, "class_tokens": {"wsj-snippet-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"paywall"}},
    ),
    "economist.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article__body-text"}},
        {"tags": {"div", "section"}, "class_tokens": {"layout-article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-text"}},
    ),
    "cnn.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article__content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article__main"}},
        {"tags": {"div", "section"}, "class_tokens": {"wysiwyg"}},
    ),
    "nytimes.com": (
        {"tags": {"div", "section"}, "class_tokens": {"storybodycompanioncolumn"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"css-at9mc1"}},
    ),
    "washingtonpost.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"story-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body-content"}},
    ),
    "vox.com": (
        {"tags": {"div", "section"}, "class_tokens": {"duet--article--article-body-component"}},
        {"tags": {"div", "section"}, "class_tokens": {"c-entry-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "time.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body__content"}},
        {"tags": {"div", "section"}, "class_tokens": {"body-wrapper"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
    ),
    "nbcnews.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body__content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
    ),
    "fastcompany.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"prose"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "businessinsider.com": (
        {"tags": {"div", "section"}, "class_tokens": {"content-lock-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
    ),
    "spectrum.ieee.org": (
        {"tags": {"div", "section"}, "class_tokens": {"article-main__content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "theatlantic.com": (
        {"tags": {"div", "section"}, "class_tokens": {"articlebody"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"contentbody"}},
    ),
    "foreignpolicy.com": (
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"entry-content"}},
    ),
    "newstatesman.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article__body"}},
        {"tags": {"div", "section"}, "class_tokens": {"c-content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "brookings.edu": (
        {"tags": {"div", "section"}, "class_tokens": {"post-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article__content"}},
        {"tags": {"div", "section"}, "class_tokens": {"wysiwyg"}},
    ),
    "rand.org": (
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"rich-text"}},
    ),
    "restofworld.org": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"story-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "mckinsey.com": (
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"wysiwyg"}},
    ),
    "cloud.google.com": (
        {"tags": {"div", "section"}, "class_tokens": {"compliance-update"}},
        {"tags": {"div", "section"}, "class_tokens": {"devsite-article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"case-study-body"}},
    ),
    "databricks.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"resource-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "techpolicy.press": (
        {"tags": {"div", "section"}, "class_tokens": {"entry-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
    ),
    "a16z.com": (
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"entry-content"}},
    ),
    "ted.com": (
        {"tags": {"div", "section"}, "class_tokens": {"talk-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"transcript__body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "aws.amazon.com": (
        {"tags": {"div", "section"}, "class_tokens": {"awsdocs-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"doc-content"}},
    ),
    "docs.anthropic.com": (
        {"tags": {"div", "section"}, "class_tokens": {"security-bulletin"}},
        {"tags": {"div", "section"}, "class_tokens": {"theme-doc-markdown"}},
        {"tags": {"div", "section"}, "class_tokens": {"docs-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "learn.microsoft.com": (
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"main-content"}},
    ),
    "docs.cohere.com": (
        {"tags": {"div", "section"}, "class_tokens": {"theme-doc-markdown"}},
        {"tags": {"div", "section"}, "class_tokens": {"docs-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"reference-body"}},
    ),
    "docs.fireworks.ai": (
        {"tags": {"div", "section"}, "class_tokens": {"theme-doc-markdown"}},
        {"tags": {"div", "section"}, "class_tokens": {"docs-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"release-channel-note"}},
    ),
    "developer.nvidia.com": (
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"doc-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "vercel.com": (
        {"tags": {"div", "section"}, "class_tokens": {"prose"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "docs.langchain.com": (
        {"tags": {"div", "section"}, "class_tokens": {"theme-doc-markdown"}},
        {"tags": {"div", "section"}, "class_tokens": {"docs-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"migration-guide"}},
    ),
    "docs.llamaindex.ai": (
        {"tags": {"div", "section"}, "class_tokens": {"theme-doc-markdown"}},
        {"tags": {"div", "section"}, "class_tokens": {"docs-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"compatibility-matrix"}},
    ),
    "developer.atlassian.com": (
        {"tags": {"div", "section"}, "class_tokens": {"doc-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "supabase.com": (
        {"tags": {"div", "section"}, "class_tokens": {"prose"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"docs-content"}},
    ),
    "openai.com": (
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"prose"}},
    ),
    "anthropic.com": (
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"prose"}},
    ),
    "platform.openai.com": (
        {"tags": {"div", "section"}, "class_tokens": {"docs-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"prose"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "trust.openai.com": (
        {"tags": {"div", "section"}, "class_tokens": {"trust-center-advisory"}},
        {"tags": {"div", "section"}, "class_tokens": {"advisory-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
    ),
    "docs.pinecone.io": (
        {"tags": {"div", "section"}, "class_tokens": {"theme-doc-markdown"}},
        {"tags": {"div", "section"}, "class_tokens": {"docs-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"migration-checklist"}},
    ),
    "docs.together.ai": (
        {"tags": {"div", "section"}, "class_tokens": {"docs-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
    ),
    "status.openai.com": (
        {"tags": {"div", "section"}, "class_tokens": {"incident-updates-container"}},
        {"tags": {"div", "section"}, "class_tokens": {"update-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"incident-body"}},
    ),
    "status.pinecone.io": (
        {"tags": {"div", "section"}, "class_tokens": {"postmortem-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"incident-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"update-body"}},
    ),
    "status.together.ai": (
        {"tags": {"div", "section"}, "class_tokens": {"incident-detail"}},
        {"tags": {"div", "section"}, "class_tokens": {"rca-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"update-body"}},
    ),
    "together.ai": (
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"prose"}},
    ),
    "docs.vllm.ai": (
        {"tags": {"div", "section"}, "class_tokens": {"md-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"content-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"document"}},
    ),
    "theguardian.com": (
        {"tags": {"div", "section"}, "class_tokens": {"liveblog__body"}},
        {"tags": {"div", "section"}, "class_tokens": {"content__article-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body-commercial-selector"}},
    ),
    "substack.com": (
        {"tags": {"div", "section"}, "class_tokens": {"body", "markup"}},
        {"tags": {"div", "section"}, "class_tokens": {"available-content"}},
        {"tags": {"div", "section"}, "class_tokens": {"post-content"}},
    ),
    "yahoo.com": (
        {"tags": {"div", "section"}, "class_tokens": {"caas-body"}},
        {"tags": {"div", "section"}, "class_tokens": {"article-body"}},
        {"tags": {"div", "section"}, "id_tokens": {"articlebody"}},
    ),
}
TEXT_BLOCK_TAGS = {
    "article",
    "blockquote",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "li",
    "main",
    "ol",
    "p",
    "section",
    "ul",
}
MIN_EXTRACTED_TEXT_LENGTH = 140
GOOGLE_NEWS_SKIP_MESSAGE = "skipped aggregated Google News shell page; direct article URL required"
logger = logging.getLogger("ainews.content_extractor")


@dataclass
class ExtractedContent:
    text: str
    title: str = ""
    resolved_url: str = ""


class ExtractionSkippedError(ValueError):
    pass


class ExtractionBlockedError(ValueError):
    pass


class _FallbackContainerParser(HTMLParser):
    def __init__(self, rules: tuple[dict, ...], drop_tokens: tuple[str, ...]):
        super().__init__(convert_charrefs=True)
        self.rules = rules
        self.drop_tokens = drop_tokens
        self.stack: List[bool] = []
        self.buffer: List[str] = []
        self.captures: List[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): (value or "") for key, value in attrs}
        attrs_blob = " ".join([attrs_dict.get("id", ""), attrs_dict.get("class", "")]).lower()

        if not self.stack:
            if self._matches_target(tag, attrs_dict):
                self.stack = [False]
                self.buffer = []
            return

        parent_skip = self.stack[-1]
        should_skip = parent_skip or tag.lower() in DROP_TAGS
        if not should_skip:
            if any(hint in attrs_blob for hint in DROP_HINTS):
                should_skip = True
            elif any(token and token in attrs_blob for token in self.drop_tokens):
                should_skip = True

        self.stack.append(should_skip)
        if not should_skip and tag.lower() in TEXT_BLOCK_TAGS:
            self.buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return

        should_skip = self.stack.pop()
        if not should_skip and tag.lower() in TEXT_BLOCK_TAGS:
            self.buffer.append("\n")
        if not self.stack and self.buffer:
            self.captures.append("".join(self.buffer))
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.stack and not self.stack[-1]:
            self.buffer.append(data)

    def _matches_target(self, tag: str, attrs_dict: dict[str, str]) -> bool:
        tag_name = tag.lower()
        class_tokens = {
            token
            for token in attrs_dict.get("class", "").lower().split()
            if token
        }
        id_tokens = {
            token
            for token in attrs_dict.get("id", "").lower().split()
            if token
        }

        for rule in self.rules:
            if tag_name not in rule.get("tags", {tag_name}):
                continue
            rule_classes = rule.get("class_tokens", set())
            rule_ids = rule.get("id_tokens", set())
            if rule_classes and not rule_classes.issubset(class_tokens):
                continue
            if rule_ids and not rule_ids.issubset(id_tokens):
                continue
            return True
        return False


class _FallbackTextParser(HTMLParser):
    def __init__(self, drop_tokens: tuple[str, ...]):
        super().__init__(convert_charrefs=True)
        self.drop_tokens = drop_tokens
        self.stack: List[bool] = []
        self.buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): (value or "") for key, value in attrs}
        attrs_blob = " ".join([attrs_dict.get("id", ""), attrs_dict.get("class", "")]).lower()
        parent_skip = self.stack[-1] if self.stack else False
        local_skip = tag.lower() in DROP_TAGS or tag.lower() in {"head", "title", "meta", "link"}
        if not local_skip and attrs_blob:
            local_skip = any(hint in attrs_blob for hint in DROP_HINTS) or any(
                token and token in attrs_blob for token in self.drop_tokens
            )
        should_skip = parent_skip or local_skip
        self.stack.append(should_skip)
        if not should_skip and tag.lower() in TEXT_BLOCK_TAGS:
            self.buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        should_skip = self.stack.pop()
        if not should_skip and tag.lower() in TEXT_BLOCK_TAGS:
            self.buffer.append("\n")

    def handle_data(self, data: str) -> None:
        if self.stack and not self.stack[-1]:
            self.buffer.append(data)

    def text(self) -> str:
        return "".join(self.buffer)


class ArticleContentExtractor:
    def __init__(
        self,
        *,
        timeout: int,
        user_agent: str,
        text_limit: int = 12000,
        google_news_resolver: Optional[GoogleNewsURLResolver] = None,
    ):
        self.timeout = timeout
        self.user_agent = user_agent
        self.text_limit = text_limit
        self.google_news_resolver = google_news_resolver or GoogleNewsURLResolver(
            timeout=timeout,
            user_agent=user_agent,
        )

    def fetch_and_extract(self, url: str) -> ExtractedContent:
        fetch_url = url
        if is_google_news_url(url):
            try:
                fetch_url = self.google_news_resolver.resolve(url)
            except GoogleNewsResolutionError:
                logger.warning(
                    "google news resolution failed; falling back to wrapper extraction path",
                    extra={"event": "extract.google_news_resolution_failed", "url": url},
                )
        html = fetch_text(fetch_url, timeout=self.timeout, user_agent=self.user_agent)
        extracted = self.extract_from_html(html, url=fetch_url)
        extracted.resolved_url = fetch_url
        return extracted

    def extract_from_html(self, html: str, *, url: str = "") -> ExtractedContent:
        host = self._normalize_host(url)
        if self._should_skip_aggregate_shell(html, host):
            raise ExtractionSkippedError(GOOGLE_NEWS_SKIP_MESSAGE)
        if self._looks_like_access_challenge(html, host):
            raise ExtractionBlockedError("publisher blocked extraction with an anti-bot challenge")
        if BeautifulSoup is None:
            return self._fallback_extract_from_html(html, url=url)

        soup = BeautifulSoup(html, "html.parser")
        self._prune_soup(soup, host)

        title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "")
        candidates = list(self._candidate_nodes(soup, host))
        best_text = ""
        best_score = -1.0

        for node, bonus in candidates:
            text = self._node_text(node, host)
            score = self._score_node(node, text) + bonus
            if score > best_score:
                best_text = text
                best_score = score

        if not best_text:
            body = soup.body or soup
            best_text = self._node_text(body, host)

        best_text = self._trim(best_text)
        if len(best_text) < MIN_EXTRACTED_TEXT_LENGTH:
            raise ValueError("extracted article text is too short")

        return ExtractedContent(text=best_text, title=title)

    def _candidate_nodes(self, soup: Any, host: str) -> Iterable[Tuple[Any, float]]:
        seen: set[int] = set()

        for selector in self._host_values(host, HOST_SELECTORS):
            for node in soup.select(selector):
                marker = id(node)
                if marker in seen:
                    continue
                seen.add(marker)
                yield node, 2400.0

        selectors = [
            "article",
            "main",
            "[role='main']",
            ".article-content",
            ".article__content",
            ".entry-content",
            ".post-content",
            ".story-content",
            ".main-content",
            ".content-body",
            ".markdown-body",
        ]
        for selector in selectors:
            for node in soup.select(selector):
                marker = id(node)
                if marker in seen:
                    continue
                seen.add(marker)
                yield node, 800.0

        for node in soup.find_all(["div", "section"]):
            attrs = self._node_attrs_blob(node)
            if any(hint in attrs for hint in ARTICLE_HINTS):
                marker = id(node)
                if marker in seen:
                    continue
                seen.add(marker)
                yield node, 0.0

    def _trim(self, value: str) -> str:
        if len(value) <= self.text_limit:
            return value
        return value[: self.text_limit].rsplit(" ", 1)[0].strip()

    def _score_node(self, node: Any, text: str) -> float:
        if not text:
            return -1.0
        paragraph_count = len(node.find_all("p")) if hasattr(node, "find_all") else 0
        heading_count = len(node.find_all(["h2", "h3", "h4"])) if hasattr(node, "find_all") else 0
        link_text_length = 0
        if hasattr(node, "find_all"):
            link_text_length = sum(
                len(clean_text(link.get_text(" ", strip=True))) for link in node.find_all("a")
            )
        line_count = len([line for line in text.splitlines() if line.strip()])
        noise_hits = sum(1 for phrase in NOISE_PHRASES if phrase in text)
        return (
            len(text)
            + paragraph_count * 320
            + heading_count * 120
            + line_count * 16
            - link_text_length * 0.65
            - noise_hits * 420
        )

    def _node_text(self, node: Any, host: str) -> str:
        fragment = BeautifulSoup(str(node), "html.parser")
        root = fragment.find() or fragment
        self._prune_soup(root, host)

        return self._normalize_extracted_text(root.get_text("\n", strip=True), host)

    def _prune_soup(self, soup: Any, host: str) -> None:
        for tag in list(soup.find_all(DROP_TAGS)):
            tag.decompose()
        for selector in self._host_values(host, HOST_DROP_SELECTORS):
            for node in list(soup.select(selector)):
                node.decompose()
        for node in list(soup.find_all(True)):
            attrs = self._node_attrs_blob(node)
            if attrs and any(hint in attrs for hint in DROP_HINTS):
                node.decompose()

    @staticmethod
    def _node_attrs_blob(node: Any) -> str:
        attrs = getattr(node, "attrs", None) or {}
        classes = attrs.get("class") or []
        if isinstance(classes, str):
            class_text = classes
        else:
            class_text = " ".join(str(item) for item in classes if item)
        identifier = attrs.get("id") or ""
        return f"{class_text} {identifier}".lower().strip()

    def _is_noise_line(self, line: str, host: str) -> bool:
        if len(line) <= 1:
            return True
        if line.count("http://") + line.count("https://") > 1:
            return True
        if any(pattern.search(line) for pattern in NOISE_LINE_PATTERNS):
            return True
        if any(pattern.search(line) for pattern in self._host_values(host, HOST_NOISE_LINE_PATTERNS)):
            return True
        return any(phrase in line for phrase in NOISE_PHRASES)

    @staticmethod
    def _normalize_host(url: str) -> str:
        if not url:
            return ""
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc

    @staticmethod
    def _host_matches(host: str, candidate: str) -> bool:
        return bool(host) and (host == candidate or host.endswith(f".{candidate}"))

    def _host_values(self, host: str, mapping: dict[str, tuple]) -> tuple:
        matches: List[object] = []
        for candidate, values in mapping.items():
            if self._host_matches(host, candidate):
                matches.extend(values)
        return tuple(matches)

    def _normalize_extracted_text(self, raw_text: str, host: str) -> str:
        lines: List[str] = []
        for raw_line in raw_text.splitlines():
            line = clean_text(raw_line)
            if not line:
                continue
            if self._is_noise_line(line, host):
                continue
            if lines and line == lines[-1]:
                continue
            lines.append(line)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

    def _host_fallback_rules(self, host: str) -> tuple[dict, ...]:
        matches: List[dict] = []
        for candidate, values in FALLBACK_HOST_RULES.items():
            if self._host_matches(host, candidate):
                matches.extend(values)
        return tuple(matches)

    def _host_drop_tokens(self, host: str) -> tuple[str, ...]:
        tokens: List[str] = []
        for selector in self._host_values(host, HOST_DROP_SELECTORS):
            selector_text = str(selector).lower().strip()
            tail = re.split(r"\s*[>+~]\s*|\s+", selector_text)[-1]
            cleaned = re.sub(r"[^a-z0-9_-]+", " ", tail).split()
            tokens.extend(cleaned)
        return tuple(tokens)

    def _fallback_extract_from_html(self, raw_html: str, *, url: str = "") -> ExtractedContent:
        host = self._normalize_host(url)
        if self._should_skip_aggregate_shell(raw_html, host):
            raise ExtractionSkippedError(GOOGLE_NEWS_SKIP_MESSAGE)
        if self._looks_like_access_challenge(raw_html, host):
            raise ExtractionBlockedError("publisher blocked extraction with an anti-bot challenge")
        title_match = TITLE_RE.search(raw_html)
        title = clean_text(html.unescape(title_match.group(1))) if title_match else ""

        rules = self._host_fallback_rules(host)
        if rules:
            parser = _FallbackContainerParser(rules, self._host_drop_tokens(host))
            parser.feed(raw_html)
            parser.close()
            candidates = [
                self._normalize_extracted_text(html.unescape(candidate), host)
                for candidate in parser.captures
            ]
            best_text = max(candidates, key=len, default="")
            best_text = self._trim(best_text)
            if len(best_text) >= MIN_EXTRACTED_TEXT_LENGTH:
                return ExtractedContent(text=best_text, title=title)

        parser = _FallbackTextParser(self._host_drop_tokens(host))
        parser.feed(raw_html)
        parser.close()
        text = self._normalize_extracted_text(html.unescape(parser.text()), host)
        text = self._trim(text)
        if len(text) < MIN_EXTRACTED_TEXT_LENGTH:
            raise ValueError("extracted article text is too short")
        return ExtractedContent(text=text, title=title)

    @staticmethod
    def _should_skip_aggregate_shell(raw_html: str, host: str) -> bool:
        if host != "news.google.com":
            return False
        lowered = raw_html.lower()
        return "<title>google news</title>" in lowered or "dotssplashui" in lowered

    @staticmethod
    def _looks_like_access_challenge(raw_html: str, host: str) -> bool:
        if not raw_html:
            return False
        lowered = raw_html.lower()
        challenge_markers = (
            "captcha",
            "verify you are human",
            "security check",
            "access denied",
            "cf-browser-verification",
            "enable javascript and cookies",
            "pardon the interruption",
            "attention required",
            "bot verification",
        )
        if any(marker in lowered for marker in challenge_markers):
            return True
        if host == "venturebeat.com" and "challenge-platform" in lowered:
            return True
        return False
