from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.rule.distance_rule import extract_distances_from_title


class DistanceRuleTest(unittest.TestCase):
    def test_extract_half_full_and_numeric(self) -> None:
        self.assertEqual(
            ["5K", "10K", "HALF", "FULL"],
            extract_distances_from_title("정읍동학마라톤 풀,하프,10km,5km"),
        )

    def test_extract_series_with_trailing_km(self) -> None:
        self.assertEqual(
            ["3K", "5K", "10K", "20K"],
            extract_distances_from_title("WALK5,10,20km 댕댕런3km"),
        )

    def test_map_legacy_full_half_numeric_values(self) -> None:
        self.assertEqual(
            ["HALF", "FULL"],
            extract_distances_from_title("42.195km / 21.0975km"),
        )

    def test_extract_ultra_distances(self) -> None:
        self.assertEqual(
            ["50K", "100K"],
            extract_distances_from_title("빛고을 울트라마라톤100km,50km"),
        )


if __name__ == "__main__":
    unittest.main()
