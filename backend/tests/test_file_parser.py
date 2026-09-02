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


class ExcelFallbackTest(unittest.TestCase):
    def test_xls_mms_parses_with_xlrd(self):
        path = Path("/workspace/doc/EO035/EO035药理测试原始数据/ADME性质/D-RF-2024031105(HW350001)-MMS-20240315.xls")
        sheets = file_parser._read_excel_sheets(path)
        self.assertTrue(sheets)

    def test_wrn_custom_docprops_parses_readonly(self):
        path = Path(
            "/workspace/doc/EO035/EO035药理测试原始数据/酶活IC50原始数据/"
            "Report_RFP-2024091402_WRN(517-1238)_ATP preincubation_FI_IC50_20240918.xlsx"
        )
        sheets = file_parser._read_excel_sheets(path)
        self.assertTrue(sheets)


if __name__ == "__main__":
    unittest.main()
