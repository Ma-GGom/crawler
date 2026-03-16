from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.rule.rare_marathon_rule import match_rare_marathon_keywords


class RareMarathonRuleTest(unittest.TestCase):
    def test_match_brand_run_keyword(self) -> None:
        title = "2026 KB 스타 런 서울"
        matched = match_rare_marathon_keywords(title)

        self.assertIn("kb스타런", matched)

    def test_match_major_alias_keyword(self) -> None:
        title = "2026 중앙서울마라톤 접수 안내"
        matched = match_rare_marathon_keywords(title)

        self.assertIn("중앙서울마라톤", matched)

    def test_match_major_short_keyword(self) -> None:
        title = "2026 제마 얼리버드 오픈"
        matched = match_rare_marathon_keywords(title)

        self.assertIn("제마", matched)

    def test_return_empty_for_normal_event(self) -> None:
        title = "2026 가을 건강 달리기 대회"
        matched = match_rare_marathon_keywords(title)

        self.assertEqual([], matched)


if __name__ == "__main__":
    unittest.main()
