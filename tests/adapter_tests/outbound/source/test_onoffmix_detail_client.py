from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.onoffmix_detail_client import OnOffMixDetailClient


class OnOffMixDetailClientTest(unittest.TestCase):
    def test_parse_detail_html(self) -> None:
        html = """
        <html>
          <body>
            <a href="https://lifemarathon.co.kr/" class="btn_submit">신청하기 (외부접수)</a>
            <script>
              var GTM_JSON_STRING_VIEW_EVENT_DETAIL = {
                "eventStartDate":"2026-05-02 00:00:00",
                "outLinkUrl":"https://lifemarathon.co.kr/"
              };
            </script>
          </body>
        </html>
        """
        client = OnOffMixDetailClient()

        detail = client.parse_detail_html(html)

        self.assertEqual("https://lifemarathon.co.kr/", detail.official_website_url)
        self.assertEqual("2026-05-02", detail.event_date.isoformat())


if __name__ == "__main__":
    unittest.main()
