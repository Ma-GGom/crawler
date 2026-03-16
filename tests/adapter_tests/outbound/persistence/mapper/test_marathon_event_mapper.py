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


if __name__ == "__main__":
    unittest.main()
