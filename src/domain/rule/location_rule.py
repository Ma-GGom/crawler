from __future__ import annotations

from functools import lru_cache
import logging
import os
import re

from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


def _parse_bool(raw_value: str | None, *, default: bool) -> bool:
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_float(raw_value: str | None, *, default: float) -> float:
    if raw_value is None or not raw_value.strip():
        return default
    try:
        parsed = float(raw_value)
    except ValueError:
        return default
    if parsed <= 0:
        return default
    return parsed


def _parse_positive_int(raw_value: str | None, *, default: int) -> int:
    if raw_value is None or not raw_value.strip():
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    if parsed <= 0:
        return default
    return parsed


ONLINE_ENRICHMENT_ENABLED = _parse_bool(
    os.getenv("CRAWLER_LOCATION_ONLINE_ENRICHMENT_ENABLED"),
    default=True,
)
ONLINE_ENRICHMENT_TIMEOUT_SECONDS = _parse_float(
    os.getenv("CRAWLER_LOCATION_ONLINE_TIMEOUT_SECONDS"),
    default=1.8,
)
ONLINE_ENRICHMENT_ENDPOINT = os.getenv(
    "CRAWLER_LOCATION_ONLINE_ENDPOINT",
    "https://nominatim.openstreetmap.org/search",
).strip()
ONLINE_ENRICHMENT_USER_AGENT = os.getenv(
    "CRAWLER_LOCATION_ONLINE_USER_AGENT",
    "maggom-crawler/1.0 (+https://maggom.com)",
).strip()
LINK_ENRICHMENT_ENABLED = _parse_bool(
    os.getenv("CRAWLER_LOCATION_LINK_ENRICHMENT_ENABLED"),
    default=True,
)
LINK_ENRICHMENT_TIMEOUT_SECONDS = _parse_float(
    os.getenv("CRAWLER_LOCATION_LINK_TIMEOUT_SECONDS"),
    default=2.5,
)
LINK_ENRICHMENT_USER_AGENT = os.getenv(
    "CRAWLER_LOCATION_LINK_USER_AGENT",
    "maggom-crawler/1.0 (+https://maggom.com)",
).strip()
LINK_ENRICHMENT_MAX_TEXT_CHARS = _parse_positive_int(
    os.getenv("CRAWLER_LOCATION_LINK_MAX_TEXT_CHARS"),
    default=12000,
)

PROVINCE_ALIAS: dict[str, str] = {
    "서울": "서울특별시",
    "서울시": "서울특별시",
    "서울특별시": "서울특별시",
    "부산": "부산광역시",
    "부산시": "부산광역시",
    "부산광역시": "부산광역시",
    "대구": "대구광역시",
    "대구시": "대구광역시",
    "대구광역시": "대구광역시",
    "인천": "인천광역시",
    "인천시": "인천광역시",
    "인천광역시": "인천광역시",
    "광주": "광주광역시",
    "광주시": "광주광역시",
    "광주광역시": "광주광역시",
    "대전": "대전광역시",
    "대전시": "대전광역시",
    "대전광역시": "대전광역시",
    "울산": "울산광역시",
    "울산시": "울산광역시",
    "울산광역시": "울산광역시",
    "세종": "세종특별자치시",
    "세종시": "세종특별자치시",
    "세종특별자치시": "세종특별자치시",
    "경기": "경기도",
    "경기도": "경기도",
    "강원": "강원특별자치도",
    "강원도": "강원특별자치도",
    "강원특별자치도": "강원특별자치도",
    "충북": "충청북도",
    "충청북도": "충청북도",
    "충남": "충청남도",
    "충청남도": "충청남도",
    "전북": "전북특별자치도",
    "전라북도": "전북특별자치도",
    "전북특별자치도": "전북특별자치도",
    "전남": "전라남도",
    "전라남도": "전라남도",
    "경북": "경상북도",
    "경상북도": "경상북도",
    "경남": "경상남도",
    "경상남도": "경상남도",
    "제주": "제주특별자치도",
    "제주도": "제주특별자치도",
    "제주특별자치도": "제주특별자치도",
    "seoul": "서울특별시",
    "busan": "부산광역시",
    "daegu": "대구광역시",
    "incheon": "인천광역시",
    "gwangju": "광주광역시",
    "daejeon": "대전광역시",
    "ulsan": "울산광역시",
    "sejong": "세종특별자치시",
    "gyeonggi": "경기도",
    "gangwon": "강원특별자치도",
    "chungcheongbuk": "충청북도",
    "chungcheongnam": "충청남도",
    "jeonbuk": "전북특별자치도",
    "jeonnam": "전라남도",
    "gyeongbuk": "경상북도",
    "gyeongnam": "경상남도",
    "jeju": "제주특별자치도",
}

