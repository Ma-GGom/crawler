from datetime import date
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.model.recurrence_watch import RecurrenceWatchSeed
from domain.rule.recurrence_watch_rule import (
    build_recurrence_watch_candidates,
    normalize_watch_title,
)


class RecurrenceWatchRuleTest(unittest.TestCase):
    def test_normalize_watch_title(self) -> None:
        self.assertEqual(
            "서울 마라톤",
            normalize_watch_title("2026 서울 마라톤 제 96회"),
        )

    def test_build_watch_candidates(self) -> None:
        seeds = [
            RecurrenceWatchSeed(
                title="2025 서울 마라톤",
                event_date=date(2025, 3, 16),
                source_name="seoul-marathon.com",
            ),
            RecurrenceWatchSeed(
                title="2026 서울 마라톤",
                event_date=date(2026, 3, 15),
                source_name="seoul-marathon.com",
            ),
            RecurrenceWatchSeed(
                title="2025 춘천마라톤",
                event_date=date(2025, 10, 27),
                source_name="chuncheon-source",
            ),
        ]

        candidates = build_recurrence_watch_candidates(
            seeds,
            today_kst=date(2026, 3, 14),
        )

        self.assertEqual(2, len(candidates))
        status_by_title = {
            candidate.sample_title: candidate.status for candidate in candidates
        }
        self.assertEqual("DETECTED", status_by_title["2026 서울 마라톤"])
        self.assertEqual("PENDING", status_by_title["2025 춘천마라톤"])


if __name__ == "__main__":
    unittest.main()
