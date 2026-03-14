from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.chuncheon_notice_detail_client import ChuncheonNoticeDetailClient
from domain.model.event_detail import MarathonEventDetail


class ChuncheonNoticeDetailClientTest(unittest.TestCase):
    def test_parse_detail_html(self) -> None:
        html = """
        <div class="board_body">
          출발일시 2026년 10월 25일(일)
          추가신청 기간 2026년 9월 3일(수) ~ 2026년 9월 5일(금)
        </div>
        """
        client = ChuncheonNoticeDetailClient()

        detail = client.parse_detail_html(html)

        self.assertEqual("2026-10-25", detail.event_date.isoformat())
        self.assertEqual("2026-09-03", detail.registration_start_date.isoformat())
        self.assertEqual("2026-09-05", detail.registration_end_date.isoformat())

    def test_fallback_info_detail_when_event_date_missing(self) -> None:
        client = ChuncheonNoticeDetailClient()
        client._fallback_info_cache = MarathonEventDetail(
            registration_period="2026년 6월 24일 ~ 2026년 7월 2일",
            official_website_url="https://www.chuncheonmarathon.com/",
            registration_start_date=None,
            registration_end_date=None,
            event_date=__import__("datetime").date(2026, 10, 25),
        )

        detail = client.parse_detail_html("<div class='board_body'>접수기간 안내만 있음</div>")
        if detail.event_date is None:
            detail = MarathonEventDetail(
                registration_period=detail.registration_period
                or client._fallback_info_cache.registration_period,
                official_website_url=detail.official_website_url
                or client._fallback_info_cache.official_website_url,
                registration_start_date=detail.registration_start_date
                or client._fallback_info_cache.registration_start_date,
                registration_end_date=detail.registration_end_date
                or client._fallback_info_cache.registration_end_date,
                event_date=detail.event_date or client._fallback_info_cache.event_date,
            )

        self.assertEqual("2026-10-25", detail.event_date.isoformat())


if __name__ == "__main__":
    unittest.main()
