from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .models import ArticleEnrichment, ArticleRecord, DailyDigest
from .utils import (
    canonicalize_url,
    clean_text,
    make_content_fingerprint,
    make_resolved_target,
    normalize_title,
    url_host,
    utc_now,
)

ARTICLE_EXTRA_COLUMNS = {
    "normalized_title": "TEXT NOT NULL DEFAULT ''",
    "resolved_target": "TEXT NOT NULL DEFAULT ''",
    "content_fingerprint": "TEXT NOT NULL DEFAULT ''",
    "duplicate_group": "TEXT NOT NULL DEFAULT ''",
    "duplicate_of": "INTEGER",
    "duplicate_reason": "TEXT NOT NULL DEFAULT ''",
    "extracted_text": "TEXT NOT NULL DEFAULT ''",
    "extraction_status": "TEXT NOT NULL DEFAULT 'pending'",
    "extraction_error": "TEXT NOT NULL DEFAULT ''",
    "extraction_updated_at": "TEXT NOT NULL DEFAULT ''",
    "extraction_attempts": "INTEGER NOT NULL DEFAULT 0",
    "extraction_last_http_status": "INTEGER NOT NULL DEFAULT 0",
    "extraction_next_retry_at": "TEXT NOT NULL DEFAULT ''",
    "extraction_error_category": "TEXT NOT NULL DEFAULT ''",
    "llm_title_zh": "TEXT NOT NULL DEFAULT ''",
    "llm_summary_zh": "TEXT NOT NULL DEFAULT ''",
    "llm_brief_zh": "TEXT NOT NULL DEFAULT ''",
    "llm_status": "TEXT NOT NULL DEFAULT 'pending'",
    "llm_provider": "TEXT NOT NULL DEFAULT ''",
    "llm_model": "TEXT NOT NULL DEFAULT ''",
    "llm_error": "TEXT NOT NULL DEFAULT ''",
    "llm_updated_at": "TEXT NOT NULL DEFAULT ''",
    "is_hidden": "INTEGER NOT NULL DEFAULT 0",
    "is_pinned": "INTEGER NOT NULL DEFAULT 0",
    "is_suppressed": "INTEGER NOT NULL DEFAULT 0",
    "must_include": "INTEGER NOT NULL DEFAULT 0",
    "editorial_note": "TEXT NOT NULL DEFAULT ''"
}

PUBLICATION_EXTRA_COLUMNS = {
    "updated_at": "TEXT NOT NULL DEFAULT ''",
}

CURRENT_SCHEMA_VERSION = 12

ARTICLE_SELECT_COLUMNS = """
    articles.id,
    articles.source_id,
    articles.source_name,
    articles.title,
    articles.url,
    articles.canonical_url,
    articles.summary,
    articles.published_at,
    articles.discovered_at,
    articles.language,
    articles.region,
    articles.country,
    articles.topic,
    articles.normalized_title,
    articles.resolved_target,
    articles.content_fingerprint,
    articles.extracted_text,
    articles.extraction_status,
    articles.extraction_error,
    articles.extraction_updated_at,
    articles.extraction_attempts,
    articles.extraction_last_http_status,
    articles.extraction_next_retry_at,
    articles.extraction_error_category,
    articles.llm_title_zh,
    articles.llm_summary_zh,
    articles.llm_brief_zh,
    articles.llm_status,
    articles.llm_provider,
    articles.llm_model,
    articles.llm_error,
    articles.llm_updated_at,
    articles.is_hidden,
    articles.is_pinned,
    articles.is_suppressed,
    articles.must_include,
    articles.editorial_note,
    articles.duplicate_group,
    articles.duplicate_of,
    articles.duplicate_reason,
    COALESCE(group_stats.total_in_group, 1) AS duplicate_count,
    CASE WHEN articles.duplicate_of IS NULL THEN 1 ELSE 0 END AS is_duplicate_primary,
    COALESCE(primary_article.id, articles.id) AS duplicate_primary_id,
    COALESCE(primary_article.title, articles.title) AS duplicate_primary_title,
    COALESCE(primary_article.source_name, articles.source_name) AS duplicate_primary_source_name
"""

ARTICLE_SELECT_JOINS = """
    LEFT JOIN (
        SELECT duplicate_group, COUNT(*) AS total_in_group
        FROM articles
        WHERE duplicate_group != ''
        GROUP BY duplicate_group
    ) AS group_stats
        ON group_stats.duplicate_group = articles.duplicate_group
    LEFT JOIN articles AS primary_article
        ON primary_article.id = COALESCE(articles.duplicate_of, articles.id)
"""

SYNDICATION_HOSTS = {
    "news.google.com",
    "news.googleusercontent.com",
    "news.yahoo.com",
    "www.yahoo.com",
    "finance.yahoo.com",
    "www.msn.com",
}

SOURCE_STATE_EXTRA_COLUMNS = {
    "consecutive_successes": "INTEGER NOT NULL DEFAULT 0",
    "last_recovered_at": "TEXT NOT NULL DEFAULT ''",
    "silenced_until": "TEXT NOT NULL DEFAULT ''",
    "maintenance_mode": "INTEGER NOT NULL DEFAULT 0",
    "acknowledged_at": "TEXT NOT NULL DEFAULT ''",
    "ack_note": "TEXT NOT NULL DEFAULT ''",
}


class ArticleRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    discovered_at TEXT NOT NULL,
                    language TEXT NOT NULL,
                    region TEXT NOT NULL,
                    country TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    dedup_key TEXT NOT NULL,
                    normalized_title TEXT NOT NULL DEFAULT '',
                    resolved_target TEXT NOT NULL DEFAULT '',
                    content_fingerprint TEXT NOT NULL DEFAULT '',
                    duplicate_group TEXT NOT NULL DEFAULT '',
                    duplicate_of INTEGER,
                    duplicate_reason TEXT NOT NULL DEFAULT '',
                    raw_payload TEXT NOT NULL,
                    extracted_text TEXT NOT NULL DEFAULT '',
                    extraction_status TEXT NOT NULL DEFAULT 'pending',
                    extraction_error TEXT NOT NULL DEFAULT '',
                    extraction_updated_at TEXT NOT NULL DEFAULT '',
                    extraction_attempts INTEGER NOT NULL DEFAULT 0,
                    extraction_last_http_status INTEGER NOT NULL DEFAULT 0,
                    extraction_next_retry_at TEXT NOT NULL DEFAULT '',
                    extraction_error_category TEXT NOT NULL DEFAULT '',
                    llm_title_zh TEXT NOT NULL DEFAULT '',
                    llm_summary_zh TEXT NOT NULL DEFAULT '',
                    llm_brief_zh TEXT NOT NULL DEFAULT '',
                    llm_status TEXT NOT NULL DEFAULT 'pending',
                    llm_provider TEXT NOT NULL DEFAULT '',
                    llm_model TEXT NOT NULL DEFAULT '',
                    llm_error TEXT NOT NULL DEFAULT '',
                    llm_updated_at TEXT NOT NULL DEFAULT '',
                    is_hidden INTEGER NOT NULL DEFAULT 0,
                    is_pinned INTEGER NOT NULL DEFAULT 0,
                    is_suppressed INTEGER NOT NULL DEFAULT 0,
                    must_include INTEGER NOT NULL DEFAULT 0,
                    editorial_note TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS digests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    region TEXT NOT NULL,
                    since_hours INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    body_markdown TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    article_count INTEGER NOT NULL,
                    source_count INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    digest_id INTEGER,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS source_states (
                    source_id TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL DEFAULT '',
                    cooldown_status TEXT NOT NULL DEFAULT '',
                    cooldown_until TEXT NOT NULL DEFAULT '',
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    consecutive_successes INTEGER NOT NULL DEFAULT 0,
                    last_error_category TEXT NOT NULL DEFAULT '',
                    last_http_status INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    last_error_at TEXT NOT NULL DEFAULT '',
                    last_success_at TEXT NOT NULL DEFAULT '',
                    last_recovered_at TEXT NOT NULL DEFAULT '',
                    silenced_until TEXT NOT NULL DEFAULT '',
                    maintenance_mode INTEGER NOT NULL DEFAULT 0,
                    acknowledged_at TEXT NOT NULL DEFAULT '',
                    ack_note TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS source_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_category TEXT NOT NULL DEFAULT '',
                    http_status INTEGER NOT NULL DEFAULT 0,
                    article_id INTEGER,
                    article_title TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_events_archive (
                    id INTEGER PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_category TEXT NOT NULL DEFAULT '',
                    http_status INTEGER NOT NULL DEFAULT 0,
                    article_id INTEGER,
                    article_title TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    archived_at TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS alert_states (
                    alert_key TEXT PRIMARY KEY,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    fingerprint TEXT NOT NULL DEFAULT '',
                    last_status TEXT NOT NULL DEFAULT '',
                    last_title TEXT NOT NULL DEFAULT '',
                    last_message TEXT NOT NULL DEFAULT '',
                    last_sent_at TEXT NOT NULL DEFAULT '',
                    last_recovered_at TEXT NOT NULL DEFAULT '',
                    delivery_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS source_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL DEFAULT '',
                    alert_key TEXT NOT NULL,
                    alert_status TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL DEFAULT '',
                    fingerprint TEXT NOT NULL DEFAULT '',
                    targets TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_alerts_archive (
                    id INTEGER PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL DEFAULT '',
                    alert_key TEXT NOT NULL,
                    alert_status TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL DEFAULT '',
                    fingerprint TEXT NOT NULL DEFAULT '',
                    targets TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    archived_at TEXT NOT NULL DEFAULT ''
                );
                """
            )
            self._ensure_article_migrations(connection)
            self._ensure_publication_migrations(connection)
            self._ensure_source_state_migrations(connection)
            connection.executescript(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_canonical_url
                    ON articles(canonical_url);

                CREATE INDEX IF NOT EXISTS idx_articles_published_at
                    ON articles(published_at);

                CREATE INDEX IF NOT EXISTS idx_articles_region_published_at
                    ON articles(region, published_at);

                CREATE INDEX IF NOT EXISTS idx_articles_content_hash
                    ON articles(content_hash);

                CREATE INDEX IF NOT EXISTS idx_articles_dedup_key
                    ON articles(dedup_key);

                CREATE INDEX IF NOT EXISTS idx_articles_normalized_title
                    ON articles(normalized_title);

                CREATE INDEX IF NOT EXISTS idx_articles_resolved_target
                    ON articles(resolved_target);

                CREATE INDEX IF NOT EXISTS idx_articles_content_fingerprint
                    ON articles(content_fingerprint);

                CREATE INDEX IF NOT EXISTS idx_articles_duplicate_group
                    ON articles(duplicate_group);

                CREATE INDEX IF NOT EXISTS idx_articles_duplicate_of
                    ON articles(duplicate_of);

                CREATE INDEX IF NOT EXISTS idx_articles_pinned_published_at
                    ON articles(is_pinned, must_include, published_at);

                CREATE INDEX IF NOT EXISTS idx_articles_llm_status
                    ON articles(llm_status);

                CREATE INDEX IF NOT EXISTS idx_articles_extraction_status
                    ON articles(extraction_status);

                CREATE INDEX IF NOT EXISTS idx_digests_generated_at
                    ON digests(generated_at);

                CREATE INDEX IF NOT EXISTS idx_digests_region_generated_at
                    ON digests(region, generated_at);

                CREATE INDEX IF NOT EXISTS idx_publications_created_at
                    ON publications(created_at);

                CREATE INDEX IF NOT EXISTS idx_publications_digest_target
                    ON publications(digest_id, target, created_at);

                CREATE INDEX IF NOT EXISTS idx_source_states_cooldown_until
                    ON source_states(cooldown_until);

                CREATE INDEX IF NOT EXISTS idx_source_states_cooldown_status
                    ON source_states(cooldown_status);

                CREATE INDEX IF NOT EXISTS idx_source_states_silenced_until
                    ON source_states(silenced_until);

                CREATE INDEX IF NOT EXISTS idx_source_states_maintenance_mode
                    ON source_states(maintenance_mode);

                CREATE INDEX IF NOT EXISTS idx_source_events_source_created_at
                    ON source_events(source_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_source_events_status_created_at
                    ON source_events(status, created_at);

                CREATE INDEX IF NOT EXISTS idx_source_events_archive_source_created_at
                    ON source_events_archive(source_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_source_alerts_source_created_at
                    ON source_alerts(source_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_source_alerts_status_created_at
                    ON source_alerts(alert_status, created_at);

                CREATE INDEX IF NOT EXISTS idx_source_alerts_alert_key_created_at
                    ON source_alerts(alert_key, created_at);

                CREATE INDEX IF NOT EXISTS idx_source_alerts_archive_source_created_at
                    ON source_alerts_archive(source_id, created_at);
                """
            )
            self._set_meta(connection, "schema_version", str(CURRENT_SCHEMA_VERSION))

    def _ensure_article_migrations(self, connection: sqlite3.Connection) -> None:
        existing_columns = self._table_columns(connection, "articles")
        for column_name, column_type in ARTICLE_EXTRA_COLUMNS.items():
            if column_name in existing_columns:
                continue
            try:
                connection.execute(
                    f"ALTER TABLE articles ADD COLUMN {column_name} {column_type}"
                )
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        self._backfill_article_metadata(connection)

    def _ensure_publication_migrations(self, connection: sqlite3.Connection) -> None:
        existing_columns = self._table_columns(connection, "publications")
        for column_name, column_type in PUBLICATION_EXTRA_COLUMNS.items():
            if column_name in existing_columns:
                continue
            try:
                connection.execute(
                    f"ALTER TABLE publications ADD COLUMN {column_name} {column_type}"
                )
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

    def _ensure_source_state_migrations(self, connection: sqlite3.Connection) -> None:
        existing_columns = self._table_columns(connection, "source_states")
        for column_name, column_type in SOURCE_STATE_EXTRA_COLUMNS.items():
            if column_name in existing_columns:
                continue
            try:
                connection.execute(
                    f"ALTER TABLE source_states ADD COLUMN {column_name} {column_type}"
                )
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

    @staticmethod
    def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}

    @staticmethod
    def _set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            """
            INSERT INTO meta(key, value)
            VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def _backfill_article_metadata(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT
                id,
                title,
                url,
                canonical_url,
                summary,
                extracted_text,
                normalized_title,
                resolved_target,
                content_fingerprint,
                duplicate_group,
                duplicate_of
            FROM articles
            """
        ).fetchall()
        for row in rows:
            normalized_title = clean_text(str(row["normalized_title"] or "")) or normalize_title(
                str(row["title"] or "")
            )
            resolved_target = clean_text(str(row["resolved_target"] or "")) or make_resolved_target(
                str(row["url"] or ""),
                str(row["canonical_url"] or ""),
            )
            content_fingerprint = clean_text(
                str(row["content_fingerprint"] or "")
            ) or make_content_fingerprint(
                str(row["title"] or ""),
                str(row["summary"] or ""),
                str(row["extracted_text"] or ""),
            )
            duplicate_group = clean_text(str(row["duplicate_group"] or ""))
            duplicate_of = row["duplicate_of"]
            if not duplicate_group:
                primary_id = int(duplicate_of) if duplicate_of is not None else int(row["id"])
                duplicate_group = self._duplicate_group_id(primary_id)
            connection.execute(
                """
                UPDATE articles
                SET
                    normalized_title = ?,
                    resolved_target = ?,
                    content_fingerprint = ?,
                    duplicate_group = ?
                WHERE id = ?
                """,
                (
                    normalized_title,
                    resolved_target,
                    content_fingerprint,
                    duplicate_group,
                    int(row["id"]),
                ),
            )

    @staticmethod
    def _row_to_article_dict(row: sqlite3.Row) -> Dict[str, object]:
        payload = dict(row)
        payload["is_hidden"] = bool(payload.get("is_hidden"))
        payload["is_pinned"] = bool(payload.get("is_pinned"))
        payload["is_suppressed"] = bool(payload.get("is_suppressed"))
        payload["must_include"] = bool(payload.get("must_include"))
        payload["extraction_attempts"] = int(payload.get("extraction_attempts") or 0)
        payload["extraction_last_http_status"] = int(payload.get("extraction_last_http_status") or 0)
        payload["duplicate_count"] = int(payload.get("duplicate_count") or 1)
        payload["duplicate_of"] = (
            int(payload["duplicate_of"]) if payload.get("duplicate_of") is not None else None
        )
        payload["duplicate_primary_id"] = int(payload.get("duplicate_primary_id") or payload["id"])
        payload["is_duplicate_primary"] = bool(payload.get("is_duplicate_primary"))
        return payload

    @staticmethod
    def _row_to_source_state_dict(row: sqlite3.Row) -> Dict[str, object]:
        payload = dict(row)
        payload["consecutive_failures"] = int(payload.get("consecutive_failures") or 0)
        payload["consecutive_successes"] = int(payload.get("consecutive_successes") or 0)
        payload["last_http_status"] = int(payload.get("last_http_status") or 0)
        payload["maintenance_mode"] = bool(payload.get("maintenance_mode"))
        cooldown_until = clean_text(str(payload.get("cooldown_until") or ""))
        silenced_until = clean_text(str(payload.get("silenced_until") or ""))
        payload["cooldown_active"] = bool(cooldown_until and cooldown_until > utc_now().isoformat())
        payload["silenced_active"] = bool(silenced_until and silenced_until > utc_now().isoformat())
        return payload

    @staticmethod
    def _row_to_source_event_dict(row: sqlite3.Row) -> Dict[str, object]:
        payload = dict(row)
        payload["http_status"] = int(payload.get("http_status") or 0)
        payload["article_id"] = int(payload["article_id"]) if payload.get("article_id") is not None else None
        return payload

    @staticmethod
    def _row_to_alert_state_dict(row: sqlite3.Row) -> Dict[str, object]:
        payload = dict(row)
        payload["is_active"] = bool(payload.get("is_active"))
        payload["delivery_count"] = int(payload.get("delivery_count") or 0)
        return payload

    @staticmethod
    def _row_to_source_alert_dict(row: sqlite3.Row) -> Dict[str, object]:
        payload = dict(row)
        targets_raw = payload.get("targets")
        if isinstance(targets_raw, str) and targets_raw:
            try:
                parsed = json.loads(targets_raw)
            except json.JSONDecodeError:
                parsed = []
        else:
            parsed = []
        payload["targets"] = parsed if isinstance(parsed, list) else []
        return payload

    def insert_article(
        self, article: ArticleRecord, dedup_window_hours: int = 72
    ) -> Dict[str, object]:
        prepared = self._prepare_article_record(article)
        threshold = (prepared.published_at - timedelta(hours=dedup_window_hours)).isoformat()

        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM articles
                WHERE canonical_url = ?
                   OR content_hash = ?
                LIMIT 1
                """,
                (
                    prepared.canonical_url,
                    prepared.content_hash,
                ),
            ).fetchone()

            if existing is not None:
                existing_id = int(existing["id"])
                return {
                    "status": "skipped_exact_duplicate",
                    "inserted": False,
                    "grouped": False,
                    "article": self.get_article(existing_id),
                    "existing_article_id": existing_id,
                }

            cursor = connection.execute(
                """
                INSERT INTO articles (
                    source_id,
                    source_name,
                    title,
                    url,
                    canonical_url,
                    summary,
                    published_at,
                    discovered_at,
                    language,
                    region,
                    country,
                    topic,
                    content_hash,
                    dedup_key,
                    normalized_title,
                    resolved_target,
                    content_fingerprint,
                    duplicate_group,
                    duplicate_of,
                    duplicate_reason,
                    raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prepared.source_id,
                    prepared.source_name,
                    prepared.title,
                    prepared.url,
                    prepared.canonical_url,
                    prepared.summary,
                    prepared.published_at.isoformat(),
                    prepared.discovered_at.isoformat(),
                    prepared.language,
                    prepared.region,
                    prepared.country,
                    prepared.topic,
                    prepared.content_hash,
                    prepared.dedup_key,
                    prepared.normalized_title,
                    prepared.resolved_target,
                    prepared.content_fingerprint,
                    "",
                    None,
                    "",
                    json.dumps(prepared.raw_payload, ensure_ascii=False),
                ),
            )
            article_id = int(cursor.lastrowid)
            duplicate_result = self._assign_duplicate_group_for_article(
                connection,
                article_id=article_id,
                published_after=threshold,
            )

        stored = self.get_article(article_id)
        return {
            "status": str(duplicate_result.get("status", "inserted")),
            "inserted": True,
            "grouped": bool(duplicate_result.get("grouped")),
            "article": stored,
            "primary_article_id": duplicate_result.get("primary_article_id"),
            "duplicate_group": duplicate_result.get("duplicate_group"),
            "duplicate_reason": duplicate_result.get("duplicate_reason", ""),
        }

    def insert_if_new(self, article: ArticleRecord, dedup_window_hours: int = 72) -> bool:
        result = self.insert_article(article, dedup_window_hours=dedup_window_hours)
        return bool(result.get("inserted"))

    @staticmethod
    def _duplicate_group_id(primary_id: int) -> str:
        return f"dg:{primary_id}"

    @staticmethod
    def _prepare_article_record(article: ArticleRecord) -> ArticleRecord:
        normalized_title = clean_text(article.normalized_title) or normalize_title(article.title)
        resolved_target = clean_text(article.resolved_target) or make_resolved_target(
            article.url,
            article.canonical_url,
        )
        content_fingerprint = clean_text(article.content_fingerprint) or make_content_fingerprint(
            article.title,
            article.summary,
            "",
        )
        article.normalized_title = normalized_title
        article.resolved_target = resolved_target
        article.content_fingerprint = content_fingerprint
        return article

    def _assign_duplicate_group_for_article(
        self,
        connection: sqlite3.Connection,
        *,
        article_id: int,
        published_after: str,
    ) -> Dict[str, object]:
        inserted_row = connection.execute(
            "SELECT * FROM articles WHERE id = ? LIMIT 1",
            (article_id,),
        ).fetchone()
        if inserted_row is None:
            return {"status": "missing", "grouped": False}
        inserted = dict(inserted_row)
        candidates = connection.execute(
            """
            SELECT *
            FROM articles
            WHERE id != ?
              AND published_at >= ?
              AND (
                    (resolved_target != '' AND resolved_target = ?)
                 OR (
                        normalized_title != ''
                    AND normalized_title = ?
                    AND (
                            (content_fingerprint != '' AND content_fingerprint = ?)
                         OR dedup_key = ?
                    )
                 )
              )
            ORDER BY published_at DESC, id DESC
            LIMIT 25
            """,
            (
                article_id,
                published_after,
                str(inserted.get("resolved_target") or ""),
                str(inserted.get("normalized_title") or ""),
                str(inserted.get("content_fingerprint") or ""),
                str(inserted.get("dedup_key") or ""),
            ),
        ).fetchall()
        if not candidates:
            group_id = self._duplicate_group_id(article_id)
            connection.execute(
                """
                UPDATE articles
                SET duplicate_group = ?, duplicate_of = NULL, duplicate_reason = ''
                WHERE id = ?
                """,
                (group_id, article_id),
            )
            return {
                "status": "inserted",
                "grouped": False,
                "primary_article_id": article_id,
                "duplicate_group": group_id,
                "duplicate_reason": "",
            }

        selected, reason = self._select_duplicate_candidate(inserted, [dict(row) for row in candidates])
        cluster_rows = [dict(row) for row in candidates if self._same_duplicate_cluster(dict(row), selected)]
        cluster_rows.append(inserted)
        primary_row = max(cluster_rows, key=self._article_primary_score)
        primary_id = int(primary_row["id"])
        group_id = clean_text(str(selected.get("duplicate_group") or "")) or self._duplicate_group_id(primary_id)
        for row in cluster_rows:
            row_id = int(row["id"])
            connection.execute(
                """
                UPDATE articles
                SET
                    duplicate_group = ?,
                    duplicate_of = ?,
                    duplicate_reason = ?
                WHERE id = ?
                """,
                (
                    group_id,
                    None if row_id == primary_id else primary_id,
                    "" if row_id == primary_id else reason,
                    row_id,
                ),
            )
        return {
            "status": "inserted_grouped",
            "grouped": True,
            "primary_article_id": primary_id,
            "duplicate_group": group_id,
            "duplicate_reason": reason,
        }

    @staticmethod
    def _same_duplicate_cluster(row: Dict[str, object], anchor: Dict[str, object]) -> bool:
        row_group = clean_text(str(row.get("duplicate_group") or ""))
        anchor_group = clean_text(str(anchor.get("duplicate_group") or ""))
        if row_group and anchor_group:
            return row_group == anchor_group
        row_primary = int(row.get("duplicate_of") or row.get("id") or 0)
        anchor_primary = int(anchor.get("duplicate_of") or anchor.get("id") or 0)
        return row_primary == anchor_primary or int(row.get("id") or 0) == anchor_primary

    @staticmethod
    def _duplicate_match_reason(left: Dict[str, object], right: Dict[str, object]) -> str:
        if clean_text(str(left.get("resolved_target") or "")) and clean_text(
            str(left.get("resolved_target") or "")
        ) == clean_text(str(right.get("resolved_target") or "")):
            return "resolved_target"
        if clean_text(str(left.get("normalized_title") or "")) == clean_text(
            str(right.get("normalized_title") or "")
        ) and clean_text(str(left.get("content_fingerprint") or "")) == clean_text(
            str(right.get("content_fingerprint") or "")
        ):
            return "normalized_title_content_fingerprint"
        return "normalized_title_dedup_key"

    def _select_duplicate_candidate(
        self, inserted: Dict[str, object], candidates: List[Dict[str, object]]
    ) -> Tuple[Dict[str, object], str]:
        scored: List[Tuple[int, Dict[str, object], str]] = []
        for candidate in candidates:
            score = 0
            if clean_text(str(inserted.get("resolved_target") or "")) and clean_text(
                str(inserted.get("resolved_target") or "")
            ) == clean_text(str(candidate.get("resolved_target") or "")):
                score += 4
            if clean_text(str(inserted.get("normalized_title") or "")) == clean_text(
                str(candidate.get("normalized_title") or "")
            ):
                score += 2
            if clean_text(str(inserted.get("content_fingerprint") or "")) and clean_text(
                str(inserted.get("content_fingerprint") or "")
            ) == clean_text(str(candidate.get("content_fingerprint") or "")):
                score += 2
            if clean_text(str(inserted.get("dedup_key") or "")) == clean_text(
                str(candidate.get("dedup_key") or "")
            ):
                score += 1
            scored.append((score, candidate, self._duplicate_match_reason(inserted, candidate)))
        best_score, best_candidate, reason = max(
            scored,
            key=lambda item: (item[0], self._article_primary_score(item[1])),
        )
        if best_score <= 0:
            return candidates[0], "normalized_title_dedup_key"
        return best_candidate, reason

    @staticmethod
    def _article_primary_score(row: Dict[str, object]) -> Tuple[int, int, int, int, int, int]:
        host = url_host(str(row.get("canonical_url") or row.get("url") or ""))
        is_syndication = host in SYNDICATION_HOSTS
        extracted_length = len(clean_text(str(row.get("extracted_text") or "")))
        llm_ready = 1 if clean_text(str(row.get("llm_status") or "")) == "ready" else 0
        note_length = len(clean_text(str(row.get("editorial_note") or "")))
        published_at = clean_text(str(row.get("published_at") or ""))
        return (
            1 if bool(row.get("must_include")) else 0,
            1 if bool(row.get("is_pinned")) else 0,
            0 if is_syndication else 1,
            extracted_length,
            llm_ready + note_length,
            0 if not published_at else int(published_at.replace("-", "").replace(":", "").replace("T", "").replace("+", "").replace("Z", "")[:14] or 0),
        )

    def list_articles(
        self,
        *,
        region: Optional[str] = None,
        language: Optional[str] = None,
        source_id: Optional[str] = None,
        article_ids: Optional[Iterable[int]] = None,
        duplicate_group: Optional[str] = None,
        primary_only: bool = False,
        since_hours: Optional[int] = None,
        extraction_status: Optional[str] = None,
        extraction_error_category: Optional[str] = None,
        due_only: bool = False,
        limit: int = 50,
        include_hidden: bool = False,
    ) -> List[dict]:
        where_sql, params = self._build_article_filters(
            region=region,
            language=language,
            source_id=source_id,
            article_ids=article_ids,
            duplicate_group=duplicate_group,
            primary_only=primary_only,
            since_hours=since_hours,
            extraction_status=extraction_status,
            extraction_error_category=extraction_error_category,
            due_only=due_only,
            include_hidden=include_hidden,
        )
        params.append(limit)

        query = f"""
            SELECT
                {ARTICLE_SELECT_COLUMNS}
            FROM articles
            {ARTICLE_SELECT_JOINS}
            {where_sql}
            ORDER BY articles.is_pinned DESC, articles.must_include DESC, articles.published_at DESC
            LIMIT ?
        """

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_article_dict(row) for row in rows]

    def get_article(self, article_id: int) -> Optional[dict]:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT
                    {ARTICLE_SELECT_COLUMNS}
                FROM articles
                {ARTICLE_SELECT_JOINS}
                WHERE articles.id = ?
                LIMIT 1
                """,
                (article_id,),
            ).fetchone()
        return self._row_to_article_dict(row) if row else None

    def list_articles_for_enrichment(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        limit: int = 20,
        force: bool = False,
    ) -> List[dict]:
        clauses = ["articles.is_hidden = 0", "articles.language NOT LIKE 'zh%'"]
        params: List[object] = []

        source_list = list(source_ids or [])
        if source_list:
            placeholders = ",".join("?" for _ in source_list)
            clauses.append(f"articles.source_id IN ({placeholders})")
            params.extend(source_list)

        article_list = list(article_ids or [])
        if article_list:
            placeholders = ",".join("?" for _ in article_list)
            clauses.append(f"articles.id IN ({placeholders})")
            params.extend(article_list)

        if since_hours:
            clauses.append("articles.published_at >= ?")
            params.append((utc_now() - timedelta(hours=since_hours)).isoformat())

        if not force:
            clauses.append(
                "("
                "articles.llm_status != 'ready' "
                "OR articles.llm_title_zh = '' "
                "OR articles.llm_summary_zh = '' "
                "OR articles.llm_brief_zh = ''"
                ")"
            )

        params.append(limit)
        where_sql = "WHERE " + " AND ".join(clauses)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    {ARTICLE_SELECT_COLUMNS}
                FROM articles
                {ARTICLE_SELECT_JOINS}
                {where_sql}
                ORDER BY articles.is_pinned DESC, articles.must_include DESC, articles.published_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_article_dict(row) for row in rows]

    def list_articles_for_extraction(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        extraction_status: Optional[str] = None,
        extraction_error_category: Optional[str] = None,
        due_only: bool = False,
        limit: int = 20,
        force: bool = False,
    ) -> List[dict]:
        clauses = ["articles.is_hidden = 0"]
        params: List[object] = []

        source_list = list(source_ids or [])
        if source_list:
            placeholders = ",".join("?" for _ in source_list)
            clauses.append(f"articles.source_id IN ({placeholders})")
            params.extend(source_list)

        article_list = list(article_ids or [])
        if article_list:
            placeholders = ",".join("?" for _ in article_list)
            clauses.append(f"articles.id IN ({placeholders})")
            params.extend(article_list)

        if since_hours:
            clauses.append("articles.published_at >= ?")
            params.append((utc_now() - timedelta(hours=since_hours)).isoformat())

        clauses.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM source_states
                WHERE source_states.source_id = articles.source_id
                  AND (
                      source_states.maintenance_mode = 1
                      OR (
                          source_states.cooldown_until != ''
                          AND source_states.cooldown_until > ?
                      )
                  )
            )
            """
        )
        params.append(utc_now().isoformat())

        if extraction_status:
            clauses.append("articles.extraction_status = ?")
            params.append(extraction_status)

        if extraction_error_category:
            clauses.append("articles.extraction_error_category = ?")
            params.append(extraction_error_category)

        if due_only:
            retry_clause, retry_params = self._build_retry_due_filter()
            clauses.append(retry_clause)
            params.extend(retry_params)
        elif not force:
            retry_threshold = utc_now().isoformat()
            clauses.append(
                """
                (
                    articles.extraction_status = 'pending'
                    OR (
                        articles.extraction_status IN ('error', 'throttled', 'temporary_error')
                        AND (
                            articles.extraction_next_retry_at = ''
                            OR articles.extraction_next_retry_at <= ?
                        )
                    )
                )
                """
            )
            params.append(retry_threshold)

        params.append(limit)
        where_sql = "WHERE " + " AND ".join(clauses)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    {ARTICLE_SELECT_COLUMNS}
                FROM articles
                {ARTICLE_SELECT_JOINS}
                {where_sql}
                ORDER BY articles.is_pinned DESC, articles.must_include DESC, articles.published_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_article_dict(row) for row in rows]

    def get_source_state(self, source_id: str) -> Optional[dict]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    source_id,
                    source_name,
                    cooldown_status,
                    cooldown_until,
                    consecutive_failures,
                    consecutive_successes,
                    last_error_category,
                    last_http_status,
                    last_error,
                    last_error_at,
                    last_success_at,
                    last_recovered_at,
                    silenced_until,
                    maintenance_mode,
                    acknowledged_at,
                    ack_note,
                    updated_at
                FROM source_states
                WHERE source_id = ?
                LIMIT 1
                """,
                (source_id,),
            ).fetchone()
        return self._row_to_source_state_dict(row) if row else None

    def list_source_states(
        self,
        *,
        active_only: bool = False,
        limit: int = 200,
    ) -> List[dict]:
        clauses = []
        params: List[object] = []
        if active_only:
            clauses.append("cooldown_until != '' AND cooldown_until > ?")
            params.append(utc_now().isoformat())

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    source_id,
                    source_name,
                    cooldown_status,
                    cooldown_until,
                    consecutive_failures,
                    consecutive_successes,
                    last_error_category,
                    last_http_status,
                    last_error,
                    last_error_at,
                    last_success_at,
                    last_recovered_at,
                    silenced_until,
                    maintenance_mode,
                    acknowledged_at,
                    ack_note,
                    updated_at
                FROM source_states
                {where_sql}
                ORDER BY cooldown_until DESC, updated_at DESC, source_id ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_source_state_dict(row) for row in rows]

    def upsert_source_state(
        self,
        *,
        source_id: str,
        source_name: str,
        cooldown_status: str = "",
        cooldown_until: str = "",
        consecutive_failures: int = 0,
        consecutive_successes: int = 0,
        last_error_category: str = "",
        last_http_status: int = 0,
        last_error: str = "",
        last_error_at: str = "",
        last_success_at: str = "",
        last_recovered_at: str = "",
        silenced_until: Optional[str] = None,
        maintenance_mode: Optional[bool] = None,
        acknowledged_at: Optional[str] = None,
        ack_note: Optional[str] = None,
    ) -> Optional[dict]:
        existing = self.get_source_state(source_id) or {}
        effective_source_name = clean_text(source_name) or clean_text(
            str(existing.get("source_name", ""))
        ) or source_id
        effective_silenced_until = (
            clean_text(str(existing.get("silenced_until", "")))
            if silenced_until is None
            else clean_text(str(silenced_until))
        )
        effective_maintenance_mode = (
            bool(existing.get("maintenance_mode"))
            if maintenance_mode is None
            else bool(maintenance_mode)
        )
        effective_acknowledged_at = (
            clean_text(str(existing.get("acknowledged_at", "")))
            if acknowledged_at is None
            else clean_text(str(acknowledged_at))
        )
        effective_ack_note = (
            clean_text(str(existing.get("ack_note", "")))
            if ack_note is None
            else clean_text(str(ack_note))
        )
        updated_at = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO source_states (
                    source_id,
                    source_name,
                    cooldown_status,
                    cooldown_until,
                    consecutive_failures,
                    consecutive_successes,
                    last_error_category,
                    last_http_status,
                    last_error,
                    last_error_at,
                    last_success_at,
                    last_recovered_at,
                    silenced_until,
                    maintenance_mode,
                    acknowledged_at,
                    ack_note,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    source_name = excluded.source_name,
                    cooldown_status = excluded.cooldown_status,
                    cooldown_until = excluded.cooldown_until,
                    consecutive_failures = excluded.consecutive_failures,
                    consecutive_successes = excluded.consecutive_successes,
                    last_error_category = excluded.last_error_category,
                    last_http_status = excluded.last_http_status,
                    last_error = excluded.last_error,
                    last_error_at = CASE
                        WHEN excluded.last_error_at != '' THEN excluded.last_error_at
                        ELSE source_states.last_error_at
                    END,
                    last_success_at = CASE
                        WHEN excluded.last_success_at != '' THEN excluded.last_success_at
                        ELSE source_states.last_success_at
                    END,
                    last_recovered_at = CASE
                        WHEN excluded.last_recovered_at != '' THEN excluded.last_recovered_at
                        ELSE source_states.last_recovered_at
                    END,
                    silenced_until = excluded.silenced_until,
                    maintenance_mode = excluded.maintenance_mode,
                    acknowledged_at = excluded.acknowledged_at,
                    ack_note = excluded.ack_note,
                    updated_at = excluded.updated_at
                """,
                (
                    source_id,
                    effective_source_name,
                    cooldown_status,
                    cooldown_until,
                    consecutive_failures,
                    consecutive_successes,
                    last_error_category,
                    last_http_status,
                    last_error,
                    last_error_at,
                    last_success_at,
                    last_recovered_at,
                    effective_silenced_until,
                    1 if effective_maintenance_mode else 0,
                    effective_acknowledged_at,
                    effective_ack_note,
                    updated_at,
                ),
            )
        return self.get_source_state(source_id)

    def mark_source_success(
        self,
        *,
        source_id: str,
        source_name: str,
        recovery_success_threshold: int = 2,
    ) -> Optional[dict]:
        current = self.get_source_state(source_id) or {}
        timestamp = utc_now().isoformat()
        threshold = max(1, int(recovery_success_threshold))
        next_successes = min(
            threshold,
            int(current.get("consecutive_successes") or 0) + 1,
        )
        recovery_pending = bool(
            clean_text(str(current.get("cooldown_status", "")))
            or clean_text(str(current.get("acknowledged_at", "")))
            or clean_text(str(current.get("ack_note", "")))
        )
        recovered = recovery_pending and next_successes >= threshold
        last_recovered_at = timestamp if recovered else ""
        return self.upsert_source_state(
            source_id=source_id,
            source_name=source_name,
            cooldown_status="" if recovered else str(current.get("cooldown_status", "")),
            cooldown_until="" if recovered else str(current.get("cooldown_until", "")),
            consecutive_failures=0,
            consecutive_successes=next_successes,
            last_error_category="" if recovered else str(current.get("last_error_category", "")),
            last_http_status=0 if recovered else int(current.get("last_http_status") or 0),
            last_error="" if recovered else str(current.get("last_error", "")),
            last_error_at=str(current.get("last_error_at", "")),
            last_success_at=timestamp,
            last_recovered_at=last_recovered_at,
            silenced_until=str(current.get("silenced_until", "")),
            maintenance_mode=bool(current.get("maintenance_mode")),
            acknowledged_at="" if recovered else str(current.get("acknowledged_at", "")),
            ack_note="" if recovered else str(current.get("ack_note", "")),
        )

    def reset_source_cooldowns(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        active_only: bool = True,
    ) -> List[dict]:
        clauses = []
        params: List[object] = []
        source_list = [str(item) for item in (source_ids or []) if str(item)]
        if source_list:
            placeholders = ",".join("?" for _ in source_list)
            clauses.append(f"source_id IN ({placeholders})")
            params.extend(source_list)
        if active_only:
            clauses.append("cooldown_until != '' AND cooldown_until > ?")
            params.append(utc_now().isoformat())

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT source_id
                FROM source_states
                {where_sql}
                ORDER BY source_id
                """,
                params,
            ).fetchall()
            source_id_rows = [str(row["source_id"]) for row in rows]
            if source_id_rows:
                placeholders = ",".join("?" for _ in source_id_rows)
                connection.execute(
                    f"""
                    UPDATE source_states
                    SET
                        cooldown_status = '',
                        cooldown_until = '',
                        consecutive_failures = 0,
                        consecutive_successes = 0,
                        acknowledged_at = '',
                        ack_note = '',
                        updated_at = ?
                    WHERE source_id IN ({placeholders})
                    """,
                    [utc_now().isoformat(), *source_id_rows],
                )
        return [state for source_id in source_id_rows if (state := self.get_source_state(source_id))]

    def update_source_runtime_controls(
        self,
        *,
        source_id: str,
        source_name: str = "",
        silenced_until: Optional[str] = None,
        maintenance_mode: Optional[bool] = None,
        acknowledged_at: Optional[str] = None,
        ack_note: Optional[str] = None,
        clear_ack: bool = False,
    ) -> Optional[dict]:
        current = self.get_source_state(source_id) or {}
        if clear_ack:
            acknowledged_at = ""
            ack_note = ""
        return self.upsert_source_state(
            source_id=source_id,
            source_name=source_name or str(current.get("source_name", "")) or source_id,
            cooldown_status=str(current.get("cooldown_status", "")),
            cooldown_until=str(current.get("cooldown_until", "")),
            consecutive_failures=int(current.get("consecutive_failures") or 0),
            consecutive_successes=int(current.get("consecutive_successes") or 0),
            last_error_category=str(current.get("last_error_category", "")),
            last_http_status=int(current.get("last_http_status") or 0),
            last_error=str(current.get("last_error", "")),
            last_error_at=str(current.get("last_error_at", "")),
            last_success_at=str(current.get("last_success_at", "")),
            last_recovered_at=str(current.get("last_recovered_at", "")),
            silenced_until=silenced_until,
            maintenance_mode=maintenance_mode,
            acknowledged_at=acknowledged_at,
            ack_note=ack_note,
        )

    def record_source_event(
        self,
        *,
        source_id: str,
        source_name: str,
        event_type: str,
        status: str,
        error_category: str = "",
        http_status: int = 0,
        article_id: Optional[int] = None,
        article_title: str = "",
        message: str = "",
    ) -> dict:
        created_at = utc_now().isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO source_events (
                    source_id,
                    source_name,
                    event_type,
                    status,
                    error_category,
                    http_status,
                    article_id,
                    article_title,
                    message,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    source_name,
                    event_type,
                    status,
                    error_category,
                    http_status,
                    article_id,
                    article_title,
                    message,
                    created_at,
                ),
            )
            event_id = int(cursor.lastrowid)
            row = connection.execute(
                """
                SELECT
                    id,
                    source_id,
                    source_name,
                    event_type,
                    status,
                    error_category,
                    http_status,
                    article_id,
                    article_title,
                    message,
                    created_at
                FROM source_events
                WHERE id = ?
                LIMIT 1
                """,
                (event_id,),
            ).fetchone()
        return self._row_to_source_event_dict(row) if row else {}

    def list_source_events(
        self,
        *,
        source_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        clauses = []
        params: List[object] = []
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    source_id,
                    source_name,
                    event_type,
                    status,
                    error_category,
                    http_status,
                    article_id,
                    article_title,
                    message,
                    created_at
                FROM source_events
                {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_source_event_dict(row) for row in rows]

    def get_source_event_summaries(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        sample_size: int = 20,
        limit_per_source: int = 5,
    ) -> Dict[str, dict]:
        requested_sources = [str(item) for item in (source_ids or []) if str(item)]
        params: List[object] = []
        where_sql = ""
        if requested_sources:
            placeholders = ",".join("?" for _ in requested_sources)
            where_sql = f"WHERE source_id IN ({placeholders})"
            params.extend(requested_sources)

        fetch_limit = max(100, max(sample_size, limit_per_source) * max(1, len(requested_sources) or 12))
        params.append(fetch_limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    source_id,
                    source_name,
                    event_type,
                    status,
                    error_category,
                    http_status,
                    article_id,
                    article_title,
                    message,
                    created_at
                FROM source_events
                {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        grouped: Dict[str, dict] = {}
        for row in rows:
            event = self._row_to_source_event_dict(row)
            source_id = str(event["source_id"])
            summary = grouped.setdefault(
                source_id,
                {
                    "recent_operations": [],
                    "sample": [],
                    "last_success_at": "",
                    "last_failure_at": "",
                    "recent_failure_categories": {},
                    "recent_success_rate": None,
                },
            )
            if len(summary["recent_operations"]) < limit_per_source:
                summary["recent_operations"].append(event)
            if len(summary["sample"]) < sample_size:
                summary["sample"].append(event)

        for source_id, summary in grouped.items():
            sample = list(summary.pop("sample"))
            considered = [
                event
                for event in sample
                if str(event.get("status", "")) not in {"skipped"}
            ]
            if considered:
                success_total = sum(1 for event in considered if str(event.get("status", "")) == "ok")
                summary["recent_success_rate"] = round((success_total / len(considered)) * 100, 1)
            else:
                summary["recent_success_rate"] = None

            failure_categories: Dict[str, int] = {}
            for event in sample:
                if not summary["last_success_at"] and str(event.get("status", "")) == "ok":
                    summary["last_success_at"] = str(event.get("created_at", ""))
                if (
                    not summary["last_failure_at"]
                    and str(event.get("status", "")) not in {"ok", "skipped"}
                ):
                    summary["last_failure_at"] = str(event.get("created_at", ""))
                category = clean_text(str(event.get("error_category", "")))
                if category:
                    failure_categories[category] = failure_categories.get(category, 0) + 1
            summary["recent_failure_categories"] = failure_categories

        return grouped

    def get_alert_state(self, alert_key: str) -> Optional[dict]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    alert_key,
                    is_active,
                    fingerprint,
                    last_status,
                    last_title,
                    last_message,
                    last_sent_at,
                    last_recovered_at,
                    delivery_count,
                    updated_at
                FROM alert_states
                WHERE alert_key = ?
                LIMIT 1
                """,
                (alert_key,),
            ).fetchone()
        return self._row_to_alert_state_dict(row) if row else None

    def list_alert_states(
        self,
        *,
        prefix: Optional[str] = None,
        active_only: bool = False,
        limit: int = 200,
    ) -> List[dict]:
        clauses = []
        params: List[object] = []
        if prefix:
            clauses.append("alert_key LIKE ?")
            params.append(f"{prefix}%")
        if active_only:
            clauses.append("is_active = 1")

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    alert_key,
                    is_active,
                    fingerprint,
                    last_status,
                    last_title,
                    last_message,
                    last_sent_at,
                    last_recovered_at,
                    delivery_count,
                    updated_at
                FROM alert_states
                {where_sql}
                ORDER BY updated_at DESC, alert_key ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_alert_state_dict(row) for row in rows]

    def save_alert_state(
        self,
        *,
        alert_key: str,
        is_active: bool,
        fingerprint: str = "",
        last_status: str = "",
        last_title: str = "",
        last_message: str = "",
        sent_at: str = "",
        recovered_at: str = "",
        increment_delivery: bool = False,
    ) -> Optional[dict]:
        updated_at = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO alert_states (
                    alert_key,
                    is_active,
                    fingerprint,
                    last_status,
                    last_title,
                    last_message,
                    last_sent_at,
                    last_recovered_at,
                    delivery_count,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alert_key) DO UPDATE SET
                    is_active = excluded.is_active,
                    fingerprint = excluded.fingerprint,
                    last_status = excluded.last_status,
                    last_title = excluded.last_title,
                    last_message = excluded.last_message,
                    last_sent_at = CASE
                        WHEN excluded.last_sent_at != '' THEN excluded.last_sent_at
                        ELSE alert_states.last_sent_at
                    END,
                    last_recovered_at = CASE
                        WHEN excluded.last_recovered_at != '' THEN excluded.last_recovered_at
                        ELSE alert_states.last_recovered_at
                    END,
                    delivery_count = CASE
                        WHEN excluded.delivery_count > 0 THEN alert_states.delivery_count + excluded.delivery_count
                        ELSE alert_states.delivery_count
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    alert_key,
                    1 if is_active else 0,
                    fingerprint,
                    last_status,
                    last_title,
                    last_message,
                    sent_at,
                    recovered_at,
                    1 if increment_delivery else 0,
                    updated_at,
                ),
            )
        return self.get_alert_state(alert_key)

    def record_source_alert(
        self,
        *,
        source_id: str,
        source_name: str,
        alert_key: str,
        alert_status: str,
        severity: str = "",
        title: str = "",
        message: str = "",
        fingerprint: str = "",
        targets: Optional[Iterable[dict]] = None,
    ) -> dict:
        created_at = utc_now().isoformat()
        target_payload = []
        for item in list(targets or []):
            if not isinstance(item, dict):
                continue
            target_payload.append(
                {
                    "target": clean_text(str(item.get("target", ""))),
                    "status": clean_text(str(item.get("status", ""))),
                }
            )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO source_alerts (
                    source_id,
                    source_name,
                    alert_key,
                    alert_status,
                    severity,
                    title,
                    message,
                    fingerprint,
                    targets,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    source_name,
                    alert_key,
                    alert_status,
                    severity,
                    title,
                    message,
                    fingerprint,
                    json.dumps(target_payload, ensure_ascii=True),
                    created_at,
                ),
            )
            alert_id = int(cursor.lastrowid)
            row = connection.execute(
                """
                SELECT
                    id,
                    source_id,
                    source_name,
                    alert_key,
                    alert_status,
                    severity,
                    title,
                    message,
                    fingerprint,
                    targets,
                    created_at
                FROM source_alerts
                WHERE id = ?
                LIMIT 1
                """,
                (alert_id,),
            ).fetchone()
        return self._row_to_source_alert_dict(row) if row else {}

    def list_source_alerts(
        self,
        *,
        source_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        clauses = []
        params: List[object] = []
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    source_id,
                    source_name,
                    alert_key,
                    alert_status,
                    severity,
                    title,
                    message,
                    fingerprint,
                    targets,
                    created_at
                FROM source_alerts
                {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_source_alert_dict(row) for row in rows]

    def get_monitoring_counters(self) -> Dict[str, object]:
        with self._connect() as connection:
            extraction_rows = connection.execute(
                """
                SELECT
                    error_category,
                    COUNT(*) AS total
                FROM (
                    SELECT error_category
                    FROM source_events
                    WHERE event_type = 'extract'
                      AND status NOT IN ('ok', 'skipped')
                      AND error_category != ''
                    UNION ALL
                    SELECT error_category
                    FROM source_events_archive
                    WHERE event_type = 'extract'
                      AND status NOT IN ('ok', 'skipped')
                      AND error_category != ''
                )
                GROUP BY error_category
                ORDER BY error_category ASC
                """
            ).fetchall()
            source_recovery_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM (
                    SELECT id
                    FROM source_events
                    WHERE event_type = 'cooldown'
                      AND status = 'recovered'
                    UNION ALL
                    SELECT id
                    FROM source_events_archive
                    WHERE event_type = 'cooldown'
                      AND status = 'recovered'
                )
                """
            ).fetchone()
            alert_sends_row = connection.execute(
                """
                SELECT COALESCE(SUM(delivery_count), 0) AS total
                FROM alert_states
                """
            ).fetchone()

        return {
            "extract_failures_total": {
                clean_text(str(row["error_category"])): int(row["total"] or 0)
                for row in extraction_rows
                if clean_text(str(row["error_category"]))
            },
            "source_recoveries_total": int(source_recovery_row["total"] or 0),
            "alert_sends_total": int(alert_sends_row["total"] or 0),
        }

    def prune_source_runtime_history(
        self,
        *,
        retention_days: int,
        archive: bool = True,
    ) -> Dict[str, object]:
        retention = max(1, int(retention_days))
        cutoff = (utc_now() - timedelta(days=retention)).isoformat()
        archived_at = utc_now().isoformat()
        with self._connect() as connection:
            event_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM source_events
                WHERE created_at < ?
                """,
                (cutoff,),
            ).fetchone()
            alert_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM source_alerts
                WHERE created_at < ?
                """,
                (cutoff,),
            ).fetchone()
            event_total = int((event_row or {})["total"] or 0)
            alert_total = int((alert_row or {})["total"] or 0)

            if archive and event_total:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO source_events_archive (
                        id,
                        source_id,
                        source_name,
                        event_type,
                        status,
                        error_category,
                        http_status,
                        article_id,
                        article_title,
                        message,
                        created_at,
                        archived_at
                    )
                    SELECT
                        id,
                        source_id,
                        source_name,
                        event_type,
                        status,
                        error_category,
                        http_status,
                        article_id,
                        article_title,
                        message,
                        created_at,
                        ?
                    FROM source_events
                    WHERE created_at < ?
                    """,
                    (archived_at, cutoff),
                )
            if archive and alert_total:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO source_alerts_archive (
                        id,
                        source_id,
                        source_name,
                        alert_key,
                        alert_status,
                        severity,
                        title,
                        message,
                        fingerprint,
                        targets,
                        created_at,
                        archived_at
                    )
                    SELECT
                        id,
                        source_id,
                        source_name,
                        alert_key,
                        alert_status,
                        severity,
                        title,
                        message,
                        fingerprint,
                        targets,
                        created_at,
                        ?
                    FROM source_alerts
                    WHERE created_at < ?
                    """,
                    (archived_at, cutoff),
                )
            deleted_events = connection.execute(
                """
                DELETE FROM source_events
                WHERE created_at < ?
                """,
                (cutoff,),
            ).rowcount
            deleted_alerts = connection.execute(
                """
                DELETE FROM source_alerts
                WHERE created_at < ?
                """,
                (cutoff,),
            ).rowcount
            archive_event_row = connection.execute(
                "SELECT COUNT(*) AS total FROM source_events_archive"
            ).fetchone()
            archive_alert_row = connection.execute(
                "SELECT COUNT(*) AS total FROM source_alerts_archive"
            ).fetchone()
        return {
            "retention_days": retention,
            "cutoff": cutoff,
            "archive": archive,
            "events_considered": event_total,
            "alerts_considered": alert_total,
            "events_archived": event_total if archive else 0,
            "alerts_archived": alert_total if archive else 0,
            "events_deleted": int(deleted_events or 0),
            "alerts_deleted": int(deleted_alerts or 0),
            "archived_events_total": int((archive_event_row or {})["total"] or 0),
            "archived_alerts_total": int((archive_alert_row or {})["total"] or 0),
        }

    def list_google_news_articles(
        self,
        *,
        source_ids: Optional[Iterable[str]] = None,
        article_ids: Optional[Iterable[int]] = None,
        since_hours: Optional[int] = None,
        limit: int = 50,
    ) -> List[dict]:
        clauses = ["(articles.url LIKE ? OR articles.canonical_url LIKE ?)"]
        params: List[object] = ["https://news.google.com/%", "https://news.google.com/%"]

        source_list = list(source_ids or [])
        if source_list:
            placeholders = ",".join("?" for _ in source_list)
            clauses.append(f"articles.source_id IN ({placeholders})")
            params.extend(source_list)

        article_list = list(article_ids or [])
        if article_list:
            placeholders = ",".join("?" for _ in article_list)
            clauses.append(f"articles.id IN ({placeholders})")
            params.extend(article_list)

        if since_hours:
            clauses.append("articles.published_at >= ?")
            params.append((utc_now() - timedelta(hours=since_hours)).isoformat())

        params.append(limit)
        where_sql = "WHERE " + " AND ".join(clauses)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    {ARTICLE_SELECT_COLUMNS}
                FROM articles
                {ARTICLE_SELECT_JOINS}
                {where_sql}
                ORDER BY articles.published_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_article_dict(row) for row in rows]

    def save_article_extraction(
        self,
        article_id: int,
        *,
        extracted_text: str,
    ) -> Optional[dict]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE articles
                SET
                    extracted_text = ?,
                    extraction_status = 'ready',
                    extraction_error = '',
                    extraction_updated_at = ?,
                    extraction_attempts = extraction_attempts + 1,
                    extraction_last_http_status = 0,
                    extraction_next_retry_at = '',
                    extraction_error_category = ''
                WHERE id = ?
                """,
                (
                    extracted_text,
                    utc_now().isoformat(),
                    article_id,
                ),
            )
            row = connection.execute(
                "SELECT title, summary FROM articles WHERE id = ? LIMIT 1",
                (article_id,),
            ).fetchone()
            if row is not None:
                connection.execute(
                    """
                    UPDATE articles
                    SET content_fingerprint = ?
                    WHERE id = ?
                    """,
                    (
                        make_content_fingerprint(
                            str(row["title"] or ""),
                            str(row["summary"] or ""),
                            extracted_text,
                        ),
                        article_id,
                    ),
                )
        return self.get_article(article_id)

    def mark_article_extraction_failure(
        self,
        article_id: int,
        *,
        error: str,
        status: str,
        error_category: str,
        http_status: int = 0,
        next_retry_at: str = "",
    ) -> Optional[dict]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE articles
                SET
                    extraction_status = ?,
                    extraction_error = ?,
                    extraction_updated_at = ?,
                    extraction_attempts = extraction_attempts + 1,
                    extraction_last_http_status = ?,
                    extraction_next_retry_at = ?,
                    extraction_error_category = ?
                WHERE id = ?
                """,
                (
                    status,
                    error,
                    utc_now().isoformat(),
                    http_status,
                    next_retry_at,
                    error_category,
                    article_id,
                ),
            )
        return self.get_article(article_id)

    def update_article_urls(
        self,
        article_id: int,
        *,
        url: str,
        canonical_url: Optional[str] = None,
    ) -> Optional[dict]:
        with self._connect() as connection:
            if canonical_url:
                try:
                    connection.execute(
                        """
                        UPDATE articles
                        SET
                            url = ?,
                            canonical_url = ?,
                            resolved_target = ?
                        WHERE id = ?
                        """,
                        (
                            url,
                            canonical_url,
                            make_resolved_target(url, canonical_url),
                            article_id,
                        ),
                    )
                except sqlite3.IntegrityError:
                    connection.execute(
                        """
                        UPDATE articles
                        SET
                            url = ?,
                            resolved_target = ?
                        WHERE id = ?
                        """,
                        (
                            url,
                            make_resolved_target(url),
                            article_id,
                        ),
                    )
            else:
                connection.execute(
                    """
                    UPDATE articles
                    SET
                        url = ?,
                        resolved_target = ?
                    WHERE id = ?
                    """,
                    (
                        url,
                        make_resolved_target(url),
                        article_id,
                    ),
                )
            self._assign_duplicate_group_for_article(
                connection,
                article_id=article_id,
                published_after=(utc_now() - timedelta(days=365)).isoformat(),
            )
        return self.get_article(article_id)

    def resolve_article_urls(
        self,
        article_id: int,
        *,
        url: str,
        canonical_url: str,
    ) -> Dict[str, object]:
        normalized_url = clean_text(url)
        normalized_canonical = canonicalize_url(canonical_url or normalized_url)
        target_id = article_id
        action = "updated"
        merged_from_article_id = None

        with self._connect() as connection:
            source_row = connection.execute(
                "SELECT * FROM articles WHERE id = ? LIMIT 1",
                (article_id,),
            ).fetchone()
            if source_row is None:
                return {"action": "missing", "article": None}

            conflict_row = connection.execute(
                """
                SELECT *
                FROM articles
                WHERE canonical_url = ? AND id != ?
                LIMIT 1
                """,
                (
                    normalized_canonical,
                    article_id,
                ),
            ).fetchone()

            if conflict_row is None:
                connection.execute(
                    """
                    UPDATE articles
                    SET
                        url = ?,
                        canonical_url = ?,
                        resolved_target = ?
                    WHERE id = ?
                    """,
                    (
                        normalized_url,
                        normalized_canonical,
                        make_resolved_target(normalized_url, normalized_canonical),
                        article_id,
                    ),
                )
                self._assign_duplicate_group_for_article(
                    connection,
                    article_id=article_id,
                    published_after=(utc_now() - timedelta(days=365)).isoformat(),
                )
            else:
                target_id = int(conflict_row["id"])
                merged_from_article_id = article_id
                action = "merged"
                merged_payload = self._merge_article_rows(
                    dict(conflict_row),
                    dict(source_row),
                    resolved_url=normalized_url,
                    resolved_canonical_url=normalized_canonical,
                )
                connection.execute(
                    """
                    UPDATE articles
                    SET
                        url = ?,
                        canonical_url = ?,
                        summary = ?,
                        discovered_at = ?,
                        extracted_text = ?,
                        extraction_status = ?,
                        extraction_error = ?,
                        extraction_updated_at = ?,
                        extraction_attempts = ?,
                        extraction_last_http_status = ?,
                        extraction_next_retry_at = ?,
                        extraction_error_category = ?,
                        llm_title_zh = ?,
                        llm_summary_zh = ?,
                        llm_brief_zh = ?,
                        llm_status = ?,
                        llm_provider = ?,
                        llm_model = ?,
                        llm_error = ?,
                        llm_updated_at = ?,
                        is_hidden = ?,
                        is_pinned = ?,
                        is_suppressed = ?,
                        must_include = ?,
                        editorial_note = ?,
                        normalized_title = ?,
                        resolved_target = ?,
                        content_fingerprint = ?,
                        duplicate_group = ?,
                        duplicate_of = ?,
                        duplicate_reason = ?,
                        raw_payload = ?
                    WHERE id = ?
                    """,
                    (
                        merged_payload["url"],
                        merged_payload["canonical_url"],
                        merged_payload["summary"],
                        merged_payload["discovered_at"],
                        merged_payload["extracted_text"],
                        merged_payload["extraction_status"],
                        merged_payload["extraction_error"],
                        merged_payload["extraction_updated_at"],
                        merged_payload["extraction_attempts"],
                        merged_payload["extraction_last_http_status"],
                        merged_payload["extraction_next_retry_at"],
                        merged_payload["extraction_error_category"],
                        merged_payload["llm_title_zh"],
                        merged_payload["llm_summary_zh"],
                        merged_payload["llm_brief_zh"],
                        merged_payload["llm_status"],
                        merged_payload["llm_provider"],
                        merged_payload["llm_model"],
                        merged_payload["llm_error"],
                        merged_payload["llm_updated_at"],
                        merged_payload["is_hidden"],
                        merged_payload["is_pinned"],
                        merged_payload["is_suppressed"],
                        merged_payload["must_include"],
                        merged_payload["editorial_note"],
                        merged_payload["normalized_title"],
                        merged_payload["resolved_target"],
                        merged_payload["content_fingerprint"],
                        merged_payload["duplicate_group"],
                        merged_payload["duplicate_of"],
                        merged_payload["duplicate_reason"],
                        json.dumps(merged_payload["raw_payload"], ensure_ascii=False),
                        target_id,
                    ),
                )
                connection.execute("DELETE FROM articles WHERE id = ?", (article_id,))

        return {
            "action": action,
            "article": self.get_article(target_id),
            "merged_into_article_id": target_id if action == "merged" else None,
            "merged_from_article_id": merged_from_article_id,
        }

    @staticmethod
    def _merge_article_rows(
        target: Dict[str, object],
        source: Dict[str, object],
        *,
        resolved_url: str,
        resolved_canonical_url: str,
    ) -> Dict[str, object]:
        extracted_text = ArticleRepository._prefer_longer_text(
            str(target.get("extracted_text") or ""),
            str(source.get("extracted_text") or ""),
        )
        target_extraction_status = str(target.get("extraction_status") or "pending")
        source_extraction_status = str(source.get("extraction_status") or "pending")
        extraction_status = (
            "ready"
            if extracted_text
            else ArticleRepository._best_status(target_extraction_status, source_extraction_status)
        )
        llm_title_zh = ArticleRepository._prefer_longer_text(
            str(target.get("llm_title_zh") or ""),
            str(source.get("llm_title_zh") or ""),
        )
        llm_summary_zh = ArticleRepository._prefer_longer_text(
            str(target.get("llm_summary_zh") or ""),
            str(source.get("llm_summary_zh") or ""),
        )
        llm_brief_zh = ArticleRepository._prefer_longer_text(
            str(target.get("llm_brief_zh") or ""),
            str(source.get("llm_brief_zh") or ""),
        )
        llm_status = (
            "ready"
            if any([llm_title_zh, llm_summary_zh, llm_brief_zh])
            else ArticleRepository._best_status(
                str(target.get("llm_status") or "pending"),
                str(source.get("llm_status") or "pending"),
            )
        )
        preferred_llm_row = target
        if llm_status == "ready":
            target_llm_score = sum(
                len(str(target.get(key) or ""))
                for key in ("llm_title_zh", "llm_summary_zh", "llm_brief_zh")
            )
            source_llm_score = sum(
                len(str(source.get(key) or ""))
                for key in ("llm_title_zh", "llm_summary_zh", "llm_brief_zh")
            )
            if source_llm_score > target_llm_score:
                preferred_llm_row = source
        elif ArticleRepository._status_rank(
            str(source.get("llm_status") or "pending")
        ) > ArticleRepository._status_rank(str(target.get("llm_status") or "pending")):
            preferred_llm_row = source

        merged_raw_payload = ArticleRepository._merge_raw_payloads(
            str(target.get("raw_payload") or "{}"),
            str(source.get("raw_payload") or "{}"),
            resolved_url=resolved_url,
            original_url=str(source.get("url") or ""),
        )

        return {
            "url": resolved_url,
            "canonical_url": resolved_canonical_url,
            "normalized_title": clean_text(str(target.get("normalized_title") or ""))
            or clean_text(str(source.get("normalized_title") or ""))
            or normalize_title(str(target.get("title") or source.get("title") or "")),
            "resolved_target": make_resolved_target(resolved_url, resolved_canonical_url),
            "content_fingerprint": make_content_fingerprint(
                str(target.get("title") or source.get("title") or ""),
                ArticleRepository._prefer_longer_text(
                    str(target.get("summary") or ""),
                    str(source.get("summary") or ""),
                ),
                extracted_text,
            ),
            "summary": ArticleRepository._prefer_longer_text(
                str(target.get("summary") or ""),
                str(source.get("summary") or ""),
            ),
            "discovered_at": ArticleRepository._min_text(
                str(target.get("discovered_at") or ""),
                str(source.get("discovered_at") or ""),
            ),
            "extracted_text": extracted_text,
            "extraction_status": extraction_status,
            "extraction_error": ""
            if extraction_status == "ready"
            else ArticleRepository._prefer_longer_text(
                str(target.get("extraction_error") or ""),
                str(source.get("extraction_error") or ""),
            ),
            "extraction_updated_at": ArticleRepository._max_text(
                str(target.get("extraction_updated_at") or ""),
                str(source.get("extraction_updated_at") or ""),
            ),
            "extraction_attempts": int(target.get("extraction_attempts") or 0)
            + int(source.get("extraction_attempts") or 0),
            "extraction_last_http_status": ArticleRepository._max_int(
                int(target.get("extraction_last_http_status") or 0),
                int(source.get("extraction_last_http_status") or 0),
            ),
            "extraction_next_retry_at": ""
            if extraction_status == "ready"
            else ArticleRepository._max_text(
                str(target.get("extraction_next_retry_at") or ""),
                str(source.get("extraction_next_retry_at") or ""),
            ),
            "extraction_error_category": ""
            if extraction_status == "ready"
            else ArticleRepository._best_status(
                str(target.get("extraction_error_category") or ""),
                str(source.get("extraction_error_category") or ""),
            ),
            "llm_title_zh": llm_title_zh,
            "llm_summary_zh": llm_summary_zh,
            "llm_brief_zh": llm_brief_zh,
            "llm_status": llm_status,
            "llm_provider": str(preferred_llm_row.get("llm_provider") or ""),
            "llm_model": str(preferred_llm_row.get("llm_model") or ""),
            "llm_error": ""
            if llm_status == "ready"
            else ArticleRepository._prefer_longer_text(
                str(target.get("llm_error") or ""),
                str(source.get("llm_error") or ""),
            ),
            "llm_updated_at": ArticleRepository._max_text(
                str(target.get("llm_updated_at") or ""),
                str(source.get("llm_updated_at") or ""),
            ),
            "is_hidden": 1
            if bool(target.get("is_hidden")) and bool(source.get("is_hidden"))
            else 0,
            "is_pinned": 1
            if bool(target.get("is_pinned")) or bool(source.get("is_pinned"))
            else 0,
            "is_suppressed": 1
            if bool(target.get("is_suppressed")) or bool(source.get("is_suppressed"))
            else 0,
            "must_include": 1
            if bool(target.get("must_include")) or bool(source.get("must_include"))
            else 0,
            "editorial_note": ArticleRepository._merge_editorial_notes(
                str(target.get("editorial_note") or ""),
                str(source.get("editorial_note") or ""),
            ),
            "duplicate_group": clean_text(str(target.get("duplicate_group") or ""))
            or clean_text(str(source.get("duplicate_group") or "")),
            "duplicate_of": target.get("duplicate_of"),
            "duplicate_reason": clean_text(str(target.get("duplicate_reason") or ""))
            or clean_text(str(source.get("duplicate_reason") or "")),
            "raw_payload": merged_raw_payload,
        }

    @staticmethod
    def _status_rank(value: str) -> int:
        return {
            "": 0,
            "pending": 1,
            "skipped": 2,
            "throttled": 3,
            "temporary_error": 4,
            "error": 4,
            "blocked": 5,
            "permanent_error": 6,
            "ready": 7,
        }.get(value, 0)

    @staticmethod
    def _best_status(left: str, right: str) -> str:
        return left if ArticleRepository._status_rank(left) >= ArticleRepository._status_rank(right) else right

    @staticmethod
    def _prefer_longer_text(left: str, right: str) -> str:
        return right if len(clean_text(right)) > len(clean_text(left)) else left

    @staticmethod
    def _min_text(left: str, right: str) -> str:
        values = [item for item in (left, right) if item]
        return min(values) if values else ""

    @staticmethod
    def _max_text(left: str, right: str) -> str:
        values = [item for item in (left, right) if item]
        return max(values) if values else ""

    @staticmethod
    def _max_int(left: int, right: int) -> int:
        return max(left, right)

    @staticmethod
    def _merge_editorial_notes(left: str, right: str) -> str:
        left_clean = left.strip()
        right_clean = right.strip()
        if not left_clean:
            return right_clean
        if not right_clean or left_clean == right_clean:
            return left_clean
        return f"{left_clean}\n\n{right_clean}"

    @staticmethod
    def _merge_raw_payloads(
        target_payload: str,
        source_payload: str,
        *,
        resolved_url: str,
        original_url: str,
    ) -> Dict[str, object]:
        try:
            merged = json.loads(target_payload or "{}")
        except json.JSONDecodeError:
            merged = {}
        if not isinstance(merged, dict):
            merged = {}
        try:
            incoming = json.loads(source_payload or "{}")
        except json.JSONDecodeError:
            incoming = {}
        if not isinstance(incoming, dict):
            incoming = {}
        for key, value in incoming.items():
            merged.setdefault(key, value)
        if original_url and original_url != resolved_url:
            merged.setdefault("original_link", incoming.get("original_link") or original_url)
            merged["resolved_link"] = resolved_url
            merged["link_resolution"] = "google_news"
        merged["link"] = resolved_url
        return merged

    def mark_article_extraction_error(
        self,
        article_id: int,
        *,
        error: str,
    ) -> Optional[dict]:
        return self.mark_article_extraction_failure(
            article_id,
            error=error,
            status="error",
            error_category="temporary_error",
        )

    def mark_article_extraction_skipped(
        self,
        article_id: int,
        *,
        error: str,
    ) -> Optional[dict]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE articles
                SET
                    extraction_status = 'skipped',
                    extraction_error = ?,
                    extraction_updated_at = ?,
                    extraction_attempts = extraction_attempts + 1,
                    extraction_last_http_status = 0,
                    extraction_next_retry_at = '',
                    extraction_error_category = ''
                WHERE id = ?
                """,
                (
                    error,
                    utc_now().isoformat(),
                    article_id,
                ),
            )
        return self.get_article(article_id)

    def save_article_enrichment(
        self,
        article_id: int,
        enrichment: ArticleEnrichment,
    ) -> Optional[dict]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE articles
                SET
                    llm_title_zh = ?,
                    llm_summary_zh = ?,
                    llm_brief_zh = ?,
                    llm_status = 'ready',
                    llm_provider = ?,
                    llm_model = ?,
                    llm_error = '',
                    llm_updated_at = ?
                WHERE id = ?
                """,
                (
                    enrichment.title_zh,
                    enrichment.summary_zh,
                    enrichment.importance_zh,
                    enrichment.provider,
                    enrichment.model,
                    utc_now().isoformat(),
                    article_id,
                ),
            )
        return self.get_article(article_id)

    def mark_article_enrichment_error(
        self,
        article_id: int,
        *,
        provider: str,
        model: str,
        error: str,
    ) -> Optional[dict]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE articles
                SET
                    llm_status = 'error',
                    llm_provider = ?,
                    llm_model = ?,
                    llm_error = ?,
                    llm_updated_at = ?
                WHERE id = ?
                """,
                (
                    provider,
                    model,
                    error,
                    utc_now().isoformat(),
                    article_id,
                ),
            )
        return self.get_article(article_id)

    def update_article_curation(
        self,
        article_id: int,
        *,
        is_hidden: Optional[bool] = None,
        is_pinned: Optional[bool] = None,
        is_suppressed: Optional[bool] = None,
        must_include: Optional[bool] = None,
        editorial_note: Optional[str] = None,
    ) -> Optional[dict]:
        updates: List[str] = []
        params: List[object] = []

        if is_hidden is not None:
            updates.append("is_hidden = ?")
            params.append(1 if is_hidden else 0)

        if is_pinned is not None:
            updates.append("is_pinned = ?")
            params.append(1 if is_pinned else 0)

        if is_suppressed is not None:
            updates.append("is_suppressed = ?")
            params.append(1 if is_suppressed else 0)

        if must_include is not None:
            updates.append("must_include = ?")
            params.append(1 if must_include else 0)

        if editorial_note is not None:
            updates.append("editorial_note = ?")
            params.append(editorial_note)

        if not updates:
            return self.get_article(article_id)

        params.append(article_id)

        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE articles
                SET {", ".join(updates)}
                WHERE id = ?
                """,
                params,
            )
        return self.get_article(article_id)

    def set_duplicate_primary(self, article_id: int) -> Optional[dict]:
        article = self.get_article(article_id)
        if article is None:
            return None
        group_id = clean_text(str(article.get("duplicate_group") or "")) or self._duplicate_group_id(
            int(article["id"])
        )
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM articles WHERE duplicate_group = ? ORDER BY id ASC",
                (group_id,),
            ).fetchall()
            member_ids = [int(row["id"]) for row in rows] or [int(article["id"])]
            for member_id in member_ids:
                connection.execute(
                    """
                    UPDATE articles
                    SET
                        duplicate_group = ?,
                        duplicate_of = ?,
                        duplicate_reason = CASE
                            WHEN id = ? THEN ''
                            ELSE 'operator_selected_primary'
                        END
                    WHERE id = ?
                    """,
                    (
                        group_id,
                        None if member_id == article_id else article_id,
                        article_id,
                        member_id,
                    ),
                )
        return self.get_article(article_id)

    def save_digest(
        self,
        *,
        region: str,
        since_hours: int,
        digest: DailyDigest,
        body_markdown: str,
        article_count: int,
        source_count: int,
        payload: Optional[dict] = None,
    ) -> dict:
        generated_at = utc_now().isoformat()
        stored_payload = payload or digest.to_dict()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO digests (
                    region,
                    since_hours,
                    title,
                    body_markdown,
                    provider,
                    model,
                    article_count,
                    source_count,
                    generated_at,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    region,
                    since_hours,
                    digest.title,
                    body_markdown,
                    digest.provider,
                    digest.model,
                    article_count,
                    source_count,
                    generated_at,
                    json.dumps(stored_payload, ensure_ascii=False),
                ),
            )
            digest_id = int(cursor.lastrowid)

        return self.get_digest(digest_id) or {}

    def get_digest(self, digest_id: int) -> Optional[dict]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    region,
                    since_hours,
                    title,
                    body_markdown,
                    provider,
                    model,
                    article_count,
                    source_count,
                    generated_at,
                    payload
                FROM digests
                WHERE id = ?
                LIMIT 1
                """,
                (digest_id,),
            ).fetchone()
        return self._row_to_digest_dict(row) if row else None

    def update_digest(
        self,
        digest_id: int,
        *,
        title: str,
        body_markdown: str,
        provider: str,
        model: str,
        article_count: int,
        source_count: int,
        payload: Dict[str, object],
    ) -> Optional[dict]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE digests
                SET
                    title = ?,
                    body_markdown = ?,
                    provider = ?,
                    model = ?,
                    article_count = ?,
                    source_count = ?,
                    payload = ?
                WHERE id = ?
                """,
                (
                    title,
                    body_markdown,
                    provider,
                    model,
                    article_count,
                    source_count,
                    json.dumps(payload, ensure_ascii=False),
                    digest_id,
                ),
            )
        return self.get_digest(digest_id)

    def list_digests(
        self,
        *,
        region: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        clauses = []
        params: List[object] = []

        if region and region != "all":
            clauses.append("region = ?")
            params.append(region)

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    region,
                    since_hours,
                    title,
                    body_markdown,
                    provider,
                    model,
                    article_count,
                    source_count,
                    generated_at,
                    payload
                FROM digests
                {where_sql}
                ORDER BY generated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_digest_dict(row) for row in rows]

    @staticmethod
    def _row_to_digest_dict(row: sqlite3.Row) -> Dict[str, object]:
        payload = dict(row)
        payload["payload"] = json.loads(payload["payload"])
        return payload

    def save_publication(
        self,
        *,
        digest_id: Optional[int],
        target: str,
        status: str,
        external_id: str = "",
        message: str = "",
        response_payload: Optional[Dict[str, object]] = None,
    ) -> dict:
        created_at = utc_now().isoformat()
        updated_at = created_at
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO publications (
                    digest_id,
                    target,
                    status,
                    external_id,
                    message,
                    response_payload,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    digest_id,
                    target,
                    status,
                    external_id,
                    message,
                    json.dumps(response_payload or {}, ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )
            publication_id = int(cursor.lastrowid)
        return self.get_publication(publication_id) or {}

    def update_publication(
        self,
        publication_id: int,
        *,
        status: Optional[str] = None,
        external_id: Optional[str] = None,
        message: Optional[str] = None,
        response_payload: Optional[Dict[str, object]] = None,
    ) -> Optional[dict]:
        updates: List[str] = ["updated_at = ?"]
        params: List[object] = [utc_now().isoformat()]

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if external_id is not None:
            updates.append("external_id = ?")
            params.append(external_id)

        if message is not None:
            updates.append("message = ?")
            params.append(message)

        if response_payload is not None:
            updates.append("response_payload = ?")
            params.append(json.dumps(response_payload, ensure_ascii=False))

        params.append(publication_id)
        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE publications
                SET {", ".join(updates)}
                WHERE id = ?
                """,
                params,
            )
        return self.get_publication(publication_id)

    def get_publication(self, publication_id: int) -> Optional[dict]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    digest_id,
                    target,
                    status,
                    external_id,
                    message,
                    response_payload,
                    created_at,
                    updated_at
                FROM publications
                WHERE id = ?
                LIMIT 1
                """,
                (publication_id,),
            ).fetchone()
        return self._row_to_publication_dict(row) if row else None

    def list_publications(
        self,
        *,
        publication_ids: Optional[Iterable[int]] = None,
        digest_id: Optional[int] = None,
        target: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        clauses = []
        params: List[object] = []
        publication_id_list = list(publication_ids or [])
        if publication_id_list:
            placeholders = ",".join("?" for _ in publication_id_list)
            clauses.append(f"id IN ({placeholders})")
            params.extend(publication_id_list)
        if digest_id is not None:
            clauses.append("digest_id = ?")
            params.append(digest_id)
        if target:
            clauses.append("target = ?")
            params.append(target)
        if status:
            clauses.append("status = ?")
            params.append(status)

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    digest_id,
                    target,
                    status,
                    external_id,
                    message,
                    response_payload,
                    created_at,
                    updated_at
                FROM publications
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_publication_dict(row) for row in rows]

    def get_latest_publication(
        self,
        *,
        digest_id: int,
        target: str,
        statuses: Optional[Iterable[str]] = None,
    ) -> Optional[dict]:
        clauses = ["digest_id = ?", "target = ?"]
        params: List[object] = [digest_id, target]

        status_list = [str(item) for item in (statuses or []) if str(item)]
        if status_list:
            placeholders = ",".join("?" for _ in status_list)
            clauses.append(f"status IN ({placeholders})")
            params.extend(status_list)

        where_sql = " AND ".join(clauses)
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT
                    id,
                    digest_id,
                    target,
                    status,
                    external_id,
                    message,
                    response_payload,
                    created_at,
                    updated_at
                FROM publications
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT 1
                """,
                params,
            ).fetchone()
        return self._row_to_publication_dict(row) if row else None

    @staticmethod
    def _row_to_publication_dict(row: sqlite3.Row) -> Dict[str, object]:
        payload = dict(row)
        payload["response_payload"] = json.loads(payload["response_payload"])
        return payload

    def get_schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM meta WHERE key = 'schema_version' LIMIT 1"
            ).fetchone()
        if not row:
            return 0
        return int(row["value"])

    def get_stats(self) -> Dict[str, object]:
        with self._connect() as connection:
            totals_row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_articles,
                    SUM(CASE WHEN is_hidden = 0 THEN 1 ELSE 0 END) AS visible_articles,
                    SUM(CASE WHEN is_hidden = 1 THEN 1 ELSE 0 END) AS hidden_articles,
                    SUM(CASE WHEN is_pinned = 1 THEN 1 ELSE 0 END) AS pinned_articles,
                    SUM(CASE WHEN is_suppressed = 1 THEN 1 ELSE 0 END) AS suppressed_articles,
                    SUM(CASE WHEN must_include = 1 THEN 1 ELSE 0 END) AS must_include_articles,
                    SUM(CASE WHEN duplicate_of IS NULL THEN 1 ELSE 0 END) AS unique_articles,
                    SUM(CASE WHEN duplicate_of IS NOT NULL THEN 1 ELSE 0 END) AS duplicate_articles,
                    SUM(CASE WHEN extraction_status = 'ready' THEN 1 ELSE 0 END) AS extracted_articles,
                    SUM(CASE WHEN extraction_status = 'skipped' THEN 1 ELSE 0 END) AS skipped_extractions,
                    SUM(CASE WHEN extraction_status IN ('error', 'throttled', 'blocked', 'temporary_error', 'permanent_error') THEN 1 ELSE 0 END) AS extraction_errors,
                    SUM(CASE WHEN extraction_status = 'throttled' THEN 1 ELSE 0 END) AS throttled_extractions,
                    SUM(CASE WHEN extraction_status = 'blocked' THEN 1 ELSE 0 END) AS blocked_extractions,
                    SUM(CASE WHEN extraction_status IN ('error', 'temporary_error') THEN 1 ELSE 0 END) AS temporary_extraction_errors,
                    SUM(CASE WHEN extraction_status = 'permanent_error' THEN 1 ELSE 0 END) AS permanent_extraction_errors,
                    SUM(CASE WHEN extraction_next_retry_at != '' AND extraction_next_retry_at > ? THEN 1 ELSE 0 END) AS scheduled_extraction_retries,
                    SUM(CASE WHEN llm_status = 'ready' THEN 1 ELSE 0 END) AS enriched_articles,
                    SUM(CASE WHEN llm_status = 'error' THEN 1 ELSE 0 END) AS llm_errors
                FROM articles
                """,
                (utc_now().isoformat(),),
            ).fetchone()
            digest_row = connection.execute(
                "SELECT COUNT(*) AS total_digests FROM digests"
            ).fetchone()
            publication_row = connection.execute(
                "SELECT COUNT(*) AS total_publications FROM publications"
            ).fetchone()
            publication_status_rows = connection.execute(
                """
                SELECT status, COUNT(*) AS total
                FROM publications
                GROUP BY status
                ORDER BY total DESC
                """
            ).fetchall()
            region_rows = connection.execute(
                """
                SELECT region, COUNT(*) AS total
                FROM articles
                GROUP BY region
                ORDER BY total DESC
                """
            ).fetchall()
            extraction_status_rows = connection.execute(
                """
                SELECT extraction_status AS status, COUNT(*) AS total
                FROM articles
                GROUP BY extraction_status
                ORDER BY total DESC
                """
            ).fetchall()
            extraction_category_rows = connection.execute(
                """
                SELECT extraction_error_category AS category, COUNT(*) AS total
                FROM articles
                WHERE extraction_error_category != ''
                GROUP BY extraction_error_category
                ORDER BY total DESC
                """
            ).fetchall()
            source_state_row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_source_states,
                    SUM(CASE WHEN cooldown_until != '' AND cooldown_until > ? THEN 1 ELSE 0 END) AS active_source_cooldowns,
                    SUM(CASE WHEN cooldown_status = 'throttled' AND cooldown_until > ? THEN 1 ELSE 0 END) AS throttled_source_cooldowns,
                    SUM(CASE WHEN cooldown_status = 'blocked' AND cooldown_until > ? THEN 1 ELSE 0 END) AS blocked_source_cooldowns,
                    SUM(CASE WHEN silenced_until != '' AND silenced_until > ? THEN 1 ELSE 0 END) AS silenced_source_alerts,
                    SUM(CASE WHEN maintenance_mode = 1 THEN 1 ELSE 0 END) AS sources_in_maintenance
                FROM source_states
                """,
                (
                    utc_now().isoformat(),
                    utc_now().isoformat(),
                    utc_now().isoformat(),
                    utc_now().isoformat(),
                ),
            ).fetchone()
            source_cooldown_rows = connection.execute(
                """
                SELECT
                    source_id,
                    source_name,
                    cooldown_status,
                    cooldown_until,
                    consecutive_failures,
                    consecutive_successes,
                    last_error_category,
                    last_http_status,
                    last_error_at,
                    last_success_at,
                    last_recovered_at,
                    silenced_until,
                    maintenance_mode,
                    acknowledged_at,
                    ack_note,
                    updated_at
                FROM source_states
                WHERE cooldown_until != '' AND cooldown_until > ?
                ORDER BY cooldown_until DESC, updated_at DESC
                LIMIT 20
                """,
                (utc_now().isoformat(),),
            ).fetchall()
            duplicate_group_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM (
                    SELECT duplicate_group
                    FROM articles
                    WHERE duplicate_group != ''
                    GROUP BY duplicate_group
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()
        publication_status_counts = {
            str(row["status"]): int(row["total"] or 0) for row in publication_status_rows
        }
        extraction_status_counts = {
            str(row["status"]): int(row["total"] or 0) for row in extraction_status_rows
        }
        extraction_error_categories = {
            str(row["category"]): int(row["total"] or 0) for row in extraction_category_rows
        }
        source_cooldowns = [self._row_to_source_state_dict(row) for row in source_cooldown_rows]

        return {
            "schema_version": self.get_schema_version(),
            "total_articles": int(totals_row["total_articles"] or 0),
            "visible_articles": int(totals_row["visible_articles"] or 0),
            "hidden_articles": int(totals_row["hidden_articles"] or 0),
            "pinned_articles": int(totals_row["pinned_articles"] or 0),
            "suppressed_articles": int(totals_row["suppressed_articles"] or 0),
            "must_include_articles": int(totals_row["must_include_articles"] or 0),
            "unique_articles": int(totals_row["unique_articles"] or 0),
            "duplicate_articles": int(totals_row["duplicate_articles"] or 0),
            "duplicate_groups": int(duplicate_group_row["total"] or 0),
            "extracted_articles": int(totals_row["extracted_articles"] or 0),
            "skipped_extractions": int(totals_row["skipped_extractions"] or 0),
            "extraction_errors": int(totals_row["extraction_errors"] or 0),
            "throttled_extractions": int(totals_row["throttled_extractions"] or 0),
            "blocked_extractions": int(totals_row["blocked_extractions"] or 0),
            "temporary_extraction_errors": int(totals_row["temporary_extraction_errors"] or 0),
            "permanent_extraction_errors": int(totals_row["permanent_extraction_errors"] or 0),
            "scheduled_extraction_retries": int(totals_row["scheduled_extraction_retries"] or 0),
            "extraction_status_counts": extraction_status_counts,
            "extraction_error_categories": extraction_error_categories,
            "enriched_articles": int(totals_row["enriched_articles"] or 0),
            "llm_errors": int(totals_row["llm_errors"] or 0),
            "total_digests": int(digest_row["total_digests"] or 0),
            "total_publications": int(publication_row["total_publications"] or 0),
            "publication_status_counts": publication_status_counts,
            "pending_publications": int(publication_status_counts.get("pending", 0)),
            "publication_errors": int(publication_status_counts.get("error", 0)),
            "total_source_states": int(source_state_row["total_source_states"] or 0),
            "active_source_cooldowns": int(source_state_row["active_source_cooldowns"] or 0),
            "throttled_source_cooldowns": int(source_state_row["throttled_source_cooldowns"] or 0),
            "blocked_source_cooldowns": int(source_state_row["blocked_source_cooldowns"] or 0),
            "silenced_source_alerts": int(source_state_row["silenced_source_alerts"] or 0),
            "sources_in_maintenance": int(source_state_row["sources_in_maintenance"] or 0),
            "source_cooldowns": source_cooldowns,
            "counts_by_region": {
                str(row["region"]): int(row["total"] or 0) for row in region_rows
            },
        }

    def count_articles(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM articles").fetchone()
        return int(row["total"])

    @staticmethod
    def _build_article_filters(
        *,
        region: Optional[str],
        language: Optional[str],
        source_id: Optional[str],
        article_ids: Optional[Iterable[int]],
        duplicate_group: Optional[str],
        primary_only: bool,
        since_hours: Optional[int],
        extraction_status: Optional[str],
        extraction_error_category: Optional[str],
        due_only: bool,
        include_hidden: bool,
    ) -> Tuple[str, List[object]]:
        clauses = []
        params: List[object] = []

        if not include_hidden:
            clauses.append("articles.is_hidden = 0")

        if region and region != "all":
            clauses.append("articles.region = ?")
            params.append(region)

        if language:
            clauses.append("articles.language = ?")
            params.append(language)

        if source_id:
            clauses.append("articles.source_id = ?")
            params.append(source_id)

        article_id_list = [int(item) for item in (article_ids or [])]
        if article_id_list:
            placeholders = ",".join("?" for _ in article_id_list)
            clauses.append(f"articles.id IN ({placeholders})")
            params.extend(article_id_list)

        if duplicate_group:
            clauses.append("articles.duplicate_group = ?")
            params.append(duplicate_group)

        if primary_only:
            clauses.append("articles.duplicate_of IS NULL")

        if since_hours:
            clauses.append("articles.published_at >= ?")
            params.append((utc_now() - timedelta(hours=since_hours)).isoformat())

        if extraction_status:
            clauses.append("articles.extraction_status = ?")
            params.append(extraction_status)

        if extraction_error_category:
            clauses.append("articles.extraction_error_category = ?")
            params.append(extraction_error_category)

        if due_only:
            retry_clause, retry_params = ArticleRepository._build_retry_due_filter()
            clauses.append(retry_clause)
            params.extend(retry_params)

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)
        return where_sql, params

    @staticmethod
    def _build_retry_due_filter() -> Tuple[str, List[object]]:
        return (
            """
            (
                articles.extraction_status IN ('error', 'throttled', 'blocked', 'temporary_error')
                AND (
                    articles.extraction_next_retry_at = ''
                    OR articles.extraction_next_retry_at <= ?
                )
            )
            """,
            [utc_now().isoformat()],
        )
