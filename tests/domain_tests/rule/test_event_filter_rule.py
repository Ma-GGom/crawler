from datetime import date
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.model.marathon_event import MarathonEvent
from domain.rule.event_filter_rule import is_actionable_event


class EventFilterRuleTest(unittest.TestCase):
    def test_closed_registration_future_event_is_actionable(self) -> None:
        event = MarathonEvent(
            date_text="3/20(금)",
            title="테스트",
            location="서울",
            link_url="http://example.com",
            registration_end_date=date(2026, 2, 1),
            event_date=date(2026, 3, 20),
        )
        self.assertTrue(is_actionable_event(event, today_kst=date(2026, 3, 10)))

    def test_past_event_is_not_actionable(self) -> None:
        event = MarathonEvent(
            date_text="3/1(일)",
            title="테스트",
            location="서울",
            link_url="http://example.com",
            event_date=date(2026, 3, 1),
        )
        self.assertFalse(is_actionable_event(event, today_kst=date(2026, 3, 10)))

    def test_future_event_is_actionable(self) -> None:
        event = MarathonEvent(
            date_text="4/1(수)",
            title="테스트",
            location="서울",
            link_url="http://example.com",
            registration_end_date=date(2026, 3, 25),
            event_date=date(2026, 4, 1),
        )
        self.assertTrue(is_actionable_event(event, today_kst=date(2026, 3, 10)))


if __name__ == "__main__":
    unittest.main()


