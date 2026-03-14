from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.runnext_parser import RunNextParser


class RunNextParserTest(unittest.TestCase):
    def test_extract_events_from_categorized_payload(self) -> None:
        html = """
        {
          "success": true,
          "data": {
            "approvedList": [
              {
                "id": "a1",
                "name": "\\uc81c1\\ud68c \\ub85c\\uceec \\ub9c8\\ub77c\\ud1a4",
                "region": "\\uac15\\uc6d0",
                "location": "\\uac15\\ub989 \\uc885\\ud569\\uc6b4\\ub3d9\\uc7a5",
                "distances": ["5km", "10km"],
                "date": "2026-06-13T15:00:00.000Z",
                "registrationStart": "2026-02-01T15:00:00.000Z",
                "registrationEnd": "2026-04-01T14:59:59.999Z",
                "website": "https://example.com/race-a1"
              }
            ],
            "openingSoonList": [
              {
                "id": "a1",
                "name": "\\uc911\\ubcf5 \\uc774\\ubca4\\ud2b8",
                "region": "\\uac15\\uc6d0",
                "location": "\\uac15\\ub989",
                "date": "2026-06-13T15:00:00.000Z",
                "registrationStart": "2026-02-01T15:00:00.000Z",
                "registrationEnd": "2026-04-01T14:59:59.999Z",
                "website": "https://example.com/race-a1"
              }
            ],
            "openForRegistrationList": [
              {
                "id": "b2",
                "name": "\\uc81c2\\ud68c \\uc18c\\ub3c4\\uc2dc \\ub7f0",
                "region": "\\uc804\\ubd81",
                "location": "\\uc804\\uc8fc \\uc885\\ud569\\uacbd\\uae30\\uc7a5",
                "distances": ["10km"],
                "date": "2026-07-01T15:00:00.000Z",
                "registrationStart": "2026-03-01T15:00:00.000Z",
                "registrationEnd": "2026-05-01T14:59:59.999Z",
                "website": "https://example.com/race-b2"
              }
            ]
          }
        }
        """
        parser = RunNextParser()

        events = parser.extract(html)

        self.assertEqual(2, len(events))
        self.assertEqual("\uc81c1\ud68c \ub85c\uceec \ub9c8\ub77c\ud1a4", events[0].title)
        self.assertEqual("2026-06-13", events[0].event_date.isoformat())
        self.assertEqual("2026-02-01", events[0].registration_start_date.isoformat())
        self.assertEqual("2026-04-01", events[0].registration_end_date.isoformat())
        self.assertEqual("https://example.com/race-a1", events[0].official_website_url)
        self.assertEqual("\uc81c2\ud68c \uc18c\ub3c4\uc2dc \ub7f0", events[1].title)


if __name__ == "__main__":
    unittest.main()
