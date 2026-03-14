from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.mara1080_detail_client import Mara1080DetailClient


class Mara1080DetailClientTest(unittest.TestCase):
    def test_parse_detail_payload(self) -> None:
        payload = {
            "eventInfo": {
                "id": "250b9e58-2837-4479-ad5d-cd989951075f",
                "nameKr": "2026 전마협새해맞이마라톤대회",
                "startDate": "2026-01-04T09:00:00",
                "registDeadline": "2025-12-16T00:00:00",
                "eventsPageUrl": "https://mara1080.com/event/250b9e58-2837-4479-ad5d-cd989951075f",
            }
        }
        client = Mara1080DetailClient()

        detail = client.parse_detail_payload(
            payload,
            fallback_url="https://mara1080.com/event/250b9e58-2837-4479-ad5d-cd989951075f?color=blue",
        )

        self.assertIsNotNone(detail)
        self.assertEqual("2026-01-04", detail.event_date.isoformat())
        self.assertEqual("2025-12-16", detail.registration_end_date.isoformat())
        self.assertEqual(
            "~2025-12-16",
            detail.registration_period,
        )
        self.assertEqual(
            "https://mara1080.com/event/250b9e58-2837-4479-ad5d-cd989951075f",
            detail.official_website_url,
        )


if __name__ == "__main__":
    unittest.main()
