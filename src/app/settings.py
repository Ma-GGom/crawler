from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SourceEndpoint:
    source_name: str
    source_url: str


@dataclass(frozen=True, slots=True)
class CrawlerSettings:
    env: str
    database_url: str | None
    marathon_event_table: str
    event_watch_table: str
    event_watch_seed_table: str
    source_registry_table: str
    marathon_pe_source: SourceEndpoint
    onoffmix_source: SourceEndpoint
    chuncheon_notice_source: SourceEndpoint
    runnext_source: SourceEndpoint
    run1080_source: SourceEndpoint
    pokemon_run_source: SourceEndpoint
    jtbc_source: SourceEndpoint
    seoul_marathon_source: SourceEndpoint
    marathon_pe_detail_base_url: str
    onoffmix_base_url: str
    runnext_fallback_url: str
    run1080_mini_url_template: str
    run1080_event_url_template: str
    pokemon_run_official_url: str
    seoul_marathon_detail_url: str
    source_priority: dict[str, int]
    watch_seed_excluded_sources: set[str]
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
    event_watch_table = os.getenv("CRAWLER_EVENT_WATCH_TABLE", "marathon_event_watch")
    event_watch_seed_table = os.getenv(
        "CRAWLER_EVENT_WATCH_SEED_TABLE",
        "marathon_event_watch_seed",
    )
    source_registry_table = os.getenv(
        "CRAWLER_SOURCE_REGISTRY_TABLE",
        "crawler_source_registry",
    )
    marathon_pe_source = _load_source_endpoint("CRAWLER_SOURCE_MARATHON_PE")
    onoffmix_source = _load_source_endpoint("CRAWLER_SOURCE_ONOFFMIX")
    chuncheon_notice_source = _load_source_endpoint("CRAWLER_SOURCE_CHUNCHEON_NOTICE")
    runnext_source = _load_source_endpoint("CRAWLER_SOURCE_RUNNEXT")
    run1080_source = _load_source_endpoint("CRAWLER_SOURCE_RUN1080")
    pokemon_run_source = _load_source_endpoint("CRAWLER_SOURCE_POKEMON_RUN")
    jtbc_source = _load_source_endpoint("CRAWLER_SOURCE_JTBC")
    seoul_marathon_source = _load_source_endpoint("CRAWLER_SOURCE_SEOUL_MARATHON")
    marathon_pe_detail_base_url = _require_env("CRAWLER_SOURCE_MARATHON_PE_DETAIL_BASE_URL")
    onoffmix_base_url = _require_env("CRAWLER_SOURCE_ONOFFMIX_BASE_URL")
    runnext_fallback_url = _require_env("CRAWLER_SOURCE_RUNNEXT_FALLBACK_URL")
    run1080_mini_url_template = _require_env("CRAWLER_SOURCE_RUN1080_MINI_URL_TEMPLATE")
    run1080_event_url_template = _require_env("CRAWLER_SOURCE_RUN1080_EVENT_URL_TEMPLATE")
    pokemon_run_official_url = _require_env("CRAWLER_SOURCE_POKEMON_RUN_OFFICIAL_URL")
    seoul_marathon_detail_url = _require_env("CRAWLER_SOURCE_SEOUL_MARATHON_DETAIL_URL")
    source_priority = _parse_source_priority(os.getenv("CRAWLER_SOURCE_PRIORITY"))
    watch_seed_excluded_sources = _parse_csv_set(
        os.getenv("CRAWLER_WATCH_SEED_EXCLUDED_SOURCES")
    )
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
        event_watch_table=event_watch_table,
        event_watch_seed_table=event_watch_seed_table,
        source_registry_table=source_registry_table,
        marathon_pe_source=marathon_pe_source,
        onoffmix_source=onoffmix_source,
        chuncheon_notice_source=chuncheon_notice_source,
        runnext_source=runnext_source,
        run1080_source=run1080_source,
        pokemon_run_source=pokemon_run_source,
        jtbc_source=jtbc_source,
        seoul_marathon_source=seoul_marathon_source,
        marathon_pe_detail_base_url=marathon_pe_detail_base_url,
        onoffmix_base_url=onoffmix_base_url,
        runnext_fallback_url=runnext_fallback_url,
        run1080_mini_url_template=run1080_mini_url_template,
        run1080_event_url_template=run1080_event_url_template,
        pokemon_run_official_url=pokemon_run_official_url,
        seoul_marathon_detail_url=seoul_marathon_detail_url,
        source_priority=source_priority,
        watch_seed_excluded_sources=watch_seed_excluded_sources,
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


def _load_source_endpoint(prefix: str) -> SourceEndpoint:
    return SourceEndpoint(
        source_name=_require_env(f"{prefix}_NAME"),
        source_url=_require_env(f"{prefix}_URL"),
    )


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"필수 환경변수가 없습니다: {key}")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"필수 환경변수가 비어 있습니다: {key}")
    return normalized


def _parse_csv_set(raw_value: str | None) -> set[str]:
    if raw_value is None or not raw_value.strip():
        return set()
    result: set[str] = set()
    for item in raw_value.split(","):
        normalized = item.strip()
        if normalized:
            result.add(normalized)
    return result


def _parse_source_priority(raw_value: str | None) -> dict[str, int]:
    if raw_value is None or not raw_value.strip():
        return {}

    result: dict[str, int] = {}
    for part in raw_value.split(","):
        token = part.strip()
        if not token or ":" not in token:
            continue
        source_name, score_text = token.split(":", 1)
        source_name = source_name.strip()
        score_text = score_text.strip()
        if not source_name or not score_text:
            continue
        try:
            result[source_name] = int(score_text)
        except ValueError:
            continue
    return result
