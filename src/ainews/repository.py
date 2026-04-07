from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .models import ArticleEnrichment, ArticleRecord, DailyDigest
from .utils import utc_now

ARTICLE_EXTRA_COLUMNS = {
    "extracted_text": "TEXT NOT NULL DEFAULT ''",
    "extraction_status": "TEXT NOT NULL DEFAULT 'pending'",
    "extraction_error": "TEXT NOT NULL DEFAULT ''",
    "extraction_updated_at": "TEXT NOT NULL DEFAULT ''",
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
    "editorial_note": "TEXT NOT NULL DEFAULT ''"
}

PUBLICATION_EXTRA_COLUMNS = {
    "updated_at": "TEXT NOT NULL DEFAULT ''",
}

CURRENT_SCHEMA_VERSION = 3


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
                    raw_payload TEXT NOT NULL,
                    extracted_text TEXT NOT NULL DEFAULT '',
                    extraction_status TEXT NOT NULL DEFAULT 'pending',
                    extraction_error TEXT NOT NULL DEFAULT '',
                    extraction_updated_at TEXT NOT NULL DEFAULT '',
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
                """
            )
            self._ensure_article_migrations(connection)
            self._ensure_publication_migrations(connection)
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

                CREATE INDEX IF NOT EXISTS idx_articles_pinned_published_at
                    ON articles(is_pinned, published_at);

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

    @staticmethod
    def _row_to_article_dict(row: sqlite3.Row) -> Dict[str, object]:
        payload = dict(row)
        payload["is_hidden"] = bool(payload.get("is_hidden"))
        payload["is_pinned"] = bool(payload.get("is_pinned"))
        return payload

    def insert_if_new(self, article: ArticleRecord, dedup_window_hours: int = 72) -> bool:
        threshold = (utc_now() - timedelta(hours=dedup_window_hours)).isoformat()

        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM articles
                WHERE canonical_url = ?
                   OR content_hash = ?
                   OR (dedup_key = ? AND published_at >= ?)
                LIMIT 1
                """,
                (
                    article.canonical_url,
                    article.content_hash,
                    article.dedup_key,
                    threshold,
                ),
            ).fetchone()

            if existing is not None:
                return False

            connection.execute(
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
                    raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.source_id,
                    article.source_name,
                    article.title,
                    article.url,
                    article.canonical_url,
                    article.summary,
                    article.published_at.isoformat(),
                    article.discovered_at.isoformat(),
                    article.language,
                    article.region,
                    article.country,
                    article.topic,
                    article.content_hash,
                    article.dedup_key,
                    json.dumps(article.raw_payload, ensure_ascii=False),
                ),
            )
        return True

    def list_articles(
        self,
        *,
        region: Optional[str] = None,
        language: Optional[str] = None,
        source_id: Optional[str] = None,
        since_hours: Optional[int] = None,
        limit: int = 50,
        include_hidden: bool = False,
    ) -> List[dict]:
        where_sql, params = self._build_article_filters(
            region=region,
            language=language,
            source_id=source_id,
            since_hours=since_hours,
            include_hidden=include_hidden,
        )
        params.append(limit)

        query = f"""
            SELECT
                id,
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
                extracted_text,
                extraction_status,
                extraction_error,
                extraction_updated_at,
                llm_title_zh,
                llm_summary_zh,
                llm_brief_zh,
                llm_status,
                llm_provider,
                llm_model,
                llm_error,
                llm_updated_at,
                is_hidden,
                is_pinned,
                editorial_note
            FROM articles
            {where_sql}
            ORDER BY is_pinned DESC, published_at DESC
            LIMIT ?
        """

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_article_dict(row) for row in rows]

    def get_article(self, article_id: int) -> Optional[dict]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
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
                    extracted_text,
                    extraction_status,
                    extraction_error,
                    extraction_updated_at,
                    llm_title_zh,
                    llm_summary_zh,
                    llm_brief_zh,
                    llm_status,
                    llm_provider,
                    llm_model,
                    llm_error,
                    llm_updated_at,
                    is_hidden,
                    is_pinned,
                    editorial_note
                FROM articles
                WHERE id = ?
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
        clauses = ["is_hidden = 0", "language NOT LIKE 'zh%'"]
        params: List[object] = []

        source_list = list(source_ids or [])
        if source_list:
            placeholders = ",".join("?" for _ in source_list)
            clauses.append(f"source_id IN ({placeholders})")
            params.extend(source_list)

        article_list = list(article_ids or [])
        if article_list:
            placeholders = ",".join("?" for _ in article_list)
            clauses.append(f"id IN ({placeholders})")
            params.extend(article_list)

        if since_hours:
            clauses.append("published_at >= ?")
            params.append((utc_now() - timedelta(hours=since_hours)).isoformat())

        if not force:
            clauses.append(
                "(llm_status != 'ready' OR llm_title_zh = '' OR llm_summary_zh = '' OR llm_brief_zh = '')"
            )

        params.append(limit)
        where_sql = "WHERE " + " AND ".join(clauses)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
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
                    extracted_text,
                    extraction_status,
                    extraction_error,
                    extraction_updated_at,
                    llm_title_zh,
                    llm_summary_zh,
                    llm_brief_zh,
                    llm_status,
                    llm_provider,
                    llm_model,
                    llm_error,
                    llm_updated_at,
                    is_hidden,
                    is_pinned,
                    editorial_note
                FROM articles
                {where_sql}
                ORDER BY is_pinned DESC, published_at DESC
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
        limit: int = 20,
        force: bool = False,
    ) -> List[dict]:
        clauses = ["is_hidden = 0"]
        params: List[object] = []

        source_list = list(source_ids or [])
        if source_list:
            placeholders = ",".join("?" for _ in source_list)
            clauses.append(f"source_id IN ({placeholders})")
            params.extend(source_list)

        article_list = list(article_ids or [])
        if article_list:
            placeholders = ",".join("?" for _ in article_list)
            clauses.append(f"id IN ({placeholders})")
            params.extend(article_list)

        if since_hours:
            clauses.append("published_at >= ?")
            params.append((utc_now() - timedelta(hours=since_hours)).isoformat())

        if not force:
            clauses.append("(extraction_status != 'ready' OR extracted_text = '')")

        params.append(limit)
        where_sql = "WHERE " + " AND ".join(clauses)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
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
                    extracted_text,
                    extraction_status,
                    extraction_error,
                    extraction_updated_at,
                    llm_title_zh,
                    llm_summary_zh,
                    llm_brief_zh,
                    llm_status,
                    llm_provider,
                    llm_model,
                    llm_error,
                    llm_updated_at,
                    is_hidden,
                    is_pinned,
                    editorial_note
                FROM articles
                {where_sql}
                ORDER BY is_pinned DESC, published_at DESC
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
                    extraction_updated_at = ?
                WHERE id = ?
                """,
                (
                    extracted_text,
                    utc_now().isoformat(),
                    article_id,
                ),
            )
        return self.get_article(article_id)

    def mark_article_extraction_error(
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
                    extraction_status = 'error',
                    extraction_error = ?,
                    extraction_updated_at = ?
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

    def save_digest(
        self,
        *,
        region: str,
        since_hours: int,
        digest: DailyDigest,
        body_markdown: str,
        article_count: int,
        source_count: int,
    ) -> dict:
        generated_at = utc_now().isoformat()
        payload = digest.to_dict()

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
                    json.dumps(payload, ensure_ascii=False),
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
                    SUM(CASE WHEN extraction_status = 'ready' THEN 1 ELSE 0 END) AS extracted_articles,
                    SUM(CASE WHEN extraction_status = 'error' THEN 1 ELSE 0 END) AS extraction_errors,
                    SUM(CASE WHEN llm_status = 'ready' THEN 1 ELSE 0 END) AS enriched_articles,
                    SUM(CASE WHEN llm_status = 'error' THEN 1 ELSE 0 END) AS llm_errors
                FROM articles
                """
            ).fetchone()
            digest_row = connection.execute(
                "SELECT COUNT(*) AS total_digests FROM digests"
            ).fetchone()
            publication_row = connection.execute(
                "SELECT COUNT(*) AS total_publications FROM publications"
            ).fetchone()
            region_rows = connection.execute(
                """
                SELECT region, COUNT(*) AS total
                FROM articles
                GROUP BY region
                ORDER BY total DESC
                """
            ).fetchall()

        return {
            "schema_version": self.get_schema_version(),
            "total_articles": int(totals_row["total_articles"] or 0),
            "visible_articles": int(totals_row["visible_articles"] or 0),
            "hidden_articles": int(totals_row["hidden_articles"] or 0),
            "pinned_articles": int(totals_row["pinned_articles"] or 0),
            "extracted_articles": int(totals_row["extracted_articles"] or 0),
            "extraction_errors": int(totals_row["extraction_errors"] or 0),
            "enriched_articles": int(totals_row["enriched_articles"] or 0),
            "llm_errors": int(totals_row["llm_errors"] or 0),
            "total_digests": int(digest_row["total_digests"] or 0),
            "total_publications": int(publication_row["total_publications"] or 0),
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
        since_hours: Optional[int],
        include_hidden: bool,
    ) -> Tuple[str, List[object]]:
        clauses = []
        params: List[object] = []

        if not include_hidden:
            clauses.append("is_hidden = 0")

        if region and region != "all":
            clauses.append("region = ?")
            params.append(region)

        if language:
            clauses.append("language = ?")
            params.append(language)

        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)

        if since_hours:
            clauses.append("published_at >= ?")
            params.append((utc_now() - timedelta(hours=since_hours)).isoformat())

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)
        return where_sql, params