PROVINCE_DISPLAY_ALIAS: dict[str, str] = {
    "서울특별시": "서울시",
    "부산광역시": "부산시",
    "대구광역시": "대구시",
    "인천광역시": "인천시",
    "광주광역시": "광주시",
    "대전광역시": "대전시",
    "울산광역시": "울산시",
    "세종특별자치시": "세종시",
    "강원특별자치도": "강원도",
    "전북특별자치도": "전라북도",
    "제주특별자치도": "제주도",
}

CITY_TO_REGION: dict[str, tuple[str, str]] = {
    "강릉": ("강원특별자치도", "강릉시"),
    "전주": ("전북특별자치도", "전주시"),
    "아산": ("충청남도", "아산시"),
    "무주": ("전북특별자치도", "무주군"),
    "나주": ("전라남도", "나주시"),
    "춘천": ("강원특별자치도", "춘천시"),
    "제주": ("제주특별자치도", "제주시"),
    "금산": ("충청남도", "금산군"),
    "창원": ("경상남도", "창원시"),
    "군산": ("전북특별자치도", "군산시"),
    "진주": ("경상남도", "진주시"),
    "정읍": ("전북특별자치도", "정읍시"),
    "청주": ("충청북도", "청주시"),
    "시흥": ("경기도", "시흥시"),
    "이천": ("경기도", "이천시"),
    "삼척": ("강원특별자치도", "삼척시"),
    "영광": ("전라남도", "영광군"),
    "영암": ("전라남도", "영암군"),
    "보성": ("전라남도", "보성군"),
    "보은": ("충청북도", "보은군"),
    "홍성": ("충청남도", "홍성군"),
    "합천": ("경상남도", "합천군"),
    "예산": ("충청남도", "예산군"),
    "기장": ("부산광역시", "기장군"),
    "구리": ("경기도", "구리시"),
    "하남": ("경기도", "하남시"),
    "양천": ("서울특별시", "양천구"),
    "성북": ("서울특별시", "성북구"),
    "송도": ("인천광역시", "연수구"),
    "영종": ("인천광역시", "중구"),
    "밀양": ("경상남도", "밀양시"),
    "부산": ("부산광역시", "해운대구"),
    "대구": ("대구광역시", "수성구"),
    "대전": ("대전광역시", "유성구"),
    "광주": ("광주광역시", "북구"),
}
CITY_OR_DISTRICT_TO_PROVINCE: dict[str, str] = {
    city_or_district: province
    for province, city_or_district in CITY_TO_REGION.values()
}

VENUE_KEYWORD_TO_REGION: dict[str, tuple[str, str]] = {
    "올림픽공원": ("서울특별시", "송파구"),
    "잠실종합운동장": ("서울특별시", "송파구"),
    "여의도공원": ("서울특별시", "영등포구"),
    "여의도": ("서울특별시", "영등포구"),
    "상암월드컵경기장": ("서울특별시", "마포구"),
    "상암동": ("서울특별시", "마포구"),
    "상암": ("서울특별시", "마포구"),
    "광화문광장": ("서울특별시", "종로구"),
    "광화문": ("서울특별시", "종로구"),
    "신정교": ("서울특별시", "양천구"),
    "창동교": ("서울특별시", "도봉구"),
    "뚝섬": ("서울특별시", "광진구"),
    "나주종합스포츠파크": ("전라남도", "나주시"),
    "화엄사주차장": ("전라남도", "구례군"),
    "고래불해수욕장": ("경상북도", "영덕군"),
    "봉화공설운동장": ("경상북도", "봉화군"),
    "울진종합운동장": ("경상북도", "울진군"),
}

