from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.persistence.postgres_health_checker import (
    assert_postgres_healthy,
    redact_dsn,
)


class _FakeCursor:
    def __init__(self, row: tuple[int] | None) -> None:
        self._row = row
        self.executed: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str) -> None:
        self.executed.append(query)

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self, row: tuple[int] | None) -> None:
        self._row = row
        self.cursor_instance = _FakeCursor(row=row)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self) -> _FakeCursor:
        return self.cursor_instance


class PostgresHealthCheckerTest(unittest.TestCase):
    def test_assert_postgres_healthy_success(self) -> None:
        connection = _FakeConnection(row=(1,))
        with patch(
            "adapter.outbound.persistence.postgres_health_checker.psycopg.connect",
            return_value=connection,
        ) as connect_mock:
            assert_postgres_healthy(
                "postgresql://user:pass@db.example.com:5432/maggom",
                connect_timeout_seconds=7,
            )

        connect_mock.assert_called_once_with(
            "postgresql://user:pass@db.example.com:5432/maggom",
            connect_timeout=7,
        )
        self.assertEqual(["SELECT 1"], connection.cursor_instance.executed)

    def test_assert_postgres_healthy_failure(self) -> None:
        connection = _FakeConnection(row=(0,))
        with patch(
            "adapter.outbound.persistence.postgres_health_checker.psycopg.connect",
            return_value=connection,
        ):
            with self.assertRaises(RuntimeError):
                assert_postgres_healthy(
                    "postgresql://user:pass@db.example.com:5432/maggom",
                    connect_timeout_seconds=5,
                )

    def test_redact_dsn(self) -> None:
        redacted = redact_dsn("postgresql://user:pass@db.example.com:5432/maggom")
        self.assertEqual("postgresql://db.example.com:5432/maggom", redacted)


if __name__ == "__main__":
    unittest.main()
