from __future__ import annotations

import re

DISTANCE_NUMBER_PATTERN = re.compile(
    r"(?<!\d)(\d{1,3}(?:\.\d{1,4})?)\s*(?:km|k|㎞|킬로|키로)(?![a-z])",
    re.IGNORECASE,
)
DISTANCE_SERIES_PATTERN = re.compile(
    r"((?:\d{1,3}(?:\.\d{1,4})?\s*[,/]\s*)+\d{1,3}(?:\.\d{1,4})?)\s*(?:km|k|㎞|킬로|키로)",
    re.IGNORECASE,
)
HALF_KEYWORD_PATTERN = re.compile(r"(?:half|하프)")
FULL_KEYWORD_PATTERN = re.compile(r"(?:full|풀코스|풀마라톤)")
FULL_TOKEN_PATTERN = re.compile(r"(^|[\s,()/|&\-])풀($|[\s,()/|&\-])")


def extract_distances_from_title(title: str) -> list[str]:
    text = _normalize_text(title)
    if not text:
        return []

    distances: set[str] = set()
    lowered = text.lower()

    if HALF_KEYWORD_PATTERN.search(lowered):
        distances.add("HALF")
    if FULL_KEYWORD_PATTERN.search(lowered) or FULL_TOKEN_PATTERN.search(text):
        distances.add("FULL")

    for value in _extract_numeric_distance_values(text):
        canonical = _to_canonical_distance(value)
        if canonical is not None:
            distances.add(canonical)

    return sorted(distances, key=_distance_sort_key)


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def _extract_numeric_distance_values(text: str) -> list[float]:
    values: list[float] = []

    for series_match in DISTANCE_SERIES_PATTERN.finditer(text):
        series = series_match.group(1)
        for token in re.split(r"[,/]", series):
            value = _parse_number(token)
            if value is not None:
                values.append(value)

    for matched in DISTANCE_NUMBER_PATTERN.finditer(text):
        value = _parse_number(matched.group(1))
        if value is not None:
            values.append(value)

    return values


def _parse_number(raw: str) -> float | None:
    normalized = raw.strip()
    if not normalized:
        return None
    try:
        parsed = float(normalized)
    except ValueError:
        return None
    if parsed <= 0 or parsed > 300:
        return None
    return parsed


def _to_canonical_distance(value: float) -> str | None:
    if 41.7 <= value <= 42.5:
        return "FULL"
    if 20.8 <= value <= 21.3:
        return "HALF"
    if value.is_integer():
        return f"{int(value)}K"
    normalized = f"{value:.3f}".rstrip("0").rstrip(".")
    if not normalized:
        return None
    return f"{normalized}K"


def _distance_sort_key(distance: str) -> tuple[int, float, str]:
    if distance.endswith("K"):
        numeric = _parse_number(distance[:-1])
        if numeric is not None:
            return (0, numeric, distance)
    if distance == "HALF":
        return (1, 0.0, distance)
    if distance == "FULL":
        return (2, 0.0, distance)
    return (3, 0.0, distance)