DISTRICT_TO_PROVINCE: dict[str, str] = {
    "종로구": "서울특별시",
    "중구": "서울특별시",
    "용산구": "서울특별시",
    "성동구": "서울특별시",
    "광진구": "서울특별시",
    "동대문구": "서울특별시",
    "중랑구": "서울특별시",
    "성북구": "서울특별시",
    "강북구": "서울특별시",
    "도봉구": "서울특별시",
    "노원구": "서울특별시",
    "은평구": "서울특별시",
    "서대문구": "서울특별시",
    "마포구": "서울특별시",
    "양천구": "서울특별시",
    "강서구": "서울특별시",
    "구로구": "서울특별시",
    "금천구": "서울특별시",
    "영등포구": "서울특별시",
    "동작구": "서울특별시",
    "관악구": "서울특별시",
    "서초구": "서울특별시",
    "강남구": "서울특별시",
    "송파구": "서울특별시",
    "강동구": "서울특별시",
}

LOCATION_SPLIT_PATTERN = re.compile(r"[\s,|/()]+")
ONLINE_ENRICHMENT_BLOCKLIST = {"전국", "국내", "해외", "장소미정", "미정"}
ONLINE_ENRICHMENT_HINTS = (
    "공원",
    "경기장",
    "운동장",
    "스타디움",
    "광장",
    "해수욕장",
    "주차장",
    "돔",
    "센터",
    "타워",
    "파크",
)

