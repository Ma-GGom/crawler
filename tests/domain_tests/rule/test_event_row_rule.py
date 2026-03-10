from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.rule.event_row_rule import has_valid_date_shape, is_header_row


class EventRowRuleTest(unittest.TestCase):
    def test_header_row(self) -> None:
        self.assertTrue(is_header_row("일자"))
        self.assertFalse(is_header_row("3/1(일)"))

    def test_date_shape(self) -> None:
        self.assertTrue(has_valid_date_shape("3/1(일)"))
        self.assertTrue(has_valid_date_shape("12/31(수)"))
        self.assertFalse(has_valid_date_shape("2026-03-01"))
        self.assertFalse(has_valid_date_shape("종목필터"))


if __name__ == "__main__":
    unittest.main()

