from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.onoffmix_parser import OnOffMixParser


class OnOffMixParserTest(unittest.TestCase):
    def test_extract_marathon_related_events(self) -> None:
        html = """
        <ul class="event_lists thumbnail_mode">
          <li>
            <article class="event_area event_main">
              <a href="/event/338383" target="_blank">
                <div class="event_thumbnail">
                  <img alt="서울 라이프마라톤 2026 OPEN" />
                </div>
                <div class="event_info_area">
                  <div class="title_area">
                    <h5 class="title">서울 라이프 <strong>마라톤</strong> 2026 OPEN</h5>
                  </div>
                  <div class="event_info">
                    <div class="date">5.2 (토)</div>
                  </div>
                </div>
                <div class="list_date_place">
                  <div class="wrapping">
                    <span class="date">2026.5.2 (토) 0:00 ~ 23:59</span>
                    <span class="place">경기도 하남시</span>
                  </div>
                </div>
              </a>
            </article>
          </li>
          <li>
            <article class="event_area event_main">
              <a href="/event/339004" target="_blank">
                <div class="event_info_area">
                  <div class="title_area">
                    <h5 class="title">연극 초대 이벤트</h5>
                  </div>
                  <div class="event_info">
                    <div class="date">3.10 (화)</div>
                  </div>
                </div>
                <div class="list_date_place">
                  <div class="wrapping">
                    <span class="date">2026.3.10 (화) 19:30 ~ 21:30</span>
                    <span class="place">서울특별시 서초구</span>
                  </div>
                </div>
              </a>
            </article>
          </li>
          <li>
            <article class="event_area event_main">
              <a href="/event/340001" target="_blank">
                <div class="event_info_area">
                  <div class="title_area">
                    <h5 class="title">산리오런 서울 2026</h5>
                  </div>
                </div>
                <div class="list_date_place">
                  <div class="wrapping">
                    <span class="date">2026.6.1 (월) 09:00 ~ 13:00</span>
                    <span class="place">서울특별시 잠실</span>
                  </div>
                </div>
              </a>
            </article>
          </li>
          <li>
            <article class="event_area event_main">
              <a href="/event/340002" target="_blank">
                <div class="event_info_area">
                  <div class="title_area">
                    <h5 class="title">브랜드 런칭 파티 2026</h5>
                  </div>
                </div>
                <div class="list_date_place">
                  <div class="wrapping">
                    <span class="date">2026.6.2 (화) 19:00 ~ 21:00</span>
                    <span class="place">서울특별시 성수동</span>
                  </div>
                </div>
              </a>
            </article>
          </li>
          <li>
            <article class="event_area event_main">
              <a href="/event/338383" target="_blank">
                <div class="event_info_area">
                  <div class="title_area">
                    <h5 class="title">서울 라이프 마라톤 2026 OPEN</h5>
                  </div>
                </div>
                <div class="list_date_place">
                  <div class="wrapping">
                    <span class="date">2026.5.2 (토) 0:00 ~ 23:59</span>
                    <span class="place">경기도 하남시</span>
                  </div>
                </div>
              </a>
            </article>
          </li>
        </ul>
        """
        parser = OnOffMixParser()

        events = parser.extract(html)

        self.assertEqual(2, len(events))
        self.assertEqual("서울 라이프 마라톤 2026 OPEN", events[0].title)
        self.assertEqual("5.2 (토)", events[0].date_text)
        self.assertEqual("경기도 하남시", events[0].location)
        self.assertEqual("https://www.onoffmix.com/event/338383", events[0].link_url)
        self.assertEqual("2026-05-02", events[0].event_date.isoformat())
        self.assertEqual("산리오런 서울 2026", events[1].title)
        self.assertEqual("https://www.onoffmix.com/event/340001", events[1].link_url)


if __name__ == "__main__":
    unittest.main()