TITLE_KEYWORD_TO_REGION: dict[str, tuple[str, str]] = {
    "가든파이브": ("서울특별시", "송파구"),
    "청남대": ("충청북도", "청주시"),
    "오크밸리": ("강원특별자치도", "원주시"),
    "빛고을": ("광주광역시", "서구"),
    "무등산": ("광주광역시", "북구"),
    "정읍동학": ("전북특별자치도", "정읍시"),
    "영광": ("전라남도", "영광군"),
    "군산새만금": ("전북특별자치도", "군산시"),
    "이천도자기": ("경기도", "이천시"),
    "삼척": ("강원특별자치도", "삼척시"),
    "보성": ("전라남도", "보성군"),
    "보은": ("충청북도", "보은군"),
    "기장": ("부산광역시", "기장군"),
    "창원": ("경상남도", "창원시"),
    "홍성": ("충청남도", "홍성군"),
    "하남": ("경기도", "하남시"),
    "시흥": ("경기도", "시흥시"),
    "영종": ("인천광역시", "중구"),
    "세종": ("세종특별자치시", "세종시"),
    "남해": ("경상남도", "남해군"),
    "내포": ("충청남도", "홍성군"),
    "지리산": ("전라남도", "구례군"),
    "knn환경": ("부산광역시", "해운대구"),
    "남산우정": ("서울특별시", "중구"),
    "태화강": ("울산광역시", "중구"),
    "청라": ("인천광역시", "서구"),
    "315마라톤": ("경상남도", "창원시"),
    "안양천": ("서울특별시", "구로구"),
    "김포": ("경기도", "김포시"),
    "건양대학교": ("충청남도", "논산시"),
    "광교산": ("경기도", "수원시"),
    "영주소백산": ("경상북도", "영주시"),
    "대청호": ("충청북도", "청주시"),
    "섬진강": ("전라남도", "구례군"),
    "단양팔경": ("충청북도", "단양군"),
    "dmz평화": ("강원특별자치도", "철원군"),
    "호남마라톤": ("광주광역시", "서구"),
    "부안": ("전북특별자치도", "부안군"),
    "반기문": ("충청북도", "음성군"),
    "홍천": ("강원특별자치도", "홍천군"),
    "포항해변": ("경상북도", "포항시"),
    "5.18": ("광주광역시", "북구"),
    "518": ("광주광역시", "북구"),
    "보령머드": ("충청남도", "보령시"),
    "용인": ("경기도", "용인시"),
    "무의도": ("인천광역시", "중구"),
    "서천": ("충청남도", "서천군"),
    "거제": ("경상남도", "거제시"),
    "백양산": ("부산광역시", "부산진구"),
    "경주시육상연맹": ("경상북도", "경주시"),
    "남한산성": ("경기도", "광주시"),
    "포항철강": ("경상북도", "포항시"),
    "성남": ("경기도", "성남시"),
    "일광": ("부산광역시", "기장군"),
    "울릉도": ("경상북도", "울릉군"),
    "충주": ("충청북도", "충주시"),
    "청계산": ("서울특별시", "서초구"),
    "대구세계마스터즈": ("대구광역시", "수성구"),
    "철원dmz": ("강원특별자치도", "철원군"),
    "영덕": ("경상북도", "영덕군"),
    "설악산": ("강원특별자치도", "속초시"),
    "가평": ("경기도", "가평군"),
    "아산이순신": ("충청남도", "아산시"),
    "천안": ("충청남도", "천안시"),
    "청원생명쌀": ("충청북도", "청주시"),
    "just run": ("충청북도", "청주시"),
    "버킷런": ("경기도", "하남시"),
    "고래마라톤": ("울산광역시", "남구"),
    "busan": ("부산광역시", "해운대구"),
    "daegu": ("대구광역시", "수성구"),
    "daejeon": ("대전광역시", "유성구"),
    "gwangju": ("광주광역시", "북구"),
    "seoul": ("서울특별시", "중구"),
}
TITLE_REGION_BLOCKLIST = {
    "전국",
    "국제",
    "마라톤",
    "레이스",
    "트레일",
    "울트라",
    "걷기",
    "러닝",
    "run",
    "race",
}
TITLE_PLACE_HINT_PATTERN = re.compile(
    r"([가-힣A-Za-z][가-힣A-Za-z\s]{1,24}?)(?:마라톤|레이스|트레일런|트레일|울트라|런)"
)
TITLE_ADMIN_TOKEN_PATTERN = re.compile(r"([가-힣]{2,15}(?:시|군|구))")
REGION_PHRASE_PATTERN = re.compile(
    r"(서울(?:특별시|시)?|부산(?:광역시|시)?|대구(?:광역시|시)?|인천(?:광역시|시)?|"
    r"광주(?:광역시|시)?|대전(?:광역시|시)?|울산(?:광역시|시)?|세종(?:특별자치시|시)?|"
    r"경기도|강원(?:특별자치도|도)|충청북도|충청남도|전북(?:특별자치도|도|라북도)|"
    r"전라남도|경상북도|경상남도|제주(?:특별자치도|도))\s*([가-힣]{1,15}(?:시|군|구))"
)
LOCATION_LINE_HINTS: tuple[str, ...] = (
    "장소",
    "대회장",
    "집결",
    "출발",
    "코스",
    "start",
    "location",
)
HOST_KEYWORD_TO_REGION: dict[str, tuple[str, str]] = {
    "incheonmarathon": ("인천광역시", "미추홀구"),
    "gimporun": ("경기도", "김포시"),
    "gnmarathon": ("경상남도", "진주시"),
    "ynmarathon": ("대구광역시", "수성구"),
    "run.ksilbo": ("울산광역시", "남구"),
    "ulsanmaeilmara": ("울산광역시", "중구"),
    "cjapplemarathon": ("충청북도", "충주시"),
    "dmzrun": ("강원특별자치도", "철원군"),
    "phsteelrun": ("경상북도", "포항시"),
    "phrun": ("경상북도", "포항시"),
    "ulmarathon": ("경상북도", "울릉군"),
    "osk.run": ("경상북도", "울릉군"),
    "sandrun": ("경상북도", "영덕군"),
    "brrun": ("충청남도", "보령시"),
    "yonginmarathon": ("경기도", "용인시"),
    "incheonafcup": ("인천광역시", "연수구"),
    "geoje100": ("경상남도", "거제시"),
    "gprun": ("경기도", "가평군"),
    "givenrace": ("서울특별시", "송파구"),
}

REGION_UNKNOWN = "unknown"


