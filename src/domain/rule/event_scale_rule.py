from domain.model.marathon_event import MarathonEvent

EVENT_SCALE_MAJOR = "MAJOR"
EVENT_SCALE_SMALL = "SMALL"
EVENT_SCALE_UNKNOWN = "UNKNOWN"

MAJOR_KEYWORDS = (
    "서울마라톤",
    "동아마라톤",
    "jtbc서울마라톤",
    "jtbc 마라톤",
    "중앙서울마라톤",
    "제마",
    "춘천마라톤",
    "국제마라톤",
)

SMALL_KEYWORDS = (
    "훈련",
    "교실",
    "무료초청",
    "무료 초청",
    "걷기대회",
    "걷기 대회",
    "클럽런",
    "동호회",
    "체험런",
    "체험 런",
    "펀런",
    "fun run",
)


def classify_event_scale(event: MarathonEvent) -> str:
    title = event.title.strip().lower()
    if not title:
        return EVENT_SCALE_UNKNOWN

    if any(keyword.lower() in title for keyword in MAJOR_KEYWORDS):
        return EVENT_SCALE_MAJOR
    if any(keyword.lower() in title for keyword in SMALL_KEYWORDS):
        return EVENT_SCALE_SMALL
    return EVENT_SCALE_UNKNOWN


def is_major_scale(scale: str) -> bool:
    return scale == EVENT_SCALE_MAJOR
