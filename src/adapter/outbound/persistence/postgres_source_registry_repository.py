from __future__ import annotations

import psycopg
from psycopg.sql import Identifier, SQL

from domain.model.source_registry import SourceCrawlResult, SourceRegistrySeed
from port.outbound.source_registry_port import SourceRegistryPort


class PostgresSourceRegistryRepository(SourceRegistryPort):
    def __init__(self, dsn: str, table_name: str = "crawler_source_registry") -> None:
        self._dsn = dsn
        self._table_name = table_name

    def upsert_sources(self, sources: list[SourceRegistrySeed]) -> int:
        if not sources:
            return 0

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                self._ensure_table(cur)
                query = SQL(
                    """
                    INSERT INTO {table} (
                        source_name,
                        source_url,
                        source_kind,
                        enabled
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (source_name)
                    DO UPDATE SET
                        source_url = EXCLUDED.source_url,
                        source_kind = EXCLUDED.source_kind,
                        enabled = EXCLUDED.enabled,
                        last_seen_at = NOW()
                    """
                ).format(table=Identifier(self._table_name))

                changed_count = 0
                for source in sources:
                    cur.execute(
                        query,
                        (
                            source.source_name,
                            source.source_url,
                            source.source_kind,
                            source.enabled,
                        ),
                    )
                    changed_count += cur.rowcount
            conn.commit()
        return changed_count

    def record_crawl_result(self, result: SourceCrawlResult) -> None:
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                self._ensure_table(cur)
                query = SQL(
                    """
                    INSERT INTO {table} (
                        source_name,
                        source_url,
                        source_kind,
                        enabled,
                        last_crawled_at,
                        last_success_at,
                        last_status,
                        last_event_count,
                        last_rare_event_count,
                        success_count,
                        fail_count,
                        last_error
                    )
                    VALUES (
                        %s, %s, %s, TRUE, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (source_name)
                    DO UPDATE SET
                        source_url = COALESCE(EXCLUDED.source_url, {table}.source_url),
                        last_seen_at = NOW(),
                        last_crawled_at = EXCLUDED.last_crawled_at,
                        last_success_at = EXCLUDED.last_success_at,
                        last_status = EXCLUDED.last_status,
                        last_event_count = EXCLUDED.last_event_count,
                        last_rare_event_count = EXCLUDED.last_rare_event_count,
                        success_count = {table}.success_count + EXCLUDED.success_count,
                        fail_count = {table}.fail_count + EXCLUDED.fail_count,
                        last_error = EXCLUDED.last_error
                    """
                ).format(table=Identifier(self._table_name))

                success_count = 1 if result.success else 0
                fail_count = 0 if result.success else 1
                status = "SUCCESS" if result.success else "FAILED"
                last_success_at = result.crawled_at_kst if result.success else None

                cur.execute(
                    query,
                    (
                        result.source_name,
                        result.source_url,
                        "UNKNOWN",
                        result.crawled_at_kst,
                        last_success_at,
                        status,
                        result.event_count,
                        result.rare_event_count,
                        success_count,
                        fail_count,
                        result.error_message,
                    ),
                )
            conn.commit()

    def _ensure_table(self, cur: psycopg.Cursor) -> None:
        query = SQL(
            """
            CREATE TABLE IF NOT EXISTS {table} (
                id BIGSERIAL PRIMARY KEY,
                source_name VARCHAR(100) NOT NULL UNIQUE,
                source_url TEXT,
                source_kind VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_crawled_at TIMESTAMPTZ,
                last_success_at TIMESTAMPTZ,
                last_status VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN',
                last_event_count INTEGER NOT NULL DEFAULT 0,
                last_rare_event_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                fail_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT
            )
            """
        ).format(table=Identifier(self._table_name))
        cur.execute(query)

        index_query = SQL(
            "CREATE INDEX IF NOT EXISTS {index_name} ON {table} (last_status, enabled)"
        ).format(
            index_name=Identifier(f"idx_{self._table_name}_status_enabled"),
            table=Identifier(self._table_name),
        )
        cur.execute(index_query)
