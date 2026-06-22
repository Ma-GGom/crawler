from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.naver_search_parser import NaverSearchParser


class NaverSearchParserTest(unittest.TestCase):
    def test_extract_marathon_candidates_from_search_items(self) -> None:
        payload = """
        {
          "results": [
            {
              "query": "마라톤 일정",
              "items": [
                {
                  "title": "<b>서울마라톤</b> 2026.11.01 참가 안내",
                  "description": "서울특별시 성동구 일대 코스",
                  "originallink": "https://seoul-marathon.example.com/notice/1",
                  "link": "https://search.naver.com/redirect?target=1"
                },
                {
                  "title": "머신 러닝 입문 세미나",
                  "description": "개발자 대상 교육",
                  "originallink": "https://example.com/ml",
                  "link": "https://example.com/ml"
                },
                {
                  "title": "산리오런 서울 5월 9일 개최",
                  "description": "올림픽공원",
                  "originallink": "https://event.example.com/sanrio-run",
                  "link": "https://event.example.com/sanrio-run"
                },
                {
                  "title": "산리오런 서울 5월 9일 개최",
                  "description": "중복 데이터",
                  "originallink": "https://event.example.com/sanrio-run",
                  "link": "https://event.example.com/sanrio-run"
                }
              ]
            }
          ]
        }
        """
        parser = NaverSearchParser()

        events = parser.extract(payload)

        self.assertEqual(2, len(events))
        self.assertEqual("서울마라톤 2026.11.01 참가 안내", events[0].title)
        self.assertEqual("2026-11-01", events[0].event_date.isoformat())
        self.assertEqual("서울특별시 성동구", events[0].location)
        self.assertEqual("https://seoul-marathon.example.com/notice/1", events[0].link_url)
        self.assertEqual("산리오런 서울 5월 9일 개최", events[1].title)
        self.assertEqual("서울", events[1].location)

    def test_return_empty_when_payload_is_invalid(self) -> None:
        parser = NaverSearchParser()
        self.assertEqual([], parser.extract("not-json"))


if __name__ == "__main__":
    unittest.main()
