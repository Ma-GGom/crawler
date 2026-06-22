from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.dtrail_parser import DtrailParser


class DtrailParserTest(unittest.TestCase):
    def test_extract_event_from_ocr_text(self) -> None:
        html = """
        <html>
          <head><title>Dtrail | 금강울트라마라톤</title></head>
          <body>
            <img src="https://cdn.example.com/kumgang-poster.png" />
            <img src="/static/info.png" />
          </body>
        </html>
        """

        ocr_by_url = {
            "https://cdn.example.com/kumgang-poster.png": (
                "금강울트라마라톤\n"
                "대회일 2026년 10월 03일\n"
                "접수기간 2026.06.01 ~ 2026.08.31\n"
                "장소 충청남도 공주시 금강신관공원"
            ),
            "https://example.com/static/info.png": "100K 50K 25K",
        }

        parser = DtrailParser(
            source_url="https://example.com/dtrail",
            link_url="https://example.com/dtrail",
            official_website_url="https://example.com/dtrail",
            image_text_reader=lambda image_url: ocr_by_url.get(image_url),
            max_images=10,
        )

        events = parser.extract(html)

        self.assertEqual(1, len(events))
        event = events[0]
        self.assertEqual("금강울트라마라톤", event.title)
        self.assertEqual("2026-10-03", event.event_date.isoformat())
        self.assertEqual("2026-06-01", event.registration_start_date.isoformat())
        self.assertEqual("2026-08-31", event.registration_end_date.isoformat())
        self.assertIn("충청남도 공주시", event.location)
        self.assertEqual("https://example.com/dtrail", event.link_url)

    def test_use_unknown_location_when_location_is_missing(self) -> None:
        html = """
        <html>
          <head><title>Dtrail | 트레일레이스</title></head>
          <body>
            <img src="https://cdn.example.com/poster.png" />
          </body>
        </html>
        """

        parser = DtrailParser(
            source_url="https://example.com/dtrail",
            image_text_reader=lambda _: "트레일레이스\n대회일 2026-09-12",
        )

        events = parser.extract(html)

        self.assertEqual(1, len(events))
        self.assertEqual("unknown", events[0].location)


if __name__ == "__main__":
    unittest.main()
