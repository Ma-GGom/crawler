import re


DATE_TEXT_PATTERN = re.compile(r"^\d{1,2}/\d{1,2}\([^)]+\)$")


def is_header_row(date_text: str) -> bool:
    normalized = date_text.strip()
    return "일자" in normalized


def has_required_fields(date_text: str, title: str, location: str) -> bool:
    return bool(date_text.strip() and title.strip() and location.strip())


def has_valid_date_shape(date_text: str) -> bool:
    normalized = date_text.strip()
    return bool(DATE_TEXT_PATTERN.fullmatch(normalized))
