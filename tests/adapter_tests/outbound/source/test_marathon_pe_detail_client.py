from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.marathon_pe_detail_client import MarathonPeDetailClient


class MarathonPeDetailClientTest(unittest.TestCase):
    def test_parse_detail_html(self) -> None:
        html = """
        <table>
          <tr><td>대회명</td><td>테스트 대회</td></tr>
          <tr><td>접수기간</td><td>2026년1월18일~2026년2월18일</td></tr>
          <tr>
            <td>홈페이지</td>
            <td>http://<a href="http://marathon.jtbc.com/" target="_new">marathon.jtbc.com/</a></td>
          </tr>
        </table>
        """
        client = MarathonPeDetailClient()

        detail = client.parse_detail_html(html, base_url="http://www.roadrun.co.kr/schedule/view.php?no=1")

        self.assertEqual("2026년1월18일~2026년2월18일", detail.registration_period)
        self.assertEqual("http://marathon.jtbc.com/", detail.official_website_url)
        self.assertEqual("2026-01-18", detail.registration_start_date.isoformat())
        self.assertEqual("2026-02-18", detail.registration_end_date.isoformat())


if __name__ == "__main__":
    unittest.main()

