from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.rule.location_rule import normalize_region, resolve_event_region


class LocationRuleTest(unittest.TestCase):
    def test_map_district_only_to_full_region(self) -> None:
        self.assertEqual(
            "서울시 마포구",
            normalize_region("마포구"),
        )

    def test_keep_province_and_city(self) -> None:
        self.assertEqual(
            "경기도 하남시",
            normalize_region("경기도 하남시"),
        )

    def test_correct_mismatched_province_and_city(self) -> None:
        self.assertEqual(
            "강원도 춘천시",
            normalize_region("경기도 춘천시"),
        )

    def test_map_venue_keyword(self) -> None:
        self.assertEqual(
            "서울시 종로구",
            normalize_region("광화문광장"),
        )

    def test_map_olympic_park_without_online_call(self) -> None:
        with patch("domain.rule.location_rule.requests.get") as get_mock:
            self.assertEqual(
                "서울시 송파구",
                normalize_region("올림픽공원"),
            )
            get_mock.assert_not_called()

    def test_infer_city_from_bare_city_name(self) -> None:
        self.assertEqual(
            "강원도 강릉시",
            normalize_region("강릉 종합운동장"),
        )

    def test_return_unknown_when_only_province_exists(self) -> None:
        self.assertEqual("unknown", normalize_region("강원도"))

    def test_enrich_region_online_when_venue_not_mapped(self) -> None:
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = [
            {
                "address": {
                    "state": "서울특별시",
                    "borough": "성동구",
                }
            }
        ]

        with patch(
            "domain.rule.location_rule.requests.get",
            return_value=fake_response,
        ) as get_mock:
            self.assertEqual(
                "서울시 성동구",
                normalize_region("서울숲공원"),
            )
            get_mock.assert_called_once()

    def test_resolve_event_region_from_title_when_location_unknown(self) -> None:
        self.assertEqual(
            "전라북도 정읍시",
            resolve_event_region(
                "unknown",
                title="2026 정읍동학마라톤풀,하프,10km,5km",
            ),
        )

    def test_resolve_event_region_from_english_city_keyword(self) -> None:
        self.assertEqual(
            "부산시 해운대구",
            resolve_event_region(
                "장소 미정",
                title="2026 THE RACE BUSAN 10K",
            ),
        )

    def test_resolve_event_region_from_link_url(self) -> None:
        self.assertEqual(
            "경기도 김포시",
            resolve_event_region(
                "unknown",
                title="장소 미정",
                link_url="http://gimporun.com",
            ),
        )

    def test_resolve_event_region_from_known_official_host(self) -> None:
        self.assertEqual(
            "대구시 수성구",
            resolve_event_region(
                "unknown",
                title="영남일보 국제 하프마라톤",
                link_url="http://ynmarathon.kr/",
            ),
        )

    def test_resolve_event_region_from_link_page_content(self) -> None:
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.text = """
            <html>
              <body>
                <div>대회 안내</div>
                <p>장소: 인천광역시 연수구 송도센트럴파크</p>
              </body>
            </html>
        """

        with patch(
            "domain.rule.location_rule.requests.get",
            return_value=fake_response,
        ) as get_mock:
            self.assertEqual(
                "인천시 연수구",
                resolve_event_region(
                    "unknown",
                    title="2026 테스트 레이스",
                    link_url="https://example.com/event/1",
                ),
            )
            get_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
