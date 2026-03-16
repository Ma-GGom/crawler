from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.jtbc_marathon_parser import JtbcMarathonParser


class JtbcMarathonParserTest(unittest.TestCase):
    def test_extract_official_event(self) -> None:
        html = """
        <div>
          NAME 2026 JTBC \uc11c\uc6b8\ub9c8\ub77c\ud1a4
          DA TE 2026\ub144 11\uc6d4 1\uc77c (\uc77c\uc694\uc77c)
          PLACE \uc0c1\uc554\uc6d4\ub4dc\ucef5\uacbd\uae30\uc7a5
        </div>
        """
        parser = JtbcMarathonParser(official_url="https://marathon.jtbc.com/")

        events = parser.extract(html)

        self.assertEqual(1, len(events))
        self.assertEqual("2026 JTBC \uc11c\uc6b8\ub9c8\ub77c\ud1a4", events[0].title)
        self.assertEqual("\uc0c1\uc554\uc6d4\ub4dc\ucef5\uacbd\uae30\uc7a5", events[0].location)
        self.assertEqual("https://marathon.jtbc.com/", events[0].link_url)
        self.assertEqual("2026-11-01", events[0].event_date.isoformat())


if __name__ == "__main__":
    unittest.main()
