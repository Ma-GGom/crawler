from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.run1080_parser import Run1080Parser


class Run1080ParserTest(unittest.TestCase):
    def test_extract_mara1080_events(self) -> None:
        html = """
        <div>
          <a href="https://mara1080.com/event/db8bfa91-d6de-4591-9f19-8f48da3adc7b">
            2026 금산 인삼 웰빙 마라톤대회
          </a>
          <a href="https://mara1080.com/event/DB8BFA91-D6DE-4591-9F19-8F48DA3ADC7B?color=blue">
            2026 금산 인삼 웰빙 마라톤대회
          </a>
          <a href="https://mara1080.com/event/29a34ee9-32a9-4a3b-b92f-37b3772cc183">
            2026 식품안전 마라톤 대회
          </a>
          <a href="https://mara1080.com/event/cc575d27-3e88-47a5-80e1-c17d4342d398">
            2026 제6회 케냐 마라톤 여행
          </a>
          <a href="javascript:miniOpen(1423);">
            2025 전마협 새해맞이 마라톤 대회
          </a>
          <a href="https://mara1080.com/event/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa">
            슈플라이트3 공동구매
          </a>
        </div>
        """
        parser = Run1080Parser(
            mini_url_template="http://www.run1080.com/new/mini/index.php?code={code}",
            event_url_template="https://mara1080.com/event/{event_id}",
        )

        events = parser.extract(html)

        self.assertEqual(4, len(events))
        self.assertEqual("2026 금산 인삼 웰빙 마라톤대회", events[0].title)
        self.assertEqual("금산", events[0].location)
        self.assertEqual(
            "https://mara1080.com/event/db8bfa91-d6de-4591-9f19-8f48da3adc7b",
            events[0].link_url,
        )
        self.assertEqual("2026년", events[0].date_text)
        self.assertEqual(
            "http://www.run1080.com/new/mini/index.php?code=1423",
            events[3].link_url,
        )
        self.assertEqual("2025-01-01", events[3].event_date.isoformat())


if __name__ == "__main__":
    unittest.main()
