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


class ExcelDisplayFormatTest(unittest.TestCase):
    def test_decimal_places_from_format(self):
        self.assertEqual(file_parser.excel_decimal_places("0.000_ "), 3)
        self.assertEqual(file_parser.excel_decimal_places("0.00_ "), 2)
        self.assertEqual(file_parser.excel_decimal_places("0.0"), 1)
        self.assertEqual(file_parser.excel_decimal_places("0"), 0)
        self.assertEqual(file_parser.excel_decimal_places("0.00%"), 2)
        self.assertIsNone(file_parser.excel_decimal_places("General"))

    def test_format_follows_display_not_raw(self):
        self.assertEqual(file_parser.format_excel_number(774.076333333333, "0.000_ "), "774.076")
        self.assertEqual(file_parser.format_excel_number(0.25, "0.00_ "), "0.25")
        self.assertEqual(file_parser.format_excel_number(0.083, "0.000_ "), "0.083")
        self.assertEqual(file_parser.format_excel_number(12.3456, "0.00"), "12.35")
        self.assertEqual(file_parser.format_excel_number(0.1234, "0.00%"), "12.34%")
        self.assertEqual(file_parser.format_excel_number(101.0, "General"), "101")
        self.assertEqual(file_parser.format_excel_number(0.2046, "General"), "0.2046")
        self.assertEqual(file_parser.format_excel_number(1.23e-5, "0.00E+00"), "1.23E-05")

    def test_monkey_summary_uses_cell_decimals(self):
        path = Path(
            "/workspace/doc/EO035/EO035药理测试原始数据/犬和猴PK数据/"
            "08065-25011-NG_HW356009-P1食蟹猴药代_报告_终稿_250312.xlsx"
        )
        text = file_parser._parse_excel(path)
        self.assertIn("774.076", text)
        self.assertNotIn("774.076333333", text)
        self.assertIn("234.445", text)
        self.assertNotIn("234.445225616", text)


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
