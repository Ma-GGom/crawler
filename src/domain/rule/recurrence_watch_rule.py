from datetime import date
import re

from domain.model.recurrence_watch import (
    RecurrenceWatchCandidate,
    RecurrenceWatchSeed,
)

YEAR_PATTERN = re.compile(r"\b20\d{2}\b")
ROUND_PATTERN = re.compile(r"제\s*\d+\s*회")
NON_WORD_PATTERN = re.compile(r"[^0-9a-z가-힣]+")


def normalize_watch_title(title: str) -> str:
    normalized = title.strip().lower()
    normalized = YEAR_PATTERN.sub(" ", normalized)
    normalized = ROUND_PATTERN.sub(" ", normalized)
    normalized = NON_WORD_PATTERN.sub(" ", normalized)
    return " ".join(normalized.split())


def build_recurrence_watch_candidates(
    seeds: list[RecurrenceWatchSeed], *, today_kst: date
) -> list[RecurrenceWatchCandidate]:
    previous_year = today_kst.year - 1
    current_year = today_kst.year
    previous_by_key: dict[str, RecurrenceWatchSeed] = {}
    current_by_key: dict[str, RecurrenceWatchSeed] = {}

    for seed in seeds:
        key = normalize_watch_title(seed.title)
        if not key:
            continue

        if seed.event_date.year == previous_year:
            previous = previous_by_key.get(key)
            if previous is None or seed.event_date > previous.event_date:
                previous_by_key[key] = seed
            continue

        if seed.event_date.year == current_year:
            current = current_by_key.get(key)
            if current is None or seed.event_date < current.event_date:
                current_by_key[key] = seed

    candidates: list[RecurrenceWatchCandidate] = []
    for key, previous in previous_by_key.items():
        expected_date = _add_year(previous.event_date)
        detected = current_by_key.get(key)
        status = "DETECTED" if detected is not None else "PENDING"
        sample_title = detected.title if detected is not None else previous.title
        detected_date = detected.event_date if detected is not None else None

        candidates.append(
            RecurrenceWatchCandidate(
                watch_key=key,
                base_title=key,
                sample_title=sample_title,
                last_event_date=previous.event_date,
                expected_event_date=expected_date,
                detected_event_date=detected_date,
                status=status,
                source_name=previous.source_name,
                source_url=previous.source_url,
            )
        )

    candidates.sort(key=lambda item: (item.expected_event_date, item.base_title))
    return candidates


def _add_year(value: date) -> date:
    try:
        return value.replace(year=value.year + 1)
    except ValueError:
        return value.replace(year=value.year + 1, day=28)
