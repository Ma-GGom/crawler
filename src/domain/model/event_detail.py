from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class MarathonEventDetail:
    registration_period: str | None = None
    official_website_url: str | None = None
    registration_start_date: date | None = None
    registration_end_date: date | None = None
    event_date: date | None = None
    location: str | None = None