def normalize_region(location: str) -> str:
    normalized = _normalize_text(location)
    if not normalized:
        return REGION_UNKNOWN

    for keyword, (province, city_or_district) in VENUE_KEYWORD_TO_REGION.items():
        if keyword in normalized:
            return _compose_region(province, city_or_district)

    tokens = [token for token in LOCATION_SPLIT_PATTERN.split(normalized) if token]
    if not tokens:
        return REGION_UNKNOWN

    province = _extract_province(tokens)
    city_or_district = _extract_city_or_district(tokens)

    if city_or_district is None:
        city_or_district = _extract_from_known_city(tokens)
        if city_or_district is not None and province is None:
            province = _extract_province_from_known_city(tokens)

    if province is None and city_or_district is not None:
        province = DISTRICT_TO_PROVINCE.get(city_or_district)

    province = _reconcile_province_by_city(
        province=province,
        city_or_district=city_or_district,
    )

    if province is not None and city_or_district is not None:
        return _compose_region(province, city_or_district)

    online_enriched = _enrich_region_online(normalized)
    if online_enriched is not None:
        return online_enriched
    return REGION_UNKNOWN


def resolve_event_region(
    location: str,
    *,
    title: str | None = None,
    link_url: str | None = None,
) -> str:
    primary = normalize_region(location)
    if primary != REGION_UNKNOWN:
        return primary
    if title is None or not title.strip():
        return _infer_region_from_link_url(link_url)
    by_title = _infer_region_from_title(title)
    if by_title != REGION_UNKNOWN:
        return by_title
    by_link = _infer_region_from_link_url(link_url)
    if by_link != REGION_UNKNOWN:
        return by_link
    return _infer_region_from_link_content(link_url)


def _normalize_text(location: str) -> str:
    return " ".join(location.strip().split())


def _extract_province(tokens: list[str]) -> str | None:
    for token in tokens:
        candidate = _canonicalize_province(token)
        if candidate:
            return candidate

    joined = " ".join(tokens).lower()
    for alias, canonical in PROVINCE_ALIAS.items():
        if alias and alias in joined:
            return canonical
    return None


def _extract_city_or_district(tokens: list[str]) -> str | None:
    for token in tokens:
        if _canonicalize_province(token) is not None:
            continue
        if token.endswith(("시", "군", "구")) and len(token) >= 2:
            return token
    return None


def _extract_from_known_city(tokens: list[str]) -> str | None:
    for token in tokens:
        if token in CITY_TO_REGION:
            return CITY_TO_REGION[token][1]
    joined = " ".join(tokens)
    for city, (_, city_or_district) in CITY_TO_REGION.items():
        if city in joined:
            return city_or_district
    return None


def _extract_province_from_known_city(tokens: list[str]) -> str | None:
    for token in tokens:
        if token in CITY_TO_REGION:
            return CITY_TO_REGION[token][0]
    joined = " ".join(tokens)
    for city, (province, _) in CITY_TO_REGION.items():
        if city in joined:
            return province
    return None


def _reconcile_province_by_city(
    *,
    province: str | None,
    city_or_district: str | None,
) -> str | None:
    if city_or_district is None:
        return province

    inferred = DISTRICT_TO_PROVINCE.get(city_or_district)
    if inferred is None:
        inferred = CITY_OR_DISTRICT_TO_PROVINCE.get(city_or_district)
    if inferred is None and city_or_district.endswith("시"):
        base_city = city_or_district[:-1]
        known = CITY_TO_REGION.get(base_city)
        if known is not None:
            inferred = known[0]

    if inferred is None:
        return province
    if province is None:
        return inferred
    if province != inferred:
        return inferred
    return province


def _canonicalize_province(raw_value: str) -> str | None:
    normalized = raw_value.strip()
    if not normalized:
        return None
    lowered = normalized.lower()
    return PROVINCE_ALIAS.get(normalized) or PROVINCE_ALIAS.get(lowered)


def _format_province_for_storage(province: str) -> str:
    return PROVINCE_DISPLAY_ALIAS.get(province, province)


def _compose_region(province: str, city_or_district: str) -> str:
    display_province = _format_province_for_storage(province)
    return f"{display_province} {city_or_district}"


