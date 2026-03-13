from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CrawlerSettings:
    env: str
    database_url: str | None
    marathon_event_table: str
    raw_data_table: str
    raw_done_retention_days: int | None
    raw_error_retention_days: int | None
    log_level: str


def load_settings() -> CrawlerSettings:
    project_root = Path(__file__).resolve().parents[2]
    protected_keys = set(os.environ.keys())

    _load_dotenv(
        dotenv_path=project_root / ".env",
        protected_keys=protected_keys,
        allow_override=False,
    )
    env_name = (os.getenv("CRAWLER_ENV") or "local").strip().lower()
    _load_dotenv(
        dotenv_path=project_root / f".env.{env_name}",
        protected_keys=protected_keys,
        allow_override=True,
    )

    database_url = os.getenv("CRAWLER_DATABASE_URL") or os.getenv("DATABASE_URL")
    marathon_event_table = os.getenv("CRAWLER_MARATHON_EVENT_TABLE", "marathon_event")
    raw_data_table = os.getenv("CRAWLER_RAW_DATA_TABLE", "raw_crawled_data")
    raw_done_retention_days = _parse_retention_days(
        os.getenv("CRAWLER_RAW_DONE_RETENTION_DAYS"),
        default_days=30,
    )
    raw_error_retention_days = _parse_retention_days(
        os.getenv("CRAWLER_RAW_ERROR_RETENTION_DAYS"),
        default_days=90,
    )
    log_level = os.getenv("CRAWLER_LOG_LEVEL", "INFO").strip().upper()

    return CrawlerSettings(
        env=env_name,
        database_url=database_url,
        marathon_event_table=marathon_event_table,
        raw_data_table=raw_data_table,
        raw_done_retention_days=raw_done_retention_days,
        raw_error_retention_days=raw_error_retention_days,
        log_level=log_level,
    )


def _load_dotenv(
    dotenv_path: Path,
    protected_keys: set[str],
    allow_override: bool,
) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if not key:
            continue
        if key in protected_keys:
            continue
        if allow_override or key not in os.environ:
            os.environ[key] = value


def _parse_retention_days(raw_value: str | None, *, default_days: int) -> int | None:
    if raw_value is None or not raw_value.strip():
        return default_days

    try:
        parsed = int(raw_value)
    except ValueError:
        return default_days

    if parsed <= 0:
        return None
    return parsed
