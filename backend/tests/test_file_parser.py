import unittest
from pathlib import Path

from app.services import file_parser


class ParseToTextTruncateTest(unittest.TestCase):
    def setUp(self):
        self.info = file_parser.save_upload("big.txt", ("X" * 25000).encode("utf-8"))
        self.file_id = self.info["file_id"]

    def tearDown(self):
        path = Path(self.info["path"])
        if path.exists():
            path.unlink()

    def test_default_does_not_truncate(self):
        text = file_parser.parse_to_text(self.file_id)
        self.assertNotIn("已截断", text)
        self.assertGreaterEqual(len(text), 25000)

    def test_positive_max_chars_truncates(self):
        text = file_parser.parse_to_text(self.file_id, max_chars=100)
        self.assertIn("已截断", text)
        self.assertTrue(text.startswith("X" * 100))


if __name__ == "__main__":
    unittest.main()
