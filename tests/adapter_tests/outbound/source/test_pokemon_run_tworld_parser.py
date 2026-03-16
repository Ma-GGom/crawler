from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adapter.outbound.source.pokemon_run_tworld_parser import PokemonRunTworldParser


class PokemonRunTworldParserTest(unittest.TestCase):
    def test_extract_pokemon_run_event(self) -> None:
        html = """
        <div>
          <h1>포켓몬 런 2026 in Seoul</h1>
          <p>일시/장소 2026년 5월 5일(화)/서울 뚝섬 한강공원</p>
          <p>예매 기간 2026년 3월 3일(화) 9시~3월 13일(금) 18시</p>
        </div>
        """
        parser = PokemonRunTworldParser(
            link_url="https://shop.tworld.co.kr/exhibition/view?exhibitionId=P00000498",
            official_website_url="https://pokemonkorea.co.kr/PokemonRUN2026/menu715",
        )

        events = parser.extract(html)

        self.assertEqual(1, len(events))
        event = events[0]
        self.assertEqual("포켓몬 런 2026", event.title)
        self.assertEqual("2026-05-05", event.event_date.isoformat())
        self.assertEqual("2026-03-03", event.registration_start_date.isoformat())
        self.assertEqual("2026-03-13", event.registration_end_date.isoformat())
        self.assertIn("뚝섬", event.location)
        self.assertEqual(
            "https://pokemonkorea.co.kr/PokemonRUN2026/menu715",
            event.official_website_url,
        )


if __name__ == "__main__":
    unittest.main()
