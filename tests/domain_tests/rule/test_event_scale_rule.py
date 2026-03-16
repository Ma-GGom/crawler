from datetime import date
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.model.marathon_event import MarathonEvent
from domain.rule.event_scale_rule import (
    EVENT_SCALE_MAJOR,
    EVENT_SCALE_SMALL,
    EVENT_SCALE_UNKNOWN,
    classify_event_scale,
)


class EventScaleRuleTest(unittest.TestCase):
    def test_classify_major_event(self) -> None:
        event = MarathonEvent(
            date_text="2026-11-01",
            title="2026 JTBC 서울마라톤",
            location="서울",
            link_url="https://example.com",
            event_date=date(2026, 11, 1),
        )

        self.assertEqual(EVENT_SCALE_MAJOR, classify_event_scale(event))

    def test_classify_small_event(self) -> None:
        event = MarathonEvent(
            date_text="2026-09-01",
            title="가을 무료 초청 훈련 런",
            location="서울",
            link_url="https://example.com",
            event_date=date(2026, 9, 1),
        )

        self.assertEqual(EVENT_SCALE_SMALL, classify_event_scale(event))

    def test_classify_unknown_event(self) -> None:
        event = MarathonEvent(
            date_text="2026-10-01",
            title="가을 건강 달리기",
            location="서울",
            link_url="https://example.com",
            event_date=date(2026, 10, 1),
        )

        self.assertEqual(EVENT_SCALE_UNKNOWN, classify_event_scale(event))


if __name__ == "__main__":
    unittest.main()
