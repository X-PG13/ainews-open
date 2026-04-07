from __future__ import annotations

import argparse
import json
import sys

from .config import load_settings
from .service import NewsService


def _json_dump(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI news aggregation toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_persist_flags(target_parser: argparse.ArgumentParser, *, default: bool) -> None:
        target_parser.set_defaults(persist=default)
        target_parser.add_argument(
            "--persist",
            dest="persist",
            action="store_true",
            help="Store generated digests in SQLite",
        )
        target_parser.add_argument(
            "--no-persist",
            dest="persist",
            action="store_false",
            help="Do not store generated digests in SQLite",
        )

    ingest_parser = subparsers.add_parser("ingest", help="Fetch and store the latest news")
    ingest_parser.add_argument(
        "--source", action="append", dest="sources", help="Ingest only selected source ids"
    )
    ingest_parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Cap the number of entries pulled per source",
    )

    subparsers.add_parser("list-sources", help="Print all configured source definitions")

    digest_parser = subparsers.add_parser("print-digest", help="Print the latest digest as JSON")
    digest_parser.add_argument(
        "--region", default="all", choices=["all", "domestic", "international"]
    )
    digest_parser.add_argument("--since-hours", type=int, default=None)
    digest_parser.add_argument("--limit", type=int, default=30)
    digest_parser.add_argument("--use-llm", action="store_true")
    add_persist_flags(digest_parser, default=False)

    enrich_parser = subparsers.add_parser(
        "enrich",
        help="Translate and summarize international articles into Chinese with the configured LLM",
    )
    enrich_parser.add_argument("--source", action="append", dest="sources")
    enrich_parser.add_argument("--article-id", action="append", dest="article_ids", type=int)
    enrich_parser.add_argument("--since-hours", type=int, default=None)
    enrich_parser.add_argument("--limit", type=int, default=20)
    enrich_parser.add_argument("--force", action="store_true")

    extract_parser = subparsers.add_parser(
        "extract",
        help="Fetch full article text for stored articles",
    )
    extract_parser.add_argument("--source", action="append", dest="sources")
    extract_parser.add_argument("--article-id", action="append", dest="article_ids", type=int)
    extract_parser.add_argument("--since-hours", type=int, default=None)
    extract_parser.add_argument("--limit", type=int, default=20)
    extract_parser.add_argument("--force", action="store_true")

    digests_parser = subparsers.add_parser("list-digests", help="Print stored digests")
    digests_parser.add_argument(
        "--region", default="all", choices=["all", "domestic", "international"]
    )
    digests_parser.add_argument("--limit", type=int, default=20)

    publications_parser = subparsers.add_parser(
        "list-publications", help="Print stored publication records"
    )
    publications_parser.add_argument("--digest-id", type=int, default=None)
    publications_parser.add_argument("--target", default=None)
    publications_parser.add_argument("--status", default=None)
    publications_parser.add_argument("--limit", type=int, default=20)

    refresh_publications_parser = subparsers.add_parser(
        "refresh-publications",
        help="Refresh publish status for supported targets such as WeChat freepublish",
    )
    refresh_publications_parser.add_argument(
        "--publication-id", action="append", dest="publication_ids", type=int
    )
    refresh_publications_parser.add_argument("--digest-id", type=int, default=None)
    refresh_publications_parser.add_argument("--target", default=None)
    refresh_publications_parser.add_argument("--limit", type=int, default=20)
    refresh_publications_parser.add_argument("--all-status", action="store_true")

    pipeline_parser = subparsers.add_parser(
        "run-pipeline",
        help="Run ingest, extraction, enrichment, and digest generation in one command",
    )
    pipeline_parser.add_argument(
        "--region", default="all", choices=["all", "domestic", "international"]
    )
    pipeline_parser.add_argument("--since-hours", type=int, default=None)
    pipeline_parser.add_argument("--limit", type=int, default=30)
    pipeline_parser.add_argument("--max-items", type=int, default=None)
    pipeline_parser.add_argument("--use-llm", action="store_true")
    add_persist_flags(pipeline_parser, default=True)
    pipeline_parser.add_argument("--export", action="store_true")
    pipeline_parser.add_argument("--publish", action="store_true")
    pipeline_parser.add_argument("--target", action="append", dest="targets")
    pipeline_parser.add_argument("--wechat-submit", action="store_true")
    pipeline_parser.add_argument("--force-republish", action="store_true")

    publish_parser = subparsers.add_parser(
        "publish",
        help="Publish a digest to Telegram, Feishu, WeChat draft, or a static site",
    )
    publish_parser.add_argument("--digest-id", type=int, default=None)
    publish_parser.add_argument(
        "--region", default="all", choices=["all", "domestic", "international"]
    )
    publish_parser.add_argument("--since-hours", type=int, default=None)
    publish_parser.add_argument("--limit", type=int, default=30)
    publish_parser.add_argument("--use-llm", action="store_true")
    add_persist_flags(publish_parser, default=True)
    publish_parser.add_argument("--export", action="store_true")
    publish_parser.add_argument("--target", action="append", dest="targets")
    publish_parser.add_argument("--wechat-submit", action="store_true")
    publish_parser.add_argument("--force-republish", action="store_true")

    subparsers.add_parser("stats", help="Print article and digest statistics")

    serve_parser = subparsers.add_parser("serve", help="Run the HTTP API with uvicorn")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    settings = load_settings()
    service = NewsService(settings)

    if args.command == "ingest":
        _json_dump(
            service.ingest(
                source_ids=args.sources,
                max_items_per_source=args.max_items,
            )
        )
        return 0

    if args.command == "list-sources":
        _json_dump({"sources": service.list_sources()})
        return 0

    if args.command == "print-digest":
        _json_dump(
            service.build_digest(
                region=args.region,
                since_hours=args.since_hours,
                limit=args.limit,
                use_llm=args.use_llm,
                persist=args.persist,
            )
        )
        return 0

    if args.command == "enrich":
        _json_dump(
            service.enrich_articles(
                source_ids=args.sources,
                article_ids=args.article_ids,
                since_hours=args.since_hours,
                limit=args.limit,
                force=args.force,
            )
        )
        return 0

    if args.command == "extract":
        _json_dump(
            service.extract_articles(
                source_ids=args.sources,
                article_ids=args.article_ids,
                since_hours=args.since_hours,
                limit=args.limit,
                force=args.force,
            )
        )
        return 0

    if args.command == "list-digests":
        _json_dump(
            {
                "digests": service.list_digests(
                    region=args.region,
                    limit=args.limit,
                )
            }
        )
        return 0

    if args.command == "list-publications":
        _json_dump(
            {
                "publications": service.list_publications(
                    digest_id=args.digest_id,
                    target=args.target,
                    status=args.status,
                    limit=args.limit,
                )
            }
        )
        return 0

    if args.command == "refresh-publications":
        _json_dump(
            service.refresh_publications(
                publication_ids=args.publication_ids,
                digest_id=args.digest_id,
                target=args.target,
                limit=args.limit,
                only_pending=not args.all_status,
            )
        )
        return 0

    if args.command == "run-pipeline":
        _json_dump(
            service.run_pipeline(
                region=args.region,
                since_hours=args.since_hours,
                limit=args.limit,
                max_items_per_source=args.max_items,
                use_llm=args.use_llm,
                persist=args.persist,
                export=args.export,
                publish=args.publish,
                publish_targets=args.targets,
                wechat_submit=args.wechat_submit,
                force_republish=args.force_republish,
            )
        )
        return 0

    if args.command == "publish":
        _json_dump(
            service.publish_digest(
                digest_id=args.digest_id,
                region=args.region,
                since_hours=args.since_hours,
                limit=args.limit,
                use_llm=args.use_llm,
                persist=args.persist,
                export=args.export,
                targets=args.targets,
                wechat_submit=args.wechat_submit,
                force_republish=args.force_republish,
            )
        )
        return 0

    if args.command == "stats":
        _json_dump(service.get_stats())
        return 0

    if args.command == "serve":
        try:
            import uvicorn
        except ImportError:
            print("uvicorn is not installed. Run `pip install .` first.", file=sys.stderr)
            return 1

        uvicorn.run(
            "ainews.api:create_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=False,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
