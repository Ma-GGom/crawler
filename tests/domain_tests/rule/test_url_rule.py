from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.rule.url_rule import normalize_url


class UrlRuleTest(unittest.TestCase):
    def test_normalize_url_remove_tracking_query(self) -> None:
        raw = "https://Example.com/race/apply/?utm_source=abc&gclid=123&id=42"
        normalized = normalize_url(raw)
        self.assertEqual("https://example.com/race/apply?id=42", normalized)

    def test_normalize_url_strip_default_port(self) -> None:
        self.assertEqual(
            "https://example.com/path",
            normalize_url("https://example.com:443/path/"),
        )


if __name__ == "__main__":
    unittest.main()
