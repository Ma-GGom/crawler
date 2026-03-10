from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SourcePayload:
    source_name: str
    source_url: str
    html: str
    fetched_at_kst: datetime
