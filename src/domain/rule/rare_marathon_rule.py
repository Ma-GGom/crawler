import re

NON_TEXT_PATTERN = re.compile(r"[^0-9a-z가-힣]+")

RARE_MARATHON_KEYWORDS = (
    "kb스타런",
    "kbstarrun",
    "포켓몬런",
    "산리오런",
    "동아마라톤",
    "동마",
    "중앙서울마라톤",
    "제마",
    "춘천마라톤",
    "춘마",
    "jtbc마라톤",
    "jtbc서울마라톤",
)


def normalize_rare_text(value: str) -> str:
    lowered = value.strip().lower()
    if not lowered:
        return ""
    return NON_TEXT_PATTERN.sub("", lowered)


def match_rare_marathon_keywords(title: str) -> list[str]:
    normalized_title = normalize_rare_text(title)
    if not normalized_title:
        return []

    matched: list[str] = []
    for keyword in RARE_MARATHON_KEYWORDS:
        normalized_keyword = normalize_rare_text(keyword)
        if not normalized_keyword:
            continue
        if normalized_keyword in normalized_title:
            matched.append(keyword)
    return matched
