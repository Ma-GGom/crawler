from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.marathon_pe_parser import MarathonPeParser


class MarathonPeParserTest(unittest.TestCase):
    def test_extract_only_event_rows(self) -> None:
        html = """
        <table>
          <tr><td>일자</td><td>대회명</td><td>장소</td><td>주최</td></tr>
          <tr>
            <td>3/1(일)</td>
            <td><a href="view.php?no=1">테스트 마라톤10km</a></td>
            <td>서울</td>
            <td>주최A</td>
          </tr>
          <tr>
            <td>종목필터</td>
            <td>필터UI</td>
            <td>필터UI</td>
            <td>필터UI</td>
          </tr>
        </table>
        """
        parser = MarathonPeParser(detail_base_url="http://www.roadrun.co.kr/schedule/")

        events = parser.extract(html)

        self.assertEqual(1, len(events))
        self.assertEqual("3/1(일)", events[0].date_text)
        self.assertEqual("테스트 마라톤10km", events[0].title)
        self.assertEqual("서울", events[0].location)
        self.assertEqual("http://www.roadrun.co.kr/schedule/view.php?no=1", events[0].link_url)

    def test_extract_javascript_link_to_detail_url(self) -> None:
        html = """
        <table>
          <tr>
            <td>3/2(월)</td>
            <td>
              <a href="javascript:open_window('win', 'view.php?no=41259', 0, 0, 550, 700, 0, 0, 0, 1, 0)">
                테스트 마라톤2
              </a>
            </td>
            <td>부산</td>
            <td>주최B</td>
          </tr>
        </table>
        """
        parser = MarathonPeParser(detail_base_url="http://www.roadrun.co.kr/schedule/")

        events = parser.extract(html)

        self.assertEqual(1, len(events))
        self.assertEqual("http://www.roadrun.co.kr/schedule/view.php?no=41259", events[0].link_url)


if __name__ == "__main__":
    unittest.main()

