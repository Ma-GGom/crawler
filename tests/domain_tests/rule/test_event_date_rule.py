from datetime import date
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.rule.event_date_rule import infer_event_date_from_list_text


class EventDateRuleTest(unittest.TestCase):
    def test_infer_from_list_text(self) -> None:
        inferred = infer_event_date_from_list_text("3/20(금)", today_kst=date(2026, 3, 10))
        self.assertEqual(date(2026, 3, 20), inferred)

    def test_invalid_text_returns_none(self) -> None:
        inferred = infer_event_date_from_list_text("잘못된값", today_kst=date(2026, 3, 10))
        self.assertIsNone(inferred)


if __name__ == "__main__":
    unittest.main()