def _infer_region_from_title(title: str) -> str:
    normalized = _normalize_text(title)
    if not normalized:
        return REGION_UNKNOWN

    for candidate in _extract_title_place_candidates(normalized):
        mapped = _map_title_keyword_to_region(candidate)
        if mapped is not None:
            return mapped

        normalized_candidate = normalize_region(candidate)
        if normalized_candidate != REGION_UNKNOWN:
            return normalized_candidate

    return REGION_UNKNOWN


def _extract_title_place_candidates(title: str) -> list[str]:
    candidates: list[str] = []
    lowered_title = title.lower()

    for keyword in TITLE_KEYWORD_TO_REGION.keys():
        if keyword.lower() in lowered_title:
            candidates.append(keyword)
    for city in CITY_TO_REGION.keys():
        if city in title:
            candidates.append(city)

    for matched in TITLE_ADMIN_TOKEN_PATTERN.finditer(title):
        token = matched.group(1).strip()
        if token:
            candidates.append(token)

    for matched in TITLE_PLACE_HINT_PATTERN.finditer(title):
        raw = matched.group(1).strip()
        if not raw:
            continue
        prefix = _strip_event_prefix(raw)
        if prefix and prefix not in TITLE_REGION_BLOCKLIST:
            candidates.append(prefix)
            if len(prefix) >= 3:
                candidates.append(prefix[:3])
            if len(prefix) >= 2:
                candidates.append(prefix[:2])

    for english in ("busan", "daegu", "daejeon", "gwangju", "seoul"):
        if english in lowered_title:
            candidates.append(english)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized:
            continue
        lowered_candidate = normalized.lower()
        if lowered_candidate in TITLE_REGION_BLOCKLIST:
            continue
        if lowered_candidate in seen:
            continue
        seen.add(lowered_candidate)
        deduped.append(normalized)
        if len(deduped) >= 12:
            break
    return deduped


