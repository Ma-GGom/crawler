from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.seoul_marathon_detail_client import SeoulMarathonDetailClient


class SeoulMarathonDetailClientTest(unittest.TestCase):
    def test_parse_detail_html(self) -> None:
        html = """
        <div>
          2026 \uc11c\uc6b8\ub9c8\ub77c\ud1a4 \uc811\uc218 \uc77c\uc815
          \uc811\uc218\ud558\uae30 \u2192 5\uc6d4 13\uc77c(\ud654) 10\uc2dc ~ 26\uc77c(\uc6d4) 15\uc2dc
          \uc11c\uc6b8\ub9c8\ub77c\ud1a4 \uc6b0\uc120 \uc811\uc218 6\uc6d4 2\uc77c(\uc6d4) 19\uc2dc~6\uc77c(\uae08) 17\uc2dc
        </div>
        """
        client = SeoulMarathonDetailClient()

        detail = client.parse_detail_html(html)

        self.assertEqual("https://seoul-marathon.com/", detail.official_website_url)
        self.assertEqual("2026-05-13", detail.registration_start_date.isoformat())
        self.assertEqual("2026-05-26", detail.registration_end_date.isoformat())
        self.assertTrue(
            detail.registration_period.startswith("5\uc6d4 13\uc77c")
        )


if __name__ == "__main__":
    unittest.main()

