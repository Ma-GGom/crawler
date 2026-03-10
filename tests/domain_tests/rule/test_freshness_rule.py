from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.rule.freshness_rule import is_fresh_payload

KST = timezone(timedelta(hours=9), name="KST")


class FreshnessRuleTest(unittest.TestCase):
    def test_fresh_true(self) -> None:
        now = datetime.now(KST)
        self.assertTrue(is_fresh_payload(now - timedelta(seconds=10), now_kst=now))

    def test_stale_false(self) -> None:
        now = datetime.now(KST)
        self.assertFalse(is_fresh_payload(now - timedelta(minutes=5), now_kst=now))

    def test_naive_datetime_false(self) -> None:
        self.assertFalse(is_fresh_payload(datetime.now()))


if __name__ == "__main__":
    unittest.main()