def _strip_event_prefix(raw: str) -> str:
    cleaned = raw
    cleaned = re.sub(r"^\d{2,4}", "", cleaned)
    cleaned = re.sub(r"^제\d+회", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def _map_title_keyword_to_region(candidate: str) -> str | None:
    lowered = candidate.lower()
    for keyword, (province, city_or_district) in TITLE_KEYWORD_TO_REGION.items():
        if keyword.lower() in lowered:
            return _compose_region(province, city_or_district)
    return None


def _infer_region_from_link_url(link_url: str | None) -> str:
    if link_url is None or not link_url.strip():
        return REGION_UNKNOWN
    lowered = link_url.lower()
    for keyword, (province, city_or_district) in HOST_KEYWORD_TO_REGION.items():
        if keyword in lowered:
            return _compose_region(province, city_or_district)
    return REGION_UNKNOWN


def _infer_region_from_link_content(link_url: str | None) -> str:
    if not LINK_ENRICHMENT_ENABLED:
        return REGION_UNKNOWN
    if link_url is None or not link_url.strip():
        return REGION_UNKNOWN
    if not link_url.startswith(("http://", "https://")):
        return REGION_UNKNOWN

    text = _fetch_link_text(link_url)
    if text is None:
        return REGION_UNKNOWN

    for line in _extract_location_lines(text):
        phrase = _extract_region_phrase(line)
        if phrase is not None:
            normalized = normalize_region(phrase)
            if normalized != REGION_UNKNOWN:
                return normalized

    return REGION_UNKNOWN


def _extract_region_phrase(text: str) -> str | None:
    matched = REGION_PHRASE_PATTERN.search(text)
    if matched is None:
        return None
    province = matched.group(1).strip()
    city_or_district = matched.group(2).strip()
    return f"{province} {city_or_district}"


def _extract_location_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    candidates: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(hint in lowered for hint in LOCATION_LINE_HINTS):
            candidates.append(line)

    deduped: list[str] = []
    seen: set[str] = set()
    for line in candidates:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
        if len(deduped) >= 120:
            break
    return deduped


@lru_cache(maxsize=256)
def _fetch_link_text(link_url: str) -> str | None:
    try:
        response = requests.get(
            link_url,
            headers={"User-Agent": LINK_ENRICHMENT_USER_AGENT},
            timeout=LINK_ENRICHMENT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning(
            "공식 링크 페이지 보강 실패",
            extra={"link_url": link_url, "error": str(exc)},
        )
        return None

    encoding = response.encoding or response.apparent_encoding or "utf-8"
    raw_content = getattr(response, "content", None)
    if isinstance(raw_content, (bytes, bytearray)):
        try:
            html = raw_content.decode(encoding, errors="replace")
        except Exception:
            html = getattr(response, "text", "") or ""
    else:
        html = getattr(response, "text", "") or ""
    if not html.strip():
        return None
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    if not text:
        return None
    if LINK_ENRICHMENT_MAX_TEXT_CHARS > 0:
        return text[:LINK_ENRICHMENT_MAX_TEXT_CHARS]
    return text


def _should_try_online_enrichment(normalized: str) -> bool:
    if not ONLINE_ENRICHMENT_ENABLED:
        return False
    if normalized in ONLINE_ENRICHMENT_BLOCKLIST:
        return False
    if " " not in normalized and _canonicalize_province(normalized) is not None:
        return False
    if any(hint in normalized for hint in ONLINE_ENRICHMENT_HINTS):
        return True
    return False


def _enrich_region_online(normalized: str) -> str | None:
    if not _should_try_online_enrichment(normalized):
        return None
    return _query_online_region(normalized)


@lru_cache(maxsize=512)
def _query_online_region(normalized: str) -> str | None:
    try:
        response = requests.get(
            ONLINE_ENRICHMENT_ENDPOINT,
            params={
                "q": f"{normalized} 대한민국",
                "countrycodes": "kr",
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 1,
            },
            headers={"User-Agent": ONLINE_ENRICHMENT_USER_AGENT},
            timeout=ONLINE_ENRICHMENT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = response.json()
    except Exception as exc:
        logger.warning(
            "장소 온라인 보강 실패",
            extra={"location": normalized, "error": str(exc)},
        )
        return None

    if not isinstance(items, list) or not items:
        return None
    top = items[0] if isinstance(items[0], dict) else None
    if top is None:
        return None

    address = top.get("address")
    if not isinstance(address, dict):
        return None

    province = _extract_province_from_address(address)
    city_or_district = _extract_city_or_district_from_address(address)

    if province is None:
        province = _extract_province_from_display_name(top.get("display_name"))
    if city_or_district is None:
        city_or_district = _extract_city_from_display_name(top.get("display_name"))

    if province is None or city_or_district is None:
        return None
    return _compose_region(province, city_or_district)


def _extract_province_from_address(address: dict[str, object]) -> str | None:
    for key in ("state", "region", "province", "city"):
        value = address.get(key)
        if not isinstance(value, str):
            continue
        canonical = _canonicalize_province(value)
        if canonical:
            return canonical
    return None


def _extract_city_or_district_from_address(address: dict[str, object]) -> str | None:
    for key in (
        "city_district",
        "borough",
        "county",
        "city",
        "municipality",
        "town",
        "village",
        "suburb",
        "quarter",
    ):
        value = address.get(key)
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if not candidate:
            continue
        if _canonicalize_province(candidate) is not None:
            continue
        if candidate.endswith(("시", "군", "구")):
            return candidate
        if candidate in CITY_TO_REGION:
            return CITY_TO_REGION[candidate][1]
    return None


def _extract_province_from_display_name(raw_display_name: object) -> str | None:
    if not isinstance(raw_display_name, str) or not raw_display_name.strip():
        return None
    parts = [part.strip() for part in raw_display_name.split(",") if part.strip()]
    for part in parts:
        canonical = _canonicalize_province(part)
        if canonical:
            return canonical
    return None


def _extract_city_from_display_name(raw_display_name: object) -> str | None:
    if not isinstance(raw_display_name, str) or not raw_display_name.strip():
        return None
    parts = [part.strip() for part in raw_display_name.split(",") if part.strip()]
    for part in parts:
        if _canonicalize_province(part) is not None:
            continue
        if part.endswith(("시", "군", "구")):
            return part
        if part in CITY_TO_REGION:
            return CITY_TO_REGION[part][1]
    return None
