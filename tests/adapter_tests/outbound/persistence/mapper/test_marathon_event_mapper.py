from datetime import date
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.persistence.mapper.marathon_event_mapper import MarathonEventMapper
from domain.model.marathon_event import MarathonEvent


class MarathonEventMapperTest(unittest.TestCase):
    def test_set_major_scale_and_major_flag(self) -> None:
        event = MarathonEvent(
            date_text="2026-11-01",
            title="2026 JTBC 서울마라톤",
            location="서울",
            link_url="https://example.com",
            event_date=date(2026, 11, 1),
        )

        row = MarathonEventMapper.to_row(event)

        self.assertEqual("MAJOR", row.event_scale)
        self.assertTrue(row.is_major)

    def test_set_small_scale_and_not_major_flag(self) -> None:
        event = MarathonEvent(
            date_text="2026-09-01",
            title="가을 무료 초청 훈련 런",
            location="서울",
            link_url="https://example.com",
            event_date=date(2026, 9, 1),
        )

        row = MarathonEventMapper.to_row(event)

        self.assertEqual("SMALL", row.event_scale)
        self.assertFalse(row.is_major)

    def test_normalize_region_to_province_and_city_or_district(self) -> None:
        event = MarathonEvent(
            date_text="2026-10-03",
            title="Test Race",
            location="마포구",
            link_url="https://example.com/region",
            event_date=date(2026, 10, 3),
        )

        row = MarathonEventMapper.to_row(event)

        self.assertEqual("서울시 마포구", row.region)

    def test_set_region_unknown_when_location_has_only_province(self) -> None:
        event = MarathonEvent(
            date_text="2026-10-03",
            title="Test Race",
            location="강원도",
            link_url="https://example.com/region",
            event_date=date(2026, 10, 3),
        )

        row = MarathonEventMapper.to_row(event)

        self.assertEqual("unknown", row.region)

    def test_infer_region_from_title_when_location_unknown(self) -> None:
        event = MarathonEvent(
            date_text="2026-10-03",
            title="2026 정읍동학마라톤 풀,하프,10km",
            location="unknown",
            link_url="https://example.com/region",
            event_date=date(2026, 10, 3),
        )

        row = MarathonEventMapper.to_row(event)

        self.assertEqual("전라북도 정읍시", row.region)

    def test_extract_distances_from_compact_title_patterns(self) -> None:
        event = MarathonEvent(
            date_text="2026-06-01",
            title="2026 송도 WALK & RUN하프,10km,5km,트레일런15km,WALK5,10,20km댕댕런3km",
            location="unknown",
            link_url="https://example.com/distances",
            event_date=date(2026, 6, 1),
        )

        row = MarathonEventMapper.to_row(event)

        self.assertEqual(
            ["3K", "5K", "10K", "15K", "20K", "HALF"],
            row.distances,
        )

    def test_set_closed_status_when_event_date_is_past(self) -> None:
        event = MarathonEvent(
            date_text="2000-01-01",
            title="히스토리 대회",
            location="서울특별시 송파구",
            link_url="https://example.com/history",
            event_date=date(2000, 1, 1),
        )

        row = MarathonEventMapper.to_row(event)

        self.assertEqual("CLOSED", row.status)


if __name__ == "__main__":
    unittest.main()
