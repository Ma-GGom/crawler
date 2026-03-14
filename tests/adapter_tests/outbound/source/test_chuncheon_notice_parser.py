from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.chuncheon_notice_parser import ChuncheonNoticeParser


class ChuncheonNoticeParserTest(unittest.TestCase):
    def test_extract_target_notice_rows(self) -> None:
        html = """
        <table>
          <tr>
            <th>번호</th><th>제목</th><th>작성자</th><th>작성일</th><th>조회</th>
          </tr>
          <tr>
            <td>10</td>
            <td><a href="../bbs/view_cached.html?b_bbs_id=10005&pn=1&num=68&pbranch=">2026 춘천마라톤 추가 참가신청 일정 안내</a></td>
            <td>운영자</td>
            <td>2026.03.12</td>
            <td>100</td>
          </tr>
          <tr>
            <td>9</td>
            <td><a href="../bbs/view_cached.html?b_bbs_id=10005&pn=1&num=67&pbranch=">개인정보처리방침 개정 안내</a></td>
            <td>운영자</td>
            <td>2026.03.01</td>
            <td>50</td>
          </tr>
        </table>
        """
        parser = ChuncheonNoticeParser()

        events = parser.extract(html)

        self.assertEqual(1, len(events))
        self.assertEqual("2026.03.12", events[0].date_text)
        self.assertIn("추가 참가신청 일정 안내", events[0].title)
        self.assertTrue(events[0].link_url.startswith("https://board.chosun.com/"))


if __name__ == "__main__":
    unittest.main()
