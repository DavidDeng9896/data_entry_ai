import unittest
from pathlib import Path

from app.schemas import ColumnDef
from app.services import file_parser
from app.services.ai_service import _is_pk_target
from app.services.pk_extract import focus_content_for_model, mock_extract_pk

COLS = [
    ColumnDef(field="cpds_id", title="ID"),
    ColumnDef(field="iv_1mpk_cl_l_h_kg", title="CL"),
    ColumnDef(field="iv_1mpk_vss_l_kg", title="Vss"),
    ColumnDef(field="iv_1mpk_auc0_t_h_ng_ml", title="AUC"),
    ColumnDef(field="iv_1mpk_t1_2_hr", title="T12"),
    ColumnDef(field="po_5_mpk_cmax_ng_ml", title="Cmax"),
    ColumnDef(field="po_5_mpk_tmax_hr", title="Tmax"),
    ColumnDef(field="po_5_mpk_auc0_t_h_ng_ml", title="POAUC"),
    ColumnDef(field="po_5_mpk_t1_2_hr", title="POT12"),
    ColumnDef(field="po_5_mpk_pct_f", title="F"),
]

FOLDER = Path("/workspace/doc/EO035/EO035药理测试原始数据/犬和猴PK数据")
RAT_FOLDER = Path("/workspace/doc/EO035/EO035药理测试原始数据/大鼠PK数据")


def _parse(name: str, folder: Path = FOLDER) -> str:
    p = folder / name
    info = file_parser.save_upload(p.name, p.read_bytes())
    return file_parser.parse_to_text(info["file_id"], max_chars=0)


def _parse_glob(folder: Path, pattern: str) -> str:
    matches = list(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(pattern)
    p = matches[0]
    info = file_parser.save_upload(p.name, p.read_bytes())
    return file_parser.parse_to_text(info["file_id"], max_chars=0)


class PkExtractTest(unittest.TestCase):
    def test_focus_drops_raw_data(self):
        text = _parse("DM-RF-2025022001（HW350003A)DPK检测报告.xlsx")
        focused = focus_content_for_model(text)
        self.assertIn("结果汇总", focused)
        self.assertNotIn("原始数据", focused)
        self.assertLess(len(focused), len(text) / 2)

    def test_rat_keeps_pk_param_sheet_without_space(self):
        """普瑞昇大鼠报告：有结果汇总时仍要送 PK参数 页（无空格），不能只留封面。"""
        text = _parse_glob(RAT_FOLDER, "*2025020702*")
        self.assertIn("### Sheet: PK参数", text)
        self.assertIn("### Sheet: 结果汇总", text)
        focused = focus_content_for_model(text)
        self.assertIn("### Sheet: PK参数", focused)
        self.assertIn("### Sheet: 结果汇总", focused)
        self.assertIn("Cl_obs", focused)
        self.assertNotIn("### Sheet: 原始数据", focused)
        self.assertNotIn("### Sheet: 试验设计", focused)

    def test_focus_synthetic_pk_param_no_space_with_summary(self):
        text = "\n".join([
            "### Sheet: 封面",
            "普瑞昇",
            "### Sheet: 结果汇总",
            "表5 Mean CL",
            "### Sheet: PK参数",
            "Cl_obs 0.70",
            "### Sheet: 原始数据",
            "peak area",
            "### Sheet: 试验设计",
            "SD 大鼠",
        ])
        focused = focus_content_for_model(text)
        self.assertIn("PK参数", focused)
        self.assertIn("Cl_obs", focused)
        self.assertIn("结果汇总", focused)
        self.assertNotIn("原始数据", focused)
        self.assertNotIn("试验设计", focused)

    def test_monkey_focus_fits_one_chunk(self):
        from app.services.ai_service import split_file_chunks
        text = _parse("08065-25011-NG_HW356009-P1食蟹猴药代_报告_终稿_250312.xlsx")
        focused = focus_content_for_model(text)
        self.assertIn("Data summary", focused)
        self.assertIn("PK parameters", focused)
        self.assertNotIn("Raw data", focused)
        self.assertEqual(len(split_file_chunks(focused)), 1)

    def test_pk_target_detection(self):
        self.assertTrue(_is_pk_target("Dog PK", COLS))
        self.assertFalse(_is_pk_target("hERG", [
            ColumnDef(field="cpds_id", title="ID"),
            ColumnDef(field="ic50_um", title="IC50"),
        ]))

    def test_mock_dog_pk(self):
        text = _parse("DM-RF-2025022001（HW350003A)DPK检测报告.xlsx")
        got = mock_extract_pk(text, COLS, table_name="Dog PK")
        self.assertIsNotNone(got)
        rows, _ = got
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cpds_id"], "HW350003A")
        self.assertTrue(rows[0]["iv_1mpk_cl_l_h_kg"])
        self.assertTrue(rows[0]["po_5_mpk_cmax_ng_ml"])
        self.assertAlmostEqual(float(rows[0]["iv_1mpk_cl_l_h_kg"]), 0.427, delta=0.03)
        self.assertGreater(float(rows[0]["po_5_mpk_pct_f"] or 0), 50)

    def test_mock_monkey_pk(self):
        text = _parse("08065-25011-NG_HW356009-P1食蟹猴药代_报告_终稿_250312.xlsx")
        got = mock_extract_pk(text, COLS, table_name="Monkey PK")
        self.assertIsNotNone(got)
        rows, _ = got
        self.assertIn("HW356009", rows[0]["cpds_id"])
        self.assertTrue(rows[0]["iv_1mpk_cl_l_h_kg"])
        cl = float(rows[0]["iv_1mpk_cl_l_h_kg"])
        self.assertLess(cl, 2.0, "mL/h/kg 应换算成 L/h/kg")
        self.assertAlmostEqual(cl, 0.2046, delta=0.02)

    def test_species_mismatch_skips(self):
        monkey = _parse("08065-25012-NG_HW350003A 食蟹猴药代_报告_终稿_250314.xlsx")
        rows, note = mock_extract_pk(monkey, COLS, table_name="Dog PK")
        self.assertEqual(rows, [])
        self.assertIn("不符", note)
        dog = _parse("DM-RF-2025022002(HW356009-P1)DPK检测报告.xlsx")
        rows, note = mock_extract_pk(dog, COLS, table_name="Monkey PK")
        self.assertEqual(rows, [])
        self.assertIn("不符", note)


if __name__ == "__main__":
    unittest.main()
