from __future__ import annotations

from urllib.parse import urlparse

import psycopg


def assert_postgres_healthy(dsn: str, *, connect_timeout_seconds: int) -> None:
    with psycopg.connect(dsn, connect_timeout=connect_timeout_seconds) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()

    if row is None or row[0] != 1:
        raise RuntimeError(f"DB 헬스체크 실패: {redact_dsn(dsn)}")


def redact_dsn(dsn: str) -> str:
    parsed = urlparse(dsn)
    host = parsed.hostname or "unknown-host"
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") or "unknown-db"
    scheme = parsed.scheme or "postgresql"
    return f"{scheme}://{host}:{port}/{database}"
