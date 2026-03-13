from __future__ import annotations

import psycopg
from psycopg.sql import Identifier, SQL
from psycopg.types.json import Jsonb

from port.outbound.raw_data_store_port import RawDataStorePort


class PostgresRawCrawledDataRepository(RawDataStorePort):
    def __init__(self, dsn: str, table_name: str = "raw_crawled_data") -> None:
        self._dsn = dsn
        self._table_name = table_name

    def save(
        self,
        *,
        source: str,
        payload: dict[str, object],
        parsed_status: str,
    ) -> None:
        query = SQL(
            "INSERT INTO {table} (source, payload, parsed_status) VALUES (%s, %s, %s)"
        ).format(table=Identifier(self._table_name))

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (source, Jsonb(payload), parsed_status))
            conn.commit()

    def prune(
        self,
        *,
        parsed_status: str,
        older_than_days: int,
    ) -> int:
        query = SQL(
            """
            DELETE FROM {table}
            WHERE parsed_status = %s
              AND created_at < NOW() - make_interval(days => %s)
            """
        ).format(table=Identifier(self._table_name))

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (parsed_status, older_than_days))
                deleted = cur.rowcount
            conn.commit()

        return deleted
