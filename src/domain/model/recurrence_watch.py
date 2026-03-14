from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class RecurrenceWatchSeed:
    title: str
    event_date: date
    source_name: str | None = None
    source_url: str | None = None


@dataclass(frozen=True, slots=True)
class RecurrenceWatchCandidate:
    watch_key: str
    base_title: str
    sample_title: str
    last_event_date: date
    expected_event_date: date
    detected_event_date: date | None
    status: str
    source_name: str | None = None
    source_url: str | None = None
