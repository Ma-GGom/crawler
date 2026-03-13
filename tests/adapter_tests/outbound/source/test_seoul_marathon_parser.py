from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.seoul_marathon_parser import SeoulMarathonParser


class SeoulMarathonParserTest(unittest.TestCase):
    def test_extract_official_event(self) -> None:
        html = """
        <div>
          \ub300\ud68c\uba85 2026 \uc11c\uc6b8\ub9c8\ub77c\ud1a4 \uacb8 \uc81c 96\ud68c \ub3d9\uc544\ub9c8\ub77c\ud1a4
          \ub300\ud68c\uc77c 2026\ub144 3\uc6d4 15\uc77c \uc77c\uc694\uc77c
          \uc9d1\uacb0\uc7a5\uc18c \ud480\ucf54\uc2a4: \uad11\ud654\ubb38 \uad11\uc7a5 10km: \uc7a0\uc2e4\uc885\ud569\uc6b4\ub3d9\uc7a5
        </div>
        """
        parser = SeoulMarathonParser()

        events = parser.extract(html)

        self.assertEqual(1, len(events))
        self.assertEqual(
            "2026 \uc11c\uc6b8\ub9c8\ub77c\ud1a4 \uacb8 \uc81c 96\ud68c \ub3d9\uc544\ub9c8\ub77c\ud1a4",
            events[0].title,
        )
        self.assertEqual("\uad11\ud654\ubb38 \uad11\uc7a5", events[0].location)
        self.assertEqual("https://seoul-marathon.com/90", events[0].link_url)
        self.assertEqual("2026-03-15", events[0].event_date.isoformat())


if __name__ == "__main__":
    unittest.main()

