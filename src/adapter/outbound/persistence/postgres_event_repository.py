from __future__ import annotations

from dataclasses import asdict
import logging

import psycopg
from psycopg.sql import Identifier, SQL

from adapter.outbound.persistence.mapper.marathon_event_mapper import MarathonEventMapper
from domain.model.marathon_event import MarathonEvent
from port.outbound.event_store_port import EventStorePort

logger = logging.getLogger(__name__)


class PostgresEventRepository(EventStorePort):
    def __init__(self, dsn: str, table_name: str = "marathon_event") -> None:
        self._dsn = dsn
        self._table_name = table_name

    def upsert_events(self, events: list[MarathonEvent]) -> int:
        if not events:
            return 0

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                table_columns = self._load_table_columns(cur)
                required_columns = self._load_required_columns(cur)
                saved_count = 0
                skipped_required_count = 0

                for event in events:
                    row = MarathonEventMapper.to_row(event)
                    record = self._row_to_record(row, table_columns)
                    if not self._has_required_values(record, required_columns):
                        skipped_required_count += 1
                        continue

                    existing_id = self._find_existing_id(cur, record, table_columns)
                    if existing_id is None:
                        self._insert_event(cur, record)
                    else:
                        self._update_event(cur, existing_id, record)
                    saved_count += 1

            conn.commit()

        if skipped_required_count > 0:
            logger.warning(
                "필수 필드 누락으로 이벤트 저장 건너뜀",
                extra={"skipped_count": skipped_required_count},
            )

        return saved_count

    def _load_table_columns(self, cur: psycopg.Cursor) -> set[str]:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = %s
            """,
            (self._table_name,),
        )
        columns = {row[0] for row in cur.fetchall()}
        if not columns:
            raise RuntimeError(f"Table not found in current schema: {self._table_name}")
        return columns

    def _load_required_columns(self, cur: psycopg.Cursor) -> set[str]:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = %s
              AND is_nullable = 'NO'
              AND column_default IS NULL
            """,
            (self._table_name,),
        )
        required = {row[0] for row in cur.fetchall()}
        required.discard("id")
        return required

    @staticmethod
    def _row_to_record(row, table_columns: set[str]) -> dict[str, object]:
        serialized = asdict(row)
        return {key: value for key, value in serialized.items() if key in table_columns}

    @staticmethod
    def _has_required_values(
        record: dict[str, object], required_columns: set[str]
    ) -> bool:
        for column in required_columns:
            value = record.get(column)
            if value is None:
                return False
        return True

    def _find_existing_id(
        self, cur: psycopg.Cursor, record: dict[str, object], table_columns: set[str]
    ) -> int | None:
        base_key_columns = ["title", "event_date"]
        if not all(col in table_columns for col in base_key_columns):
            return None

        title = record.get("title")
        event_date = record.get("event_date")
        link_url = record.get("link_url")

        if "link_url" in table_columns and link_url:
            query = SQL(
                """
                SELECT id
                FROM {table}
                WHERE title = %s
                  AND event_date = %s
                  AND COALESCE(link_url, '') = COALESCE(%s, '')
                LIMIT 1
                """
            ).format(table=Identifier(self._table_name))
            cur.execute(query, (title, event_date, link_url))
            row = cur.fetchone()
            if row:
                return row[0]

        if "region" not in table_columns:
            return None

        region = record.get("region")
        if region is None:
            return None

        query = SQL("SELECT id FROM {table} WHERE {where_clause} LIMIT 1").format(
            table=Identifier(self._table_name),
            where_clause=SQL(" AND ").join(
                SQL(part)
                for part in (
                    "title = %s",
                    "event_date = %s",
                    "region = %s",
                )
            ),
        )
        cur.execute(query, (title, event_date, region))
        row = cur.fetchone()
        return row[0] if row else None

    def _insert_event(self, cur: psycopg.Cursor, record: dict[str, object]) -> None:
        columns = list(record.keys())
        placeholders = SQL(", ").join(SQL("%s") for _ in columns)
        query = SQL("INSERT INTO {table} ({columns}) VALUES ({values})").format(
            table=Identifier(self._table_name),
            columns=SQL(", ").join(Identifier(col) for col in columns),
            values=placeholders,
        )
        cur.execute(query, [record[col] for col in columns])

    def _update_event(self, cur: psycopg.Cursor, row_id: int, record: dict[str, object]) -> None:
        update_columns = [col for col in record.keys() if col != "id"]
        if not update_columns:
            return

        query = SQL("UPDATE {table} SET {sets} WHERE id = %s").format(
            table=Identifier(self._table_name),
            sets=SQL(", ").join(
                SQL("{} = %s").format(Identifier(col)) for col in update_columns
            ),
        )
        params = [record[col] for col in update_columns]
        params.append(row_id)
        cur.execute(query, params)

