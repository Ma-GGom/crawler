from datetime import date

import psycopg
from psycopg.sql import Identifier, SQL

from domain.model.recurrence_watch import RecurrenceWatchSeed
from domain.rule.recurrence_watch_rule import build_recurrence_watch_candidates
from port.outbound.event_watch_port import EventWatchPort


class PostgresEventWatchRepository(EventWatchPort):
    def __init__(
        self,
        dsn: str,
        watch_table_name: str = "marathon_event_watch",
        seed_table_name: str = "marathon_event_watch_seed",
    ) -> None:
        self._dsn = dsn
        self._watch_table_name = watch_table_name
        self._seed_table_name = seed_table_name

    def save_seeds(self, seeds: list[RecurrenceWatchSeed]) -> int:
        if not seeds:
            return 0

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                self._ensure_seed_table(cur)
                upsert_query = SQL(
                    """
                    INSERT INTO {table} (
                        title,
                        event_date,
                        source_name,
                        source_url
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """
                ).format(table=Identifier(self._seed_table_name))

                saved_count = 0
                for seed in seeds:
                    cur.execute(
                        upsert_query,
                        (
                            seed.title,
                            seed.event_date,
                            seed.source_name,
                            seed.source_url,
                        ),
                    )
                    saved_count += cur.rowcount
            conn.commit()

        return saved_count

    def refresh_watchlist(self, *, today_kst: date) -> dict[str, int]:
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                self._ensure_seed_table(cur)
                self._ensure_watch_table(cur)
                seeds = self._load_recent_seeds(cur, today_kst=today_kst)
                candidates = build_recurrence_watch_candidates(
                    seeds,
                    today_kst=today_kst,
                )
                self._replace_candidates(cur, candidates)
            conn.commit()

        pending_count = sum(1 for item in candidates if item.status == "PENDING")
        detected_count = sum(1 for item in candidates if item.status == "DETECTED")
        return {
            "watch_total_count": len(candidates),
            "watch_pending_count": pending_count,
            "watch_detected_count": detected_count,
        }

    def _load_recent_seeds(
        self,
        cur: psycopg.Cursor,
        *,
        today_kst: date,
    ) -> list[RecurrenceWatchSeed]:
        previous_year_start = date(today_kst.year - 1, 1, 1)
        current_year_end = date(today_kst.year, 12, 31)

        query = SQL(
            """
            SELECT title, event_date, source_name, source_url
            FROM {table}
            WHERE event_date BETWEEN %s AND %s
            """
        ).format(table=Identifier(self._seed_table_name))
        cur.execute(query, (previous_year_start, current_year_end))

        seeds: list[RecurrenceWatchSeed] = []
        for row in cur.fetchall():
            title = row[0] or ""
            event_date = row[1]
            if not title or event_date is None:
                continue
            seeds.append(
                RecurrenceWatchSeed(
                    title=title,
                    event_date=event_date,
                    source_name=row[2],
                    source_url=row[3],
                )
            )
        return seeds

    def _replace_candidates(self, cur: psycopg.Cursor, candidates) -> None:
        delete_query = SQL("DELETE FROM {table}").format(
            table=Identifier(self._watch_table_name)
        )
        cur.execute(delete_query)

        if not candidates:
            return

        insert_query = SQL(
            """
            INSERT INTO {table} (
                watch_key,
                base_title,
                sample_title,
                last_event_date,
                expected_event_date,
                detected_event_date,
                status,
                source_name,
                source_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        ).format(table=Identifier(self._watch_table_name))

        for candidate in candidates:
            cur.execute(
                insert_query,
                (
                    candidate.watch_key,
                    candidate.base_title,
                    candidate.sample_title,
                    candidate.last_event_date,
                    candidate.expected_event_date,
                    candidate.detected_event_date,
                    candidate.status,
                    candidate.source_name,
                    candidate.source_url,
                ),
            )

    def _ensure_watch_table(self, cur: psycopg.Cursor) -> None:
        query = SQL(
            """
            CREATE TABLE IF NOT EXISTS {table} (
                id BIGSERIAL PRIMARY KEY,
                watch_key VARCHAR(255) NOT NULL UNIQUE,
                base_title VARCHAR(255) NOT NULL,
                sample_title VARCHAR(255) NOT NULL,
                last_event_date DATE NOT NULL,
                expected_event_date DATE NOT NULL,
                detected_event_date DATE,
                status VARCHAR(20) NOT NULL,
                source_name VARCHAR(100),
                source_url TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        ).format(table=Identifier(self._watch_table_name))
        cur.execute(query)

        index_query_one = SQL(
            "CREATE INDEX IF NOT EXISTS {index_name} ON {table} (status)"
        ).format(
            index_name=Identifier(f"idx_{self._watch_table_name}_status"),
            table=Identifier(self._watch_table_name),
        )
        cur.execute(index_query_one)

        index_query_two = SQL(
            "CREATE INDEX IF NOT EXISTS {index_name} ON {table} (expected_event_date)"
        ).format(
            index_name=Identifier(f"idx_{self._watch_table_name}_expected_event_date"),
            table=Identifier(self._watch_table_name),
        )
        cur.execute(index_query_two)

    def _ensure_seed_table(self, cur: psycopg.Cursor) -> None:
        query = SQL(
            """
            CREATE TABLE IF NOT EXISTS {table} (
                id BIGSERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                event_date DATE NOT NULL,
                source_name VARCHAR(100),
                source_url TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        ).format(table=Identifier(self._seed_table_name))
        cur.execute(query)

        unique_query = SQL(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
            ON {table} (title, event_date, COALESCE(source_name, ''), COALESCE(source_url, ''))
            """
        ).format(
            index_name=Identifier(f"uq_{self._seed_table_name}_dedup"),
            table=Identifier(self._seed_table_name),
        )
        cur.execute(unique_query)
